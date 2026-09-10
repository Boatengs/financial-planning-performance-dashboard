#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.airports import build_airport_dimension
from pipeline.config import PROCESSED
from pipeline.dimensions import build_dimensions, build_source_manifest
from pipeline.financials import build_financial_actuals, build_financial_derived
from pipeline.quality import validate
from pipeline.sqlite_store import build_sqlite
from pipeline.t100 import build_t100


def main():
    detailed, route_rows, system_rows, t100_sources = build_t100()
    financial_rows, fin_meta = build_financial_actuals()
    financial_derived_rows = build_financial_derived(financial_rows)
    airport_rows, route_codes, bts_master_path = build_airport_dimension(detailed, route_rows)
    _, _, metric_rows, _ = build_dimensions(fin_meta, route_rows)
    source_rows = build_source_manifest(t100_sources, bts_master_path)
    qa = validate(financial_rows, detailed, route_rows, airport_rows, route_codes, bts_master_path)
    table_files = {
        "fact_financial_actual": PROCESSED / "fact_financial_actual.csv",
        "fact_financial_kpi_derived": PROCESSED / "fact_financial_kpi_derived.csv",
        "fact_route_aircraft_monthly": PROCESSED / "fact_route_aircraft_monthly.csv",
        "fact_route_monthly": PROCESSED / "fact_route_monthly.csv",
        "fact_network_kpi_monthly": PROCESSED / "fact_network_kpi_monthly.csv",
        "dim_date": PROCESSED / "dim_date.csv",
        "dim_route": PROCESSED / "dim_route.csv",
        "dim_airport": PROCESSED / "dim_airport.csv",
        "dim_metric": PROCESSED / "dim_metric.csv",
        "dim_scenario": PROCESSED / "dim_scenario.csv",
        "source_manifest": PROCESSED / "source_manifest.csv",
    }
    db = build_sqlite(table_files)
    print(json.dumps({
        "qa": qa,
        "sqlite": str(db),
        "source_count": len(source_rows),
        "metric_count": len(metric_rows),
        "financial_derived_rows": len(financial_derived_rows),
    }, indent=2))


if __name__ == "__main__":
    main()
