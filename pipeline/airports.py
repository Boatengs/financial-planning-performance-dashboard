from __future__ import annotations

import csv
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


def load_bts_master_coordinate(route_codes: set[str]):
    path = _find_master_coordinate_file()
    if path is None:
        return {}, None
    result = {}
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for r in reader:
            code = (r.get("Airport") or r.get("AIRPORT") or r.get("airport") or "").strip().upper()
            if code not in route_codes:
                continue
            is_latest = str(r.get("AirportIsLatest") or r.get("AIRPORT_IS_LATEST") or "").strip()
            if is_latest not in ("", "1", "1.0", "True", "TRUE", "true"):
                continue
            lat = _safe_float(r.get("Latitude") or r.get("LATITUDE"))
            lon = _safe_float(r.get("Longitude") or r.get("LONGITUDE"))
            row = {
                "airport_code": code,
                "airport_name": (r.get("AirportName") or r.get("AIRPORT_NAME") or "").strip(),
                "city": (r.get("AirportCityName") or r.get("AIRPORT_CITY_NAME") or "").strip(),
                "state_code": (r.get("AirportStateCode") or r.get("AIRPORT_STATE_CODE") or "").strip(),
                "state_name": (r.get("AirportStateName") or r.get("AIRPORT_STATE_NAME") or "").strip(),
                "country_code": (r.get("AirportCountryCodeISO") or r.get("AIRPORT_COUNTRY_CODE_ISO") or "").strip(),
                "country_name": (r.get("AirportCountryName") or r.get("AIRPORT_COUNTRY_NAME") or "").strip(),
                "city_market_name": (r.get("CityMarketName") or r.get("CITY_MARKET_NAME") or "").strip(),
                "latitude": lat, "longitude": lon, "elevation_ft": None,
                "coordinate_source": "BTS Master Coordinate", "coordinate_status": "resolved_bts_master_coordinate" if lat is not None and lon is not None else "bts_master_coordinate_missing_latlon",
                "effective_date": (r.get("AirportStartDate") or r.get("AIRPORT_START_DATE") or "").strip(),
            }
            if code not in result or (result[code]["latitude"] is None and lat is not None):
                result[code] = row
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
