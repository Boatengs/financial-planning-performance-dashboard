#!/usr/bin/env python3
"""Download annual BTS T-100 Segment extracts from the official TranStats form.

Each requested calendar year is downloaded directly from TranStats for domestic
and/or international segment data. Extracts are stored under raw/t100/{scope}
and recorded with URL, table ID, size, checksum, and acquisition timestamp.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.transtats import TABLE_IDS, download_t100_year, form_url

RAW = ROOT / "raw" / "t100"
MANIFEST = ROOT / "raw" / "t100_history_download_manifest.csv"
SUPPORTED_YEARS = range(2019, 2027)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", nargs="*", type=int, default=list(SUPPORTED_YEARS))
    ap.add_argument("--scope", choices=["domestic", "international", "both"], default="both")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--retries", type=int, default=3)
    args = ap.parse_args()

    years = sorted(set(args.years))
    supported = set(SUPPORTED_YEARS)
    invalid = [year for year in years if year not in supported]
    if invalid:
        raise SystemExit(f"Unsupported years: {invalid}; supported range is 2019-2026")
    scopes = ["domestic", "international"] if args.scope == "both" else [args.scope]
    acquired_at = datetime.now(timezone.utc).replace(microsecond=0)
    snapshot_tag = acquired_at.strftime("%Y%m%d")

    records = []
    for scope in scopes:
        for year in years:
            url = form_url(scope)
            dest = RAW / scope / f"transtats_{scope}_{year}.snapshot_{snapshot_tag}.zip"
            status = "planned"
            error = ""
            if args.dry_run:
                print(f"DRY RUN {scope} {year}: {url} -> {dest}")
            else:
                try:
                    if dest.exists() and not args.force:
                        status = "existing"
                    else:
                        print(f"Downloading TranStats {scope} T-100 Segment {year}")
                        download_t100_year(
                            scope,
                            year,
                            dest,
                            retries=max(1, args.retries),
                        )
                        status = "downloaded"
                except Exception as exc:
                    status = "failed"
                    error = str(exc)
            records.append(
                {
                    "scope": scope,
                    "year": year,
                    "table_id": TABLE_IDS[scope],
                    "official_url": url,
                    "local_file": str(dest.relative_to(ROOT)),
                    "status": status,
                    "size_bytes": dest.stat().st_size if dest.exists() else "",
                    "sha256": sha256(dest) if dest.exists() else "",
                    "error": error,
                    "checked_at_utc": acquired_at.isoformat().replace("+00:00", "Z"),
                }
            )

    prior = []
    if MANIFEST.exists():
        with MANIFEST.open(newline="", encoding="utf-8") as f:
            prior = list(csv.DictReader(f))
    touched = {(record["scope"], str(record["year"])) for record in records}
    merged = [
        record
        for record in prior
        if (record.get("scope", ""), record.get("year", "")) not in touched
    ] + [{key: str(value) for key, value in record.items()} for record in records]
    merged.sort(key=lambda record: (record["scope"], int(record["year"])))

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "scope",
        "year",
        "table_id",
        "official_url",
        "local_file",
        "status",
        "size_bytes",
        "sha256",
        "error",
        "checked_at_utc",
    ]
    with MANIFEST.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(merged)

    failed = [record for record in records if record["status"] == "failed"]
    if failed:
        raise SystemExit(f"{len(failed)} TranStats downloads failed; see {MANIFEST}")


if __name__ == "__main__":
    main()
