from __future__ import annotations

import json
from datetime import datetime, timezone

from .config import PROCESSED


def validate(financial_rows, detailed, route_rows, airport_rows, route_codes, bts_master_path):
    errors = []
    for r in detailed:
        for k in ["distance_miles", "departures_performed", "departures_scheduled", "seats", "passengers"]:
            if r[k] < 0:
                errors.append(f"negative {k}: {r}")
    if not financial_rows:
        errors.append("No financial actuals extracted")
    if not route_rows:
        errors.append("No Delta T-100 route rows extracted")
    if len(airport_rows) != len(route_codes):
        errors.append(f"Airport dimension coverage mismatch: {len(airport_rows)} rows for {len(route_codes)} codes")
    if errors:
        raise AssertionError("; ".join(errors[:10]))

    coverage_months = sorted({r["period"] for r in route_rows})
    resolved = [r for r in airport_rows if r.get("latitude") is not None and r.get("longitude") is not None]
    pending = [r for r in airport_rows if r.get("latitude") is None or r.get("longitude") is None]
    faa_resolved = [r for r in resolved if r.get("coordinate_source") == "FAA NASR APT_BASE"]
    bts_resolved = [r for r in resolved if r.get("coordinate_source") == "BTS Master Coordinate"]
    over_capacity = sum(1 for r in detailed if r["aircraft_configuration"] == 1 and r["passengers"] > r["seats"] and r["seats"] > 0)
    summary = {
        "build_timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "financial_fact_rows": len(financial_rows),
        "t100_delta_aircraft_rows": len(detailed),
        "t100_delta_route_month_rows": len(route_rows),
        "t100_date_min": min(coverage_months) if coverage_months else None,
        "t100_date_max": max(coverage_months) if coverage_months else None,
        "unique_directional_routes": len({r["route_id"] for r in route_rows}),
        "unique_airports_in_t100": len(route_codes),
        "airport_dimension_rows": len(airport_rows),
        "airports_with_coordinates": len(resolved),
        "airports_resolved_bts_master_coordinate": len(bts_resolved),
        "airports_resolved_faa_fallback": len(faa_resolved),
        "airports_pending_coordinates": len(pending),
        "pending_airport_codes": [r["airport_code"] for r in pending],
        "bts_master_coordinate_ingested": bool(bts_master_path),
        "passenger_gt_seat_detail_rows_flagged": over_capacity,
        "scope_note": "T-100 layer is restricted to records whose reporting carrier code is DL. It is not represented as the full Delta-marketed network or all Delta Connection affiliates.",
        "coordinate_note": "BTS Master Coordinate is canonical when present; FAA NASR is a U.S.-focused fallback. Unresolved airports remain explicitly flagged rather than fabricated.",
        "scenario_integrity_note": "Budget, Forecast, Upside and Downside tables are schema-only templates at this stage; no modeled values are fabricated in the data foundation.",
    }
    (PROCESSED / "qa_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
