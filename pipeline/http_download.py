from __future__ import annotations

import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Safari/537.36"
)
DEFAULT_SEC_USER_AGENT = (
    "FinancialPlanningPerformanceDashboard/1.0 "
    "32736261+Boatengs@users.noreply.github.com"
)


def request_headers(url: str) -> dict[str, str]:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if host == "data.sec.gov" or host.endswith(".sec.gov"):
        return {
            "User-Agent": os.environ.get("SEC_USER_AGENT", DEFAULT_SEC_USER_AGENT),
            "Accept": "application/json,text/plain;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        }
    if host == "www.bts.gov" or host.endswith(".bts.gov"):
        return {
            "User-Agent": os.environ.get("BTS_USER_AGENT", BROWSER_USER_AGENT),
            "Accept": "application/zip,application/octet-stream;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.bts.gov/",
        }
    return {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _validate_payload(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError(f"Downloaded file is empty: {path}")
    if path.suffix.lower() == ".zip":
        with path.open("rb") as handle:
            signature = handle.read(4)
        if signature not in {b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"}:
            raise ValueError(f"Downloaded payload is not a ZIP archive: {path}")


def _download_with_urllib(url: str, destination: Path, timeout: int) -> None:
    request = urllib.request.Request(url, headers=request_headers(url))
    with urllib.request.urlopen(request, timeout=timeout) as response, destination.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)


def _download_with_curl(url: str, destination: Path, timeout: int) -> None:
    headers = request_headers(url)
    command = [
        "curl",
        "--fail",
        "--location",
        "--silent",
        "--show-error",
        "--connect-timeout",
        "30",
        "--max-time",
        str(timeout),
        "--retry",
        "2",
        "--retry-delay",
        "2",
        "--output",
        str(destination),
    ]
    for name, value in headers.items():
        if name.lower() == "user-agent":
            command.extend(["--user-agent", value])
        else:
            command.extend(["--header", f"{name}: {value}"])
    command.append(url)
    subprocess.run(command, check=True)


def _is_bts(url: str) -> bool:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return host == "www.bts.gov" or host.endswith(".bts.gov")


def download_file(
    url: str,
    destination: Path,
    *,
    retries: int = 3,
    timeout: int = 180,
) -> None:
    """Download one public source file with validation and BTS fallback handling."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    attempts = max(1, retries)
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        if partial.exists():
            partial.unlink()
        try:
            _download_with_urllib(url, partial, timeout)
            _validate_payload(partial)
            partial.replace(destination)
            return
        except urllib.error.HTTPError as exc:
            last_error = exc
            if partial.exists():
                partial.unlink()
            if _is_bts(url) and exc.code in {403, 429}:
                try:
                    _download_with_curl(url, partial, timeout)
                    _validate_payload(partial)
                    partial.replace(destination)
                    return
                except (subprocess.CalledProcessError, OSError, ValueError) as curl_exc:
                    last_error = curl_exc
                    if partial.exists():
                        partial.unlink()
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = exc
            if partial.exists():
                partial.unlink()

        if attempt < attempts:
            time.sleep(min(2**attempt, 10))

    raise RuntimeError(f"Failed to download {url} after {attempts} attempts: {last_error}")
