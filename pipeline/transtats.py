"""Acquire tables from the BTS TranStats download form (DL_SelectFields.aspx).

TranStats has no bulk API. Each table is downloaded by loading its public form, reading the
ASP.NET state fields, ticking the required variables, and posting the form back with a year
and period. The same protocol serves T-100 segment data, Form 41 financial schedules and the
Master Coordinate airport table; only the table ID, database query and field list differ.
"""
from __future__ import annotations

import html as html_lib
import http.cookiejar
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DL_FORM = "https://transtats.bts.gov/DL_SelectFields.aspx"
DB_NAME_QUERY = "QO_fu146_anzr=Nv4%20Pn44vr45"
TABLE_IDS = {"domestic": 259, "international": 261}
_VQ = "abcdefghijklmnopqrstuvwxyz0123456789"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Safari/537.36"
)

# Canonical fields required by pipeline.t100. carrier_wac is not exposed by the
# current TranStats form and is retained as a zero-valued compatibility field.
REQUIRED_FORM_FIELDS = {
    "DEPARTURES_SCHEDULED",
    "DEPARTURES_PERFORMED",
    "PAYLOAD",
    "SEATS",
    "PASSENGERS",
    "FREIGHT",
    "MAIL",
    "DISTANCE",
    "RAMP_TO_RAMP",
    "AIR_TIME",
    "UNIQUE_CARRIER",
    "UNIQUE_CARRIER_ENTITY",
    "CARRIER_GROUP",
    "ORIGIN_AIRPORT_ID",
    "ORIGIN",
    "ORIGIN_CITY_NAME",
    "ORIGIN_WAC",
    "DEST_AIRPORT_ID",
    "DEST",
    "DEST_CITY_NAME",
    "DEST_WAC",
    "AIRCRAFT_GROUP",
    "AIRCRAFT_TYPE",
    "AIRCRAFT_CONFIG",
    "YEAR",
    "MONTH",
    "CLASS",
}

FORM41_P12_FIELDS = {
    "YEAR", "QUARTER", "UNIQUE_CARRIER", "UNIQUE_CARRIER_ENTITY", "REGION", "CARRIER_GROUP_NEW",
    "TRANS_REV_PAX", "MAIL", "TOTAL_PROPERTY", "PROP_FREIGHT", "PROP_BAG", "TOTAL_CHARTER",
    "TOTAL_MISC_REV", "RES_CANCEL_FEES", "MISC_OP_REV", "PUB_SVC_REVENUE", "TRANS_REVENUE", "OP_REVENUES",
    "FLYING_OPS", "MAINTENANCE", "PAX_SERVICE", "AIRCFT_SERVICES", "PROMOTION_SALES", "GENERAL_ADMIN",
    "GENERAL_SERVICES", "DEPREC_AMORT", "TRANS_EXPENSES", "OP_EXPENSES", "OP_PROFIT_LOSS",
    "INTEREST_LONG_DEBT", "NON_OP_INCOME", "INCOME_PRE_TAX", "INCOME_TAX", "NET_INCOME",
}

FORM41_FUEL_FIELDS = {
    "YEAR", "QUARTER", "MONTH", "UNIQUE_CARRIER", "CARRIER_GROUP_NEW",
    "SDOMT_GALLONS", "SINT_GALLONS", "TS_GALLONS", "TOTAL_GALLONS",
    "SDOMT_COST", "SINT_COST", "TS_COST", "TOTAL_COST",
}

MASTER_COORDINATE_FIELDS = {
    "AIRPORT_ID", "AIRPORT", "DISPLAY_AIRPORT_NAME", "DISPLAY_AIRPORT_CITY_NAME_FULL", "AIRPORT_WAC",
    "AIRPORT_COUNTRY_NAME", "AIRPORT_COUNTRY_CODE_ISO", "AIRPORT_STATE_NAME", "AIRPORT_STATE_CODE",
    "DISPLAY_CITY_MARKET_NAME_FULL", "LATITUDE", "LONGITUDE", "AIRPORT_START_DATE", "AIRPORT_THRU_DATE",
    "AIRPORT_IS_CLOSED", "AIRPORT_IS_LATEST",
}


@dataclass(frozen=True)
class TableSpec:
    key: str
    title: str
    table_id: int
    db_query: str
    fields: frozenset
    by_year: bool = True


TABLES = {
    "t100_domestic": TableSpec("t100_domestic", "T-100 Domestic Segment (U.S. Carriers)", 259,
                               DB_NAME_QUERY, frozenset(REQUIRED_FORM_FIELDS)),
    "t100_international": TableSpec("t100_international", "T-100 International Segment (All Carriers)", 261,
                                    DB_NAME_QUERY, frozenset(REQUIRED_FORM_FIELDS)),
    "form41_p12": TableSpec("form41_p12", "Form 41 Schedule P-1.2 (quarterly profit and loss)", 295,
                            "QO_fu146_anzr=Nv4%20Pn44vr4%20Sv0n0pvny", frozenset(FORM41_P12_FIELDS)),
    "form41_fuel": TableSpec("form41_fuel", "Form 41 Schedule P-12(a) (monthly fuel cost and consumption)", 294,
                             "QO_fu146_anzr=Nv4%20Pn44vr4%20Sv0n0pvny", frozenset(FORM41_FUEL_FIELDS)),
    "master_coordinate": TableSpec("master_coordinate", "Aviation Support Tables: Master Coordinate", 288,
                                   "QO_fu146_anzr=N8vn6v10", frozenset(MASTER_COORDINATE_FIELDS), by_year=False),
}


