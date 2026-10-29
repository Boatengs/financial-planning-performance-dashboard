#!/usr/bin/env python3
"""Independent checks on the built model. Writes processed/validation_report.json; exits non-zero on failure."""
from __future__ import annotations

import csv
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.network_history import validate_network_history
from pipeline.publish import PUBLISHED_FILES
from pipeline.config import PUBLISHED

P = ROOT / "processed"
FY_TOLERANCE_USD = 3_000_000  # SEC amounts are in millions; quarterly rounding can differ by a few million
REQUIRED_QUARTERLY = ["revenue", "operating_expenses", "operating_income", "net_income", "fuel_costs",
                      "labor_costs", "operating_cash_flow", "capex_total", "cash", "debt_total"]


def rows(name):
    with (P / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def q_index(label):
    return int(label[:4]) * 4 + int(label[5]) - 1


def main():
    checks, errors = {}, []

    def check(name, ok, detail=""):
        checks[name] = {"pass": bool(ok), "detail": detail}
        if not ok:
            errors.append(f"{name}: {detail}")

    # ---- SEC financials
    fin = rows("fact_financial_actual.csv")
    by = {(r["metric_id"], r["period_label"]): float(r["value"]) for r in fin}
    quarters = sorted({r["period_label"] for r in fin if r["metric_id"] == "revenue" and r["period_type"] != "FY"},
                      key=q_index)
    expected = list(range(q_index("2019Q1"), q_index(quarters[-1]) + 1))
    check("financial_quarters_contiguous_from_2019Q1", [q_index(q) for q in quarters] == expected,
          f"{quarters[0]}..{quarters[-1]} ({len(quarters)} quarters)")
    gaps = [f"{m}:{q}" for m in REQUIRED_QUARTERLY for q in quarters if (m, q) not in by]
    check("financial_required_metrics_every_quarter", not gaps, f"{len(gaps)} gaps {gaps[:10]}")
    worst = 0.0
    for m in ["revenue", "operating_income", "net_income", "operating_cash_flow", "capex_total", "fuel_costs"]:
        for year in {int(q[:4]) for q in quarters}:
            parts = [by.get((m, f"{year}Q{n}")) for n in range(1, 5)]
            full = by.get((m, f"{year}FY"))
            if full is not None and all(p is not None for p in parts):
                worst = max(worst, abs(sum(parts) - full))
    check("financial_quarters_sum_to_full_year", worst <= FY_TOLERANCE_USD, f"max difference ${worst:,.0f}")
    q4_derived = sum(1 for r in fin if r["period_type"] == "Q4" and r["method"] != "reported")
    check("financial_q4_present", any(r["period_type"] == "Q4" for r in fin), f"{q4_derived} Q4 values derived as FY minus 9M")

    # ---- network history (reuses the historical-network validator)
    try:
        report = validate_network_history(expected_years=range(2019, 2027))
        check("network_history_reconciles", report["status"] == "PASS",
              f'{report["period_min"]}..{report["period_max"]}, {report["route_month_rows"]} route-months')
    except AssertionError as exc:
        check("network_history_reconciles", False, str(exc)[:500])

    # ---- airports and the map layer
    qa = json.loads((P / "qa_summary.json").read_text(encoding="utf-8"))
    share = qa["airports"]["ttm_passenger_share_on_mapped_routes"] or 0
    check("bts_master_coordinate_ingested", qa["airports"]["bts_master_coordinate_ingested"])
    check("map_layer_covers_99pct_of_ttm_passengers", share >= 0.99, f"{share:.4%} of TTM passengers mapped")

    # ---- Form 41 and unit economics
    check("form41_no_unmapped_regions", not qa["form41"]["skipped_regions"], str(qa["form41"]["skipped_regions"]))
    pnl = rows("fact_form41_pnl_quarterly.csv")
    sums = defaultdict(lambda: defaultdict(int))
    for r in pnl:
        for f in ("op_revenues", "op_expenses", "trans_rev_pax"):
            sums[r["period_label"]][(r["scope"], f)] += int(r[f])
    bad = [q for q, s in sums.items() for f in ("op_revenues", "op_expenses", "trans_rev_pax")
           if s[("system", f)] != s[("domestic", f)] + s[("international", f)]]
    check("form41_system_equals_domestic_plus_international", not bad, str(bad[:5]))
    lo, hi = qa["form41"]["revenue_ratio_to_sec_min"], qa["form41"]["revenue_ratio_to_sec_max"]
    check("form41_revenue_reconciles_to_sec_within_2pct", lo is not None and 0.98 <= lo and hi <= 1.02,
          f"Form 41 system revenue / SEC consolidated revenue ranges {lo:.4f} to {hi:.4f}")
    ue = rows("fact_unit_economics_quarterly.csv")
    sys_q = sorted({r["period_label"] for r in ue if r["scope"] == "system"}, key=q_index)
    check("unit_economics_contiguous", [q_index(q) for q in sys_q] == list(range(q_index(sys_q[0]), q_index(sys_q[-1]) + 1)),
          f"{sys_q[0]}..{sys_q[-1]}")
    lf = [float(r["load_factor"]) for r in ue]
    fuel = [float(r["fuel_cost_per_gallon"]) for r in ue]
    check("unit_economics_plausible_ranges", min(lf) > 0.2 and max(lf) < 1.0 and min(fuel) > 0.5 and max(fuel) < 6.0,
          f"load factor {min(lf):.3f}..{max(lf):.3f}; fuel $/gal {min(fuel):.2f}..{max(fuel):.2f}")

    # ---- FP&A model
    summary = json.loads((P / "fpa_model_summary.json").read_text(encoding="utf-8"))
    sc = summary["scenario_next4_operating_income"]
    check("scenario_ordering", sc["DOWN"] < summary["base_next4_operating_income"] < sc["UP"],
          f'DOWN {sc["DOWN"]:,.0f} < BASE {summary["base_next4_operating_income"]:,.0f} < UP {sc["UP"]:,.0f}')
    bridge = rows("analysis_operating_income_bridge.csv")
    for b in summary["bridges"]:
        total = sum(float(r["operating_income_effect"]) for r in bridge
                    if r["from_period"] == b["from_period"] and r["to_period"] == b["to_period"])
        check(f'bridge_closes_{b["to_period"]}',
              abs(b["start_operating_income"] + total - b["end_operating_income"]) < 1.0)
    plan = rows("fact_budget_forecast.csv")
    act = {(r["period"], r["metric_id"]): float(r["value"]) for r in plan if r["scenario_id"] == "ACT"}
    ue_sys = {r["period_label"]: float(r["mainline_operating_income"]) for r in ue if r["scope"] == "system"}
    worst = max(abs(act[(q, "mainline_operating_income")] - v) for q, v in ue_sys.items())
    check("model_actuals_match_unit_economics", worst < 1.0, f"max difference ${worst:,.2f}")

    # ---- database and published outputs
    conn = sqlite3.connect(P / "delta_fpna_foundation.sqlite")
    route = rows("fact_route_monthly.csv")
    csv_totals = tuple(sum(int(r[f]) for r in route) for f in ("passengers", "seats", "asm", "rpm"))
    sql_totals = conn.execute("SELECT SUM(passengers), SUM(seats), SUM(asm), SUM(rpm) FROM fact_route_monthly").fetchone()
    check("sqlite_route_totals_match_csv", tuple(sql_totals) == csv_totals)
    window = conn.execute("SELECT MIN(window_start), MAX(window_end) FROM vw_route_12m").fetchone()
    check("route_12m_view_is_twelve_months", window[0] == qa["network"]["ttm_start"] and window[1] == qa["network"]["ttm_end"],
          f"{window[0]}..{window[1]}")
    conn.close()
    missing = [t for t in PUBLISHED_FILES.values() if not (PUBLISHED / t).exists()]
    check("published_outputs_present", not missing, str(missing))

    report = {"status": "PASS" if not errors else "FAIL", "checks": checks, "errors": errors}
    (P / "validation_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    shutil_target = PUBLISHED / "validation_report.json"
    shutil_target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
