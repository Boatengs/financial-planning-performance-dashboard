#!/usr/bin/env python3
"""Download BTS Form 41 schedules and the Master Coordinate airport table from TranStats.

Form 41 P-1.2 (quarterly profit and loss) and P-12(a) (monthly fuel) are downloaded one
calendar year per request. Master Coordinate is a single reference table. Each file is
recorded with its form URL, size, SHA-256 checksum and acquisition time in
raw/bts_download_manifest.csv. Existing files are reused unless --force is given or the
year is listed in --refresh-years (use this for the current, still-filling year).
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

from pipeline.transtats import TABLES, download_table, table_url

RAW = ROOT / "raw"
MANIFEST = RAW / "bts_download_manifest.csv"
SUPPORTED_YEARS = range(2019, 2027)
DESTINATIONS = {
    "form41_p12": lambda year: RAW / "form41" / "p12" / f"form41_p12_{year}.zip",
    "form41_fuel": lambda year: RAW / "form41" / "fuel" / f"form41_fuel_{year}.zip",
    "master_coordinate": lambda year: RAW / "bts" / "master_coordinate.zip",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tables", nargs="*", choices=sorted(DESTINATIONS), default=sorted(DESTINATIONS))
    ap.add_argument("--years", nargs="*", type=int, default=list(SUPPORTED_YEARS))
    ap.add_argument("--refresh-years", nargs="*", type=int, default=[])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--retries", type=int, default=3)
    args = ap.parse_args()

    invalid = [y for y in args.years if y not in SUPPORTED_YEARS]
    if invalid:
        raise SystemExit(f"Unsupported years: {invalid}; supported range is 2019-2026")
    acquired_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    records = []
    for key in args.tables:
        spec = TABLES[key]
        years = sorted(set(args.years)) if spec.by_year else [None]
        for year in years:
            dest = DESTINATIONS[key](year)
            refresh = args.force or (year is not None and year in args.refresh_years)
            status, error = "existing", ""
            try:
                if refresh or not dest.exists():
                    print(f"Downloading TranStats {key} {year or ''}".rstrip())
                    download_table(spec, year, dest, retries=max(1, args.retries))
                    status = "downloaded"
            except Exception as exc:  # recorded in the manifest, reported below
                status, error = "failed", str(exc)
            records.append({
                "table": key, "table_id": spec.table_id, "year": year or "", "official_url": table_url(spec),
                "local_file": str(dest.relative_to(ROOT)), "status": status,
                "size_bytes": dest.stat().st_size if dest.exists() else "",
                "sha256": sha256(dest) if dest.exists() else "", "error": error, "checked_at_utc": acquired_at,
            })

    prior = []
    if MANIFEST.exists():
        with MANIFEST.open(newline="", encoding="utf-8") as f:
            prior = list(csv.DictReader(f))
    touched = {(r["table"], str(r["year"])) for r in records}
    merged = [r for r in prior if (r.get("table", ""), r.get("year", "")) not in touched]
    merged += [{k: str(v) for k, v in r.items()} for r in records]
    merged.sort(key=lambda r: (r["table"], r["year"]))
    fields = ["table", "table_id", "year", "official_url", "local_file", "status", "size_bytes", "sha256",
              "error", "checked_at_utc"]
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(merged)

    failed = [r for r in records if r["status"] == "failed"]
    if failed:
        for r in failed:
            print(f"FAILED {r['table']} {r['year']}: {r['error']}", file=sys.stderr)
        raise SystemExit(f"{len(failed)} TranStats downloads failed; see {MANIFEST}")


if __name__ == "__main__":
    main()
