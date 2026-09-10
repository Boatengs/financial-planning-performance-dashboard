from __future__ import annotations

import zipfile
from collections import defaultdict

from .config import INT_FIELDS, PROCESSED, RAW, T100_COLUMNS
from .io_utils import release_date_from_name, write_csv


def parse_t100_zip(path, scope: str):
    release_date = release_date_from_name(path)
    with zipfile.ZipFile(path) as zf:
        members = [n for n in zf.namelist() if n.lower().endswith((".asc", ".txt", ".csv"))]
        if not members:
            raise ValueError(f"No data member found in {path}")
        with zf.open(members[0]) as raw:
            for line_no, rawline in enumerate(raw, 1):
                line = rawline.decode("latin1").rstrip("\r\n")
                if not line:
                    continue
                parts = line.split("|")
                if parts and parts[-1] == "":
                    parts = parts[:-1]
                if len(parts) != 28:
                    raise ValueError(f"{path.name}:{line_no}: expected 28 fields, got {len(parts)}")
                row = dict(zip(T100_COLUMNS, parts))
                if row["carrier_code"].strip().upper() != "DL":
                    continue
                for key in INT_FIELDS:
                    v = row[key].strip()
                    row[key] = int(v) if v else 0
                for key in set(T100_COLUMNS) - INT_FIELDS:
                    row[key] = row[key].strip()
                row["scope"] = scope
                row["source_file"] = path.name
                row["source_release_date"] = release_date
                yield row


def build_t100():
    rows_by_key: dict[tuple, dict] = {}
    sources = []
    for scope in ("domestic", "international"):
        folder = RAW / "t100" / scope
        for path in sorted(folder.glob("*.zip")):
            sources.append(path)
            for row in parse_t100_zip(path, scope):
                natural_key = tuple(row[k] for k in [
                    "year", "month", "origin", "destination", "carrier_code", "carrier_entity_code",
                    "service_class", "aircraft_group", "aircraft_type", "aircraft_configuration"
                ])
                previous = rows_by_key.get(natural_key)
                if previous is None or row["source_release_date"] >= previous["source_release_date"]:
                    rows_by_key[natural_key] = row

    detailed = sorted(rows_by_key.values(), key=lambda r: (
        r["year"], r["month"], r["origin"], r["destination"], r["aircraft_type"], r["service_class"]
    ))
    write_csv(PROCESSED / "fact_route_aircraft_monthly.csv", detailed, T100_COLUMNS + ["scope", "source_file", "source_release_date"])

    agg = defaultdict(lambda: defaultdict(float))
    source_dates = defaultdict(str)
    for r in detailed:
        key = (r["year"], r["month"], r["origin"], r["destination"], r["scope"])
        a = agg[key]
        for field in ["departures_performed", "departures_scheduled", "payload_pounds", "seats", "passengers", "freight_pounds", "mail_pounds", "ramp_to_ramp_minutes", "airborne_minutes"]:
            a[field] += r[field]
        a["asm"] += r["seats"] * r["distance_miles"]
        a["rpm"] += r["passengers"] * r["distance_miles"]
        a["departure_miles"] += r["departures_performed"] * r["distance_miles"]
        a["distance_weight"] += r["departures_performed"]
        a["distance_miles"] = max(a.get("distance_miles", 0), r["distance_miles"])
        source_dates[key] = max(source_dates[key], r["source_release_date"])

    route_rows = []
    for (year, month, origin, destination, scope), a in sorted(agg.items()):
        asm, rpm = a["asm"], a["rpm"]
        dep_p, dep_s = a["departures_performed"], a["departures_scheduled"]
        route_rows.append({
            "period": f"{year:04d}-{month:02d}-01", "year": year, "month": month,
            "origin": origin, "destination": destination, "route_id": f"{origin}-{destination}",
            "market_id": "-".join(sorted([origin, destination])), "scope": scope,
            "distance_miles": int(a["distance_miles"]),
            "departures_performed": int(dep_p), "departures_scheduled": int(dep_s),
            "completion_rate": dep_p / dep_s if dep_s else None,
            "seats": int(a["seats"]), "passengers": int(a["passengers"]),
            "asm": int(asm), "rpm": int(rpm), "load_factor": rpm / asm if asm else None,
            "passengers_per_departure": a["passengers"] / dep_p if dep_p else None,
            "average_stage_length": a["departure_miles"] / a["distance_weight"] if a["distance_weight"] else None,
            "payload_pounds": int(a["payload_pounds"]), "freight_pounds": int(a["freight_pounds"]),
            "mail_pounds": int(a["mail_pounds"]), "ramp_to_ramp_hours": a["ramp_to_ramp_minutes"] / 60.0,
            "airborne_hours": a["airborne_minutes"] / 60.0, "source_release_date": source_dates[(year, month, origin, destination, scope)],
        })
    write_csv(PROCESSED / "fact_route_monthly.csv", route_rows)

    system = defaultdict(lambda: defaultdict(float))
    for r in route_rows:
        key = (r["period"], r["scope"])
        s = system[key]
        for field in ["departures_performed", "departures_scheduled", "seats", "passengers", "asm", "rpm", "freight_pounds", "mail_pounds", "airborne_hours"]:
            s[field] += r[field]
        s["departure_miles"] += r["departures_performed"] * r["distance_miles"]
    system_rows = []
    for (period, scope), s in sorted(system.items()):
        system_rows.append({
            "period": period, "scope": scope,
            "passengers": int(s["passengers"]), "seats": int(s["seats"]), "asm": int(s["asm"]), "rpm": int(s["rpm"]),
            "load_factor": s["rpm"] / s["asm"] if s["asm"] else None,
            "departures_performed": int(s["departures_performed"]), "departures_scheduled": int(s["departures_scheduled"]),
            "completion_rate": s["departures_performed"] / s["departures_scheduled"] if s["departures_scheduled"] else None,
            "passengers_per_departure": s["passengers"] / s["departures_performed"] if s["departures_performed"] else None,
            "average_stage_length": s["departure_miles"] / s["departures_performed"] if s["departures_performed"] else None,
            "freight_pounds": int(s["freight_pounds"]), "mail_pounds": int(s["mail_pounds"]), "airborne_hours": s["airborne_hours"],
        })
    write_csv(PROCESSED / "fact_network_kpi_monthly.csv", system_rows)
    return detailed, route_rows, system_rows, sources
