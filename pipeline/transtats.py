from __future__ import annotations

import html as html_lib
import http.cookiejar
import re
import time
import urllib.error
import urllib.parse
import urllib.request
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


def vq_encode(value: str) -> str:
    return "".join(
        _VQ[(_VQ.index(char) + 13) % len(_VQ)] if char in _VQ else char
        for char in value.lower()
    ).upper()


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
    if not years:
        raise RuntimeError("TranStats form did not expose selectable years")
    return hidden, checkboxes, years


def _fetch_once(scope: str, year: int, timeout: int) -> bytes:
    url = form_url(scope)
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
    year_text = str(year)
    if year_text not in years:
        raise RuntimeError(
            f"TranStats {scope} segment form does not offer year {year}; "
            f"available range is {min(years)}-{max(years)}"
        )

    missing = sorted(REQUIRED_FORM_FIELDS - set(checkboxes))
    if missing:
        raise RuntimeError(f"TranStats form is missing required fields: {', '.join(missing)}")

    form = dict(hidden)
    form.update(
        {
            "btnDownload": "Download",
            "chkDownloadZip": "on",
            "cboGeography": "All",
            "cboYear": year_text,
            "cboPeriod": "All",
        }
    )
    for field in REQUIRED_FORM_FIELDS:
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


def download_t100_year(
    scope: str,
    year: int,
    destination: Path,
    *,
    retries: int = 3,
    timeout: int = 600,
) -> None:
    """Download one annual T-100 segment extract from the official TranStats form."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    attempts = max(1, retries)
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            raw = _fetch_once(scope, year, timeout)
            partial = destination.with_suffix(destination.suffix + ".part")
            partial.write_bytes(raw)
            partial.replace(destination)
            return
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as exc:
            last_error = exc
            partial = destination.with_suffix(destination.suffix + ".part")
            if partial.exists():
                partial.unlink()
            if attempt < attempts:
                time.sleep(min(2**attempt, 10))
    raise RuntimeError(
        f"Failed to download TranStats {scope} T-100 segment year {year} "
        f"after {attempts} attempts: {last_error}"
    )
