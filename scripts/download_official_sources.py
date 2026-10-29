#!/usr/bin/env python3
"""Download fixed raw inputs required by the financial and network data models.

SEC CompanyFacts and the FAA NASR airport reference file are acquired here.
T-100, Form 41 and Master Coordinate extracts come from the BTS TranStats forms via
``download_t100_history.py`` and ``download_bts_tables.py``.
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
