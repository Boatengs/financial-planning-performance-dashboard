#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "processed"


def csv_rows(name):
    with (P / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    route = csv_rows("fact_route_monthly.csv")
    detail = csv_rows("fact_route_aircraft_monthly.csv")
    airports = csv_rows("dim_airport.csv")
    fin = csv_rows("fact_financial_actual.csv")
    fin_derived = csv_rows("fact_financial_kpi_derived.csv")
    metrics = csv_rows("dim_metric.csv")
    scenarios = csv_rows("dim_scenario.csv")

    assert route and detail and fin, "Core facts cannot be empty"
    assert len(airports) == len({r["origin"] for r in route} | {r["destination"] for r in route}), "Airport dimension must cover every observed airport code"
    assert len({r["airport_code"] for r in airports}) == len(airports), "Airport codes must be unique"
    assert all(r["carrier_code"] == "DL" for r in detail), "T-100 detail must be restricted to DL reporting carrier code"
    assert all(int(r["passengers"]) >= 0 and int(r["seats"]) >= 0 for r in detail), "Negative traffic values found"
    assert all(r["scenario_type"] == "Reported" or r["scenario_type"] == "Modeled" for r in scenarios)
    assert sum(1 for _ in open(P / "fact_budget_forecast_template.csv", encoding="utf-8")) == 1, "Budget template must be header-only"
    assert sum(1 for _ in open(P / "fact_driver_assumption_template.csv", encoding="utf-8")) == 1, "Driver template must be header-only"

    total_passengers = sum(int(r["passengers"]) for r in route)
    total_seats = sum(int(r["seats"]) for r in route)
    total_asm = sum(int(r["asm"]) for r in route)
    total_rpm = sum(int(r["rpm"]) for r in route)
    total_dep_p = sum(int(r["departures_performed"]) for r in route)
    total_dep_s = sum(int(r["departures_scheduled"]) for r in route)
    resolved_coords = sum(1 for r in airports if r["latitude"] and r["longitude"])

    conn = sqlite3.connect(P / "delta_fpna_foundation.sqlite")
    sql_totals = conn.execute("SELECT SUM(passengers), SUM(seats), SUM(asm), SUM(rpm), SUM(departures_performed), SUM(departures_scheduled) FROM fact_route_monthly").fetchone()
    assert sql_totals == (total_passengers, total_seats, total_asm, total_rpm, total_dep_p, total_dep_s), "SQLite totals differ from CSV facts"
    route_types = {r[1]: r[2] for r in conn.execute("PRAGMA table_info(fact_route_monthly)")}
    assert route_types["passengers"] == "INTEGER" and route_types["load_factor"] == "REAL", "SQLite numeric types not preserved"
    views = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'")}
    assert {"vw_network_monthly", "vw_route_12m", "vw_financial_actual_latest", "vw_financial_kpi_long"} <= views, "Expected analytical views missing"
    conn.close()

    report = {
        "status": "PASS",
        "checks": {
            "core_facts_nonempty": True,
            "airport_dimension_complete_for_observed_codes": True,
            "airport_codes_unique": True,
            "reporting_carrier_restricted_to_DL": True,
            "no_negative_passenger_or_seat_values": True,
            "modeled_scenario_templates_empty": True,
            "sqlite_totals_match_csv": True,
            "sqlite_numeric_types_preserved": True,
            "analytical_views_present": sorted(views),
        },
        "counts": {
            "financial_fact_rows": len(fin),
            "financial_derived_kpi_rows": len(fin_derived),
            "t100_aircraft_rows": len(detail),
            "t100_route_month_rows": len(route),
            "metric_dictionary_rows": len(metrics),
            "airport_rows": len(airports),
            "airports_with_coordinates": resolved_coords,
            "passengers": total_passengers,
            "seats": total_seats,
            "asm": total_asm,
            "rpm": total_rpm,
            "load_factor": total_rpm / total_asm if total_asm else None,
            "departures_performed": total_dep_p,
            "departures_scheduled": total_dep_s,
            "completion_rate": total_dep_p / total_dep_s if total_dep_s else None,
        },
        "key_output_sha256": {
            name: sha256(P / name) for name in [
                "fact_financial_actual.csv", "fact_financial_kpi_derived.csv", "fact_route_monthly.csv", "fact_network_kpi_monthly.csv",
                "dim_airport.csv", "dim_metric.csv", "dim_scenario.csv", "source_manifest.csv"
            ]
        }
    }
    (P / "validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
