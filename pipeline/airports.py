from __future__ import annotations

import csv
import io
import math
import zipfile

from .config import PROCESSED, RAW
from .io_utils import write_csv


def _safe_float(value):
    if value in (None, ""):
        return None
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def load_faa_airports(route_codes: set[str]):
    path = RAW / "faa_airports_2026-09-03.zip"
    result = {}
    if not path.exists():
        # FAA NASR is a U.S. fallback only; BTS Master Coordinate is the primary source.
        return result
    with zipfile.ZipFile(path) as zf:
        with zf.open("APT_BASE.csv") as raw:
            reader = csv.DictReader((line.decode("utf-8-sig", errors="replace") for line in raw))
            for r in reader:
                code = (r.get("ARPT_ID") or "").strip().upper()
                if code not in route_codes:
                    continue
                result[code] = {
                    "airport_code": code, "airport_name": (r.get("ARPT_NAME") or "").strip(),
                    "city": (r.get("CITY") or "").strip(), "state_code": (r.get("STATE_CODE") or "").strip(),
                    "state_name": (r.get("STATE_NAME") or "").strip(), "country_code": (r.get("COUNTRY_CODE") or "").strip(),
                    "country_name": "", "city_market_name": "", "latitude": _safe_float(r.get("LAT_DECIMAL")),
                    "longitude": _safe_float(r.get("LONG_DECIMAL")), "elevation_ft": _safe_float(r.get("ELEV")),
                    "coordinate_source": "FAA NASR APT_BASE", "coordinate_status": "resolved_faa",
                    "effective_date": (r.get("EFF_DATE") or "").strip(),
                }
    return result


def _find_master_coordinate_file():
    preferred = [
        RAW / "bts" / "master_coordinate.zip",
        RAW / "bts_master_coordinate.csv", RAW / "Master_Coordinate.csv", RAW / "T_MASTER_CORD.csv",
        RAW / "master_coordinate.csv", RAW / "bts" / "Master_Coordinate.csv"
    ]
    for p in preferred:
        if p.exists():
            return p
    candidates = list(RAW.rglob("*.csv"))
    for p in candidates:
        n = p.name.lower().replace("_", " ")
        if "master" in n and "coord" in n:
            return p
    return None


def _master_coordinate_rows(path):
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            members = [i for i in zf.infolist() if i.filename.lower().endswith(".csv")]
            if not members:
                raise ValueError(f"No CSV member found in {path}")
            member = max(members, key=lambda i: i.file_size)
            with zf.open(member) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
                yield from csv.DictReader(text)
    else:
        with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
            yield from csv.DictReader(f)


def _pick(row, *names):
    """Return the first non-empty value among header aliases (TranStats CSV or legacy CamelCase)."""
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value).strip()
    return ""


COORDINATE_DIAGNOSTICS: dict = {}


