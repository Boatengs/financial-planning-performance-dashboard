#!/usr/bin/env python3
"""Download fixed raw inputs required by the financial and network data models.

SEC and Delta filing inputs plus the FAA NASR reference file are acquired here.
T-100 annual extracts are acquired separately from the official BTS TranStats form
by ``download_t100_history.py``.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.http_download import download_file

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

    download_file(url, destination, retries=max(1, retries))
    print(
        f"OK    {label}: {destination.relative_to(ROOT)} "
        f"bytes={destination.stat().st_size} sha256={sha256(destination)}"
    )


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
        help="Fixed-source domain to acquire (default: all)",
    )
    parser.add_argument("--force", action="store_true", help="Re-download files that already exist")
    parser.add_argument("--retries", type=int, default=3, help="Download attempts per source (default: 3)")
    args = parser.parse_args()

    for label, _group, url, destination in select_sources(args.group):
        download(label, url, destination, force=args.force, retries=max(1, args.retries))


if __name__ == "__main__":
    main()
