"""Validation of the 2019-2026 T-100 network marts written by scripts/build_data_foundation.py."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from .config import PROCESSED, ROOT

DETAIL_KEY_FIELDS = [
    "year",
    "month",
    "origin",
    "destination",
    "carrier_code",
    "carrier_entity_code",
    "service_class",
    "aircraft_group",
    "aircraft_type",
    "aircraft_configuration",
    "scope",
]

ROUTE_KEY_FIELDS = ["period", "origin", "destination", "scope"]
CORE_NONNEGATIVE_FIELDS = [
    "distance_miles",
    "departures_performed",
    "departures_scheduled",
    "seats",
    "passengers",
    "asm",
    "rpm",
    "freight_pounds",
    "mail_pounds",
]


def _read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _as_int(row, field):
    value = row.get(field, "")
    return int(float(value)) if value not in (None, "") else 0


def _as_float(row, field):
    value = row.get(field, "")
    return float(value) if value not in (None, "") else None


def _unique_key_check(rows, fields, label, errors):
    seen = set()
    duplicates = 0
    for row in rows:
        key = tuple(row.get(field, "") for field in fields)
        if key in seen:
            duplicates += 1
        seen.add(key)
    if duplicates:
        errors.append(f"{label} contains {duplicates} duplicate natural keys")


def validate_network_history(expected_years=range(2019, 2027)):
    detail_path = PROCESSED / "fact_route_aircraft_monthly.csv"
    route_path = PROCESSED / "fact_route_monthly.csv"
    network_path = PROCESSED / "fact_network_kpi_monthly.csv"
    airport_path = PROCESSED / "dim_airport.csv"
    route_dim_path = PROCESSED / "dim_route.csv"
    summary_path = PROCESSED / "network_history_summary.json"

    required = [detail_path, route_path, network_path, airport_path, route_dim_path, summary_path]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"Missing network outputs: {', '.join(missing)}")

    detailed = _read_csv(detail_path)
    route_rows = _read_csv(route_path)
    network_rows = _read_csv(network_path)
    airport_rows = _read_csv(airport_path)
    route_dim = _read_csv(route_dim_path)
    errors = []

    if not detailed:
        errors.append("Aircraft-detail fact table is empty")
    if not route_rows:
        errors.append("Route-month fact table is empty")
    if not network_rows:
        errors.append("Network KPI fact table is empty")

    carriers = {row.get("carrier_code", "").strip().upper() for row in detailed}
    if carriers != {"DL"}:
        errors.append(f"Unexpected reporting carriers: {sorted(carriers)}")

    _unique_key_check(detailed, DETAIL_KEY_FIELDS, "Aircraft-detail fact table", errors)
    _unique_key_check(route_rows, ROUTE_KEY_FIELDS, "Route-month fact table", errors)

    for row in route_rows:
        for field in CORE_NONNEGATIVE_FIELDS:
            if _as_int(row, field) < 0:
                errors.append(f"Negative {field} in route-month fact table")
                break

    invalid_release_rows = [
        row
        for row in detailed
        if ".REL" in row.get("source_file", "").upper()
        and row.get("source_release_date") == "1900-01-01"
    ]
    if invalid_release_rows:
        errors.append(f"{len(invalid_release_rows)} annual archive rows have unknown release dates")

    observed_airports = {row["origin"] for row in route_rows} | {row["destination"] for row in route_rows}
    dimension_airports = {row["airport_code"] for row in airport_rows}
    if observed_airports != dimension_airports:
        errors.append("Airport dimension does not exactly cover observed route airport codes")

    observed_routes = {row["route_id"] for row in route_rows}
    dimension_routes = {row["route_id"] for row in route_dim}
    if observed_routes != dimension_routes:
        errors.append("Route dimension does not exactly cover observed route IDs")

    periods = sorted({row["period"] for row in route_rows})
    observed_years = {int(row["period"][:4]) for row in route_rows}
    expected_years = set(expected_years)
    missing_years = sorted(expected_years - observed_years)
    if missing_years:
        errors.append(f"Missing expected calendar years: {missing_years}")
    if expected_years == set(range(2019, 2027)):
        if not periods or periods[0] > "2019-01-01":
            errors.append(f"Historical coverage starts too late: {periods[0] if periods else 'none'}")
        if not periods or periods[-1] < "2026-05-01":
            errors.append(f"Historical coverage ends too early: {periods[-1] if periods else 'none'}")

    route_aggregates = defaultdict(lambda: defaultdict(int))
    for row in route_rows:
        key = (row["period"], row["scope"])
        for field in [
            "passengers",
            "seats",
            "asm",
            "rpm",
            "departures_performed",
            "departures_scheduled",
            "freight_pounds",
            "mail_pounds",
        ]:
            route_aggregates[key][field] += _as_int(row, field)

    network_by_key = {(row["period"], row["scope"]): row for row in network_rows}
    if set(route_aggregates) != set(network_by_key):
        errors.append("Network KPI period/scope keys do not match route aggregates")
    else:
        for key, aggregate in route_aggregates.items():
            row = network_by_key[key]
            for field, expected in aggregate.items():
                if _as_int(row, field) != expected:
                    errors.append(f"Network reconciliation failed for {key} field {field}")
            asm = aggregate["asm"]
            rpm = aggregate["rpm"]
            departures_scheduled = aggregate["departures_scheduled"]
            departures_performed = aggregate["departures_performed"]
            expected_load = rpm / asm if asm else None
            expected_completion = departures_performed / departures_scheduled if departures_scheduled else None
            actual_load = _as_float(row, "load_factor")
            actual_completion = _as_float(row, "completion_rate")
            if expected_load is not None and (actual_load is None or abs(actual_load - expected_load) > 1e-12):
                errors.append(f"Load-factor reconciliation failed for {key}")
            if expected_completion is not None and (
                actual_completion is None or abs(actual_completion - expected_completion) > 1e-12
            ):
                errors.append(f"Completion-rate reconciliation failed for {key}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("route_month_rows") != len(route_rows):
        errors.append("Summary route-month row count does not match generated fact table")
    if summary.get("aircraft_detail_rows") != len(detailed):
        errors.append("Summary aircraft-detail row count does not match generated fact table")

    report = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "period_min": periods[0] if periods else None,
        "period_max": periods[-1] if periods else None,
        "years_observed": sorted(observed_years),
        "detail_rows": len(detailed),
        "route_month_rows": len(route_rows),
        "network_month_rows": len(network_rows),
        "airports": len(airport_rows),
        "routes": len(route_dim),
        "reporting_carriers": sorted(carriers),
        "annual_rows_with_unknown_release_date": len(invalid_release_rows),
    }
    (PROCESSED / "network_history_validation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if errors:
        raise AssertionError("; ".join(errors[:20]))
    return report
