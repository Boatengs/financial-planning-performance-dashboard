#!/usr/bin/env python3
"""Download raw inputs required by the financial and network data models.

Files are retrieved from SEC, Delta Investor Relations, BTS, and FAA publisher
endpoints, written to the paths expected by the build pipelines, and checksum-logged.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"

SOURCES = [
    (
        "SEC CompanyFacts",
        "financial",
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0000027904.json",
        RAW / "delta_companyfacts.json",
    ),
    (
        "Delta 2025 10-K XBRL workbook",
        "financial",
        "https://d18rn0p25nwr6d.cloudfront.net/CIK-0000027904/0db061b6-3e78-4a3a-8131-9b65c5210ab7.xls",
        RAW / "delta_2025_10k.xls",
    ),
    (
        "Delta 2026 Q2 10-Q XBRL workbook",
        "financial",
        "https://d18rn0p25nwr6d.cloudfront.net/CIK-0000027904/47a4a84f-7c64-4145-b2b4-288bed9a4037.xls",
        RAW / "delta_2026_q2_10q.xls",
    ),
    (
        "FAA NASR airport CSV",
        "network",
        "https://nfdc.faa.gov/webContent/28DaySub/extra/03_Sep_2026_APT_CSV.zip",
        RAW / "faa_airports_2026-09-03.zip",
    ),
    (
        "BTS T-100 Domestic Segment",
        "network",
        "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/domestic-segments/DB28SEG.DD.WAC.202506.202605.REL01.04AUG2026.zip",
        RAW / "t100" / "domestic" / "current_202506_202605.zip",
    ),
    (
        "BTS T-100 International Segment",
        "network",
        "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/international-segments/DB28SEG.FD.WAC.202506.202605.REL01.04AUG2026.zip",
        RAW / "t100" / "international" / "current_202506_202605.zip",
    ),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(label: str, url: str, destination: Path, *, force: bool, retries: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        print(f"SKIP  {label}: {destination.relative_to(ROOT)} sha256={sha256(destination)}")
        return

    headers = {
        "User-Agent": os.environ.get(
            "SEC_USER_AGENT",
            "FinancialPlanningPerformanceDashboard/1.0 (+https://github.com/Boatengs/financial-planning-performance-dashboard)",
        ),
        "Accept": "*/*",
    }
    request = urllib.request.Request(url, headers=headers)
    tmp = destination.with_suffix(destination.suffix + ".part")

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=90) as response, tmp.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
            tmp.replace(destination)
            print(
                f"OK    {label}: {destination.relative_to(ROOT)} "
                f"bytes={destination.stat().st_size} sha256={sha256(destination)}"
            )
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if tmp.exists():
                tmp.unlink()
            if attempt < retries:
                time.sleep(min(2**attempt, 10))
    raise RuntimeError(f"Failed to download {label} after {retries} attempts: {last_error}")


def select_sources(group: str):
    if group == "all":
        return SOURCES
    return [source for source in SOURCES if source[1] == group]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--group",
        choices=("all", "financial", "network"),
        default="all",
        help="Source domain to acquire (default: all)",
    )
    parser.add_argument("--force", action="store_true", help="Re-download files that already exist")
    parser.add_argument("--retries", type=int, default=3, help="Download attempts per source (default: 3)")
    args = parser.parse_args()

    for label, _group, url, destination in select_sources(args.group):
        download(label, url, destination, force=args.force, retries=max(1, args.retries))


if __name__ == "__main__":
    main()
