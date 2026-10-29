#!/usr/bin/env python3
"""Build the complete Delta FP&A model from downloaded raw sources.

One run produces every mart, the analysis tables, the FP&A model, a single SQLite database
and the published outputs for the dashboard and Tableau.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.airports import COORDINATE_DIAGNOSTICS, build_airport_dimension
from pipeline.config import PROCESSED
from pipeline.dimensions import build_dimensions, build_source_manifest
from pipeline.financials import (build_financial_actuals, resolve_companyfacts_path, build_financial_derived, coverage_summary, latest_period,
                                 quarterly_reconciliation)
from pipeline.form41 import build_form41
from pipeline.fpa_model import build_fpa_model
from pipeline.io_utils import sha256_file
from pipeline.network_analysis import build_network_analysis
from pipeline.publish import publish
from pipeline.sqlite_store import build_sqlite
from pipeline.t100 import build_t100
from pipeline.unit_economics import build_unit_economics, form41_vs_sec


def main():
    detailed, route_rows, system_rows, t100_sources = build_t100()
    financial_rows, fin_meta = build_financial_actuals()
    derived_rows = build_financial_derived(financial_rows)
    recon = quarterly_reconciliation(financial_rows)
    airport_rows, route_codes, bts_master_path = build_airport_dimension(detailed, route_rows)
    form41 = build_form41()
    unit_rows, unit_skipped = build_unit_economics(route_rows, form41["pnl_quarterly"], form41["fuel_quarterly"])
    sec_check = form41_vs_sec(form41["pnl_quarterly"], financial_rows)
    network = build_network_analysis(route_rows, airport_rows)
    model = build_fpa_model(unit_rows)
    _, _, metric_rows, _ = build_dimensions(fin_meta, route_rows)
    source_rows = build_source_manifest(t100_sources, bts_master_path, form41["sources"])

    resolved = [a for a in airport_rows if a.get("latitude") is not None and a.get("longitude") is not None]
    pending = [a["airport_code"] for a in airport_rows if a.get("latitude") is None or a.get("longitude") is None]
    ttm_pax = sum(int(r["passengers"]) for r in route_rows if network["ttm_start"] <= r["period"] <= network["ttm_end"])
    mapped_pax = sum(int(r["passengers"]) for r in network["layer"])
    periods = sorted({r["period"] for r in route_rows})
    ratios = [r["revenue_ratio"] for r in sec_check if r["revenue_ratio"] is not None]

    qa = {
        "build_timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "financial": {
            "source": resolve_companyfacts_path()[1],
            "fact_rows": len(financial_rows), "derived_rows": len(derived_rows),
            "latest_quarter_end": latest_period(financial_rows), "methods": coverage_summary(financial_rows),
            "fy_reconciliation_checks": len(recon),
            "fy_reconciliation_max_abs_difference": max((abs(c["difference"]) for c in recon), default=0),
        },
        "network": {
            "period_min": periods[0], "period_max": periods[-1], "t100_source_files": len(t100_sources),
            "aircraft_detail_rows": len(detailed), "route_month_rows": len(route_rows),
            "network_month_rows": len(system_rows),
            "directional_routes": len({r["route_id"] for r in route_rows}),
            "ttm_start": network["ttm_start"], "ttm_end": network["ttm_end"],
        },
        "airports": {
            "observed": len(route_codes), "with_coordinates": len(resolved), "pending_codes": pending,
            "pending_master_coordinate_rows": {c: COORDINATE_DIAGNOSTICS.get(c, {"rows": 0}) for c in pending},
            "resolved_from_prior_record": [a["airport_code"] for a in airport_rows
                                           if a.get("coordinate_status") == "resolved_bts_master_coordinate_prior_record"],
            "bts_master_coordinate_ingested": bool(bts_master_path),
            "ttm_passenger_share_on_mapped_routes": mapped_pax / ttm_pax if ttm_pax else None,
            "ttm_routes_without_coordinates": network["routes_without_coordinates"],
        },
        "form41": {
            "p12_rows": len(form41["p12_rows"]), "regions_seen": form41["regions_seen"],
            "skipped_regions": form41["skipped_regions"], "fuel_months": len(form41["fuel_monthly"]),
            "revenue_ratio_to_sec_min": min(ratios) if ratios else None,
            "revenue_ratio_to_sec_max": max(ratios) if ratios else None,
        },
        "unit_economics": {
            "rows": len(unit_rows), "quarters": sorted({r["period_label"] for r in unit_rows}),
            "skipped_incomplete_quarters": unit_skipped,
        },
        "model": {k: model[k] for k in ("latest_actual", "forecast_quarters", "budget_quarters")},
        "scope_note": ("T-100 and Form 41 cover the DL reporting carrier (mainline). SEC figures are consolidated "
                       "Delta Air Lines, Inc. Per-ASM measures use Form 41 numerators over T-100 ASMs only."),
        "scenario_integrity_note": ("Budget, Forecast, Upside and Downside rows are analyst-modeled from public "
                                    "actuals with documented assumptions; they are not Delta guidance."),
    }
    (PROCESSED / "qa_summary.json").write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")

    network_summary = {
        "period_min": periods[0], "period_max": periods[-1],
        "aircraft_detail_rows": len(detailed), "route_month_rows": len(route_rows),
        "network_month_rows": len(system_rows),
        "output_sha256": {name: sha256_file(PROCESSED / name) for name in
                          ("fact_route_monthly.csv", "fact_network_kpi_monthly.csv", "dim_airport.csv")},
    }
    (PROCESSED / "network_history_summary.json").write_text(
        json.dumps(network_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    table_files = {name: PROCESSED / f"{name}.csv" for name in [
        "fact_financial_actual", "fact_financial_kpi_derived", "fact_route_aircraft_monthly", "fact_route_monthly",
        "fact_network_kpi_monthly", "fact_route_annual", "fact_form41_pnl_region", "fact_form41_pnl_quarterly",
        "fact_fuel_monthly", "fact_fuel_quarterly", "fact_unit_economics_quarterly", "fact_budget_forecast",
        "fact_driver_assumption", "fact_budget_variance", "fact_forecast_backtest", "analysis_forecast_method_comparison",
        "analysis_sensitivity",
        "analysis_operating_income_bridge", "analysis_market_ttm_vs_2019", "analysis_airport_ttm_vs_2019",
        "analysis_network_structure", "layer_route_ttm", "check_form41_vs_sec", "dim_date", "dim_route",
        "dim_airport", "dim_metric", "dim_scenario", "source_manifest",
    ]}
    db = build_sqlite(table_files)
    published = publish()
    print(json.dumps({"qa": qa, "model": model, "sqlite": str(db.relative_to(ROOT)), "sources": len(source_rows),
                      "metrics": len(metric_rows), "published_files": len(published)}, indent=2, default=str))


if __name__ == "__main__":
    main()