def load_bts_master_coordinate(route_codes: set[str]):
    """Latest Master Coordinate record per airport; fall back to the newest earlier record with coordinates.

    An airport keeps its location when it is renamed or re-sequenced, so an earlier record's latitude and
    longitude is a sound fallback when the latest record has none. Such rows are flagged separately.
    """
    path = _find_master_coordinate_file()
    COORDINATE_DIAGNOSTICS.clear()
    if path is None:
        return {}, None
    latest, prior = {}, {}
    for r in _master_coordinate_rows(path):
        code = _pick(r, "AIRPORT", "Airport", "airport").upper()
        if code not in route_codes:
            continue
        is_latest = _pick(r, "AIRPORT_IS_LATEST", "AirportIsLatest") in ("", "1", "1.0", "1.00", "True", "TRUE", "true")
        lat = _safe_float(_pick(r, "LATITUDE", "Latitude"))
        lon = _safe_float(_pick(r, "LONGITUDE", "Longitude"))
        diag = COORDINATE_DIAGNOSTICS.setdefault(code, {"rows": 0, "latest_rows": 0, "rows_with_coordinates": 0})
        diag["rows"] += 1
        diag["latest_rows"] += int(is_latest)
        diag["rows_with_coordinates"] += int(lat is not None and lon is not None)
        row = {
            "airport_code": code,
            "airport_name": _pick(r, "DISPLAY_AIRPORT_NAME", "AIRPORT_NAME", "AirportName"),
            "city": _pick(r, "DISPLAY_AIRPORT_CITY_NAME_FULL", "AIRPORT_CITY_NAME", "AirportCityName"),
            "state_code": _pick(r, "AIRPORT_STATE_CODE", "AirportStateCode"),
            "state_name": _pick(r, "AIRPORT_STATE_NAME", "AirportStateName"),
            "country_code": _pick(r, "AIRPORT_COUNTRY_CODE_ISO", "AirportCountryCodeISO"),
            "country_name": _pick(r, "AIRPORT_COUNTRY_NAME", "AirportCountryName"),
            "city_market_name": _pick(r, "DISPLAY_CITY_MARKET_NAME_FULL", "CITY_MARKET_NAME", "CityMarketName"),
            "latitude": lat, "longitude": lon, "elevation_ft": None,
            "coordinate_source": "BTS Master Coordinate",
            "coordinate_status": "resolved_bts_master_coordinate" if lat is not None and lon is not None
            else "bts_master_coordinate_missing_latlon",
            "effective_date": _pick(r, "AIRPORT_START_DATE", "AirportStartDate"),
        }
        if is_latest:
            if code not in latest or (latest[code]["latitude"] is None and lat is not None):
                latest[code] = row
        elif lat is not None and lon is not None:
            if code not in prior or row["effective_date"] > prior[code]["effective_date"]:
                prior[code] = row
    result = dict(latest)
    for code, row in prior.items():
        if code not in result or result[code]["latitude"] is None:
            fallback = dict(row)
            if code in result:  # keep the current name and attributes, borrow only the location
                fallback = {**result[code], "latitude": row["latitude"], "longitude": row["longitude"]}
            fallback["coordinate_status"] = "resolved_bts_master_coordinate_prior_record"
            result[code] = fallback
    return result, path


def build_airport_dimension(detailed, route_rows):
    route_codes = {r["origin"] for r in route_rows} | {r["destination"] for r in route_rows}
    observed = {}
    for r in detailed:
        for side in ("origin", "destination"):
            code = r[side]
            city = r[f"{side}_city_name"]
            wac = r[f"{side}_wac"]
            o = observed.setdefault(code, {"t100_city_name": city, "wac": wac})
            if not o.get("t100_city_name") and city:
                o["t100_city_name"] = city
            if not o.get("wac") and wac:
                o["wac"] = wac

    faa = load_faa_airports(route_codes)
    bts, bts_path = load_bts_master_coordinate(route_codes)
    rows = []
    for code in sorted(route_codes):
        obs = observed.get(code, {})
        if code in bts and bts[code].get("latitude") is not None and bts[code].get("longitude") is not None:
            base = dict(bts[code])
            if code in faa and base.get("elevation_ft") is None:
                base["elevation_ft"] = faa[code].get("elevation_ft")
        elif code in faa:
            base = dict(faa[code])
        elif code in bts:
            base = dict(bts[code])
        else:
            base = {
                "airport_code": code, "airport_name": "", "city": "", "state_code": "", "state_name": "",
                "country_code": "", "country_name": "", "city_market_name": "", "latitude": None, "longitude": None,
                "elevation_ft": None, "coordinate_source": "", "coordinate_status": "pending_bts_master_coordinate",
                "effective_date": "",
            }
        base["t100_city_name"] = obs.get("t100_city_name", "")
        base["wac"] = obs.get("wac", "")
        rows.append(base)

    fields = ["airport_code", "airport_name", "t100_city_name", "city", "state_code", "state_name", "country_code", "country_name",
              "city_market_name", "wac", "latitude", "longitude", "elevation_ft", "coordinate_source", "coordinate_status", "effective_date"]
    write_csv(PROCESSED / "dim_airport.csv", rows, fields)
    return rows, route_codes, bts_path