def vq_encode(value: str) -> str:
    return "".join(
        _VQ[(_VQ.index(char) + 13) % len(_VQ)] if char in _VQ else char
        for char in value.lower()
    ).upper()


def table_url(spec: TableSpec) -> str:
    return f"{DL_FORM}?gnoyr_VQ={vq_encode(str(spec.table_id))}&{spec.db_query}"


def form_url(scope: str) -> str:
    try:
        table_id = TABLE_IDS[scope]
    except KeyError as exc:
        raise ValueError(f"Unsupported T-100 scope: {scope}") from exc
    return f"{DL_FORM}?gnoyr_VQ={vq_encode(str(table_id))}&{DB_NAME_QUERY}"


def _parse_form(html: str) -> tuple[dict[str, str], dict[str, str], set[str]]:
    hidden = {
        name: html_lib.unescape(value)
        for name, value in re.findall(
            r'<input\s+type="hidden"\s+name="([^"]+)"[^>]*value="([^"]*)"',
            html,
            flags=re.IGNORECASE,
        )
    }
    checkboxes = {
        name.upper(): name
        for name in re.findall(
            r'<input[^>]+type="checkbox"[^>]+name="([^"]+)"',
            html,
            flags=re.IGNORECASE,
        )
        if not name.lower().startswith("chk")
    }
    years = set(re.findall(r'<option[^>]+value="(\d{4})"', html, flags=re.IGNORECASE))
    if not hidden.get("__VIEWSTATE") or not hidden.get("__EVENTVALIDATION"):
        raise RuntimeError("TranStats form did not expose required ASP.NET state fields")
    if not checkboxes:
        raise RuntimeError("TranStats form did not expose selectable fields")
    return hidden, checkboxes, years


def _first_option(html: str, select_name: str) -> str | None:
    match = re.search(
        rf'<select[^>]+name="{re.escape(select_name)}"[^>]*>(.*?)</select>', html, flags=re.IGNORECASE | re.DOTALL
    )
    if not match:
        return None
    option = re.search(r'<option[^>]*value="([^"]*)"', match.group(1), flags=re.IGNORECASE)
    return option.group(1) if option else None


def fetch_table(spec: TableSpec, year: int | None, timeout: int) -> bytes:
    url = table_url(spec)
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    get_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    html = opener.open(urllib.request.Request(url, headers=get_headers), timeout=timeout).read().decode(
        "utf-8", "replace"
    )
    hidden, checkboxes, years = _parse_form(html)
    if spec.by_year:
        if not years:
            raise RuntimeError("TranStats form did not expose selectable years")
        year_text = str(year)
        if year_text not in years:
            raise RuntimeError(
                f"TranStats {spec.key} form does not offer year {year}; "
                f"available range is {min(years)}-{max(years)}"
            )
        geography, period = "All", "All"
    else:
        year_text = _first_option(html, "cboYear") or ""
        geography = _first_option(html, "cboGeography") or "All"
        period = _first_option(html, "cboPeriod") or "All"

    missing = sorted(set(spec.fields) - set(checkboxes))
    if missing:
        raise RuntimeError(f"TranStats form is missing required fields: {', '.join(missing)}")

    form = dict(hidden)
    form.update(
        {
            "btnDownload": "Download",
            "chkDownloadZip": "on",
            "cboGeography": geography,
            "cboYear": year_text,
            "cboPeriod": period,
        }
    )
    for field in spec.fields:
        form[checkboxes[field]] = "on"

    payload = urllib.parse.urlencode(form).encode()
    post_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/zip,application/octet-stream;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": url,
    }
    response = opener.open(
        urllib.request.Request(url, data=payload, headers=post_headers), timeout=timeout
    )
    raw = response.read()
    if raw[:2] != b"PK":
        detail = re.search(rb"alert\('([^']*)'\)", raw)
        message = detail.group(1).decode("utf-8", "replace") if detail else "non-ZIP response"
        raise RuntimeError(f"TranStats form download failed: {message}")
    return raw


def _fetch_once(scope: str, year: int, timeout: int) -> bytes:
    if scope not in TABLE_IDS:
        raise ValueError(f"Unsupported T-100 scope: {scope}")
    return fetch_table(TABLES[f"t100_{scope}"], year, timeout)


def download_table(
    spec: TableSpec,
    year: int | None,
    destination: Path,
    *,
    retries: int = 3,
    timeout: int = 600,
) -> None:
    """Download one TranStats table extract (one year, or the whole table if not yearly)."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    attempts = max(1, retries)
    last_error: Exception | None = None
    partial = destination.with_suffix(destination.suffix + ".part")
    for attempt in range(1, attempts + 1):
        try:
            raw = fetch_table(spec, year, timeout)
            partial.write_bytes(raw)
            partial.replace(destination)
            return
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as exc:
            last_error = exc
            if partial.exists():
                partial.unlink()
            if attempt < attempts:
                time.sleep(min(2**attempt, 10))
    raise RuntimeError(
        f"Failed to download TranStats {spec.key} {year or ''} after {attempts} attempts: {last_error}"
    )


def download_t100_year(
    scope: str,
    year: int,
    destination: Path,
    *,
    retries: int = 3,
    timeout: int = 600,
) -> None:
    """Download one annual T-100 segment extract from the official TranStats form."""
    if scope not in TABLE_IDS:
        raise ValueError(f"Unsupported T-100 scope: {scope}")
    download_table(TABLES[f"t100_{scope}"], year, destination, retries=retries, timeout=timeout)
