#!/usr/bin/env python3
"""Download BTS DB28 T-100 Segment annual archives for 2019-2025.

Files are saved under raw/t100/{scope}. Existing files are checksum-logged and
preserved unless --force is passed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "t100"
MANIFEST = ROOT / "raw" / "t100_history_download_manifest.csv"

URLS = {
    "domestic": {
        2019: "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/domestic-segments/DD.DB28DS.WAC.201901.201912.REL01.04MAR2020.zip",
        2020: "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/domestic-segments/DB28SEG.DD.WAC.202001.202012.REL01.02MAR2021.zip",
        2021: "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/domestic-segments/DB28SEG.DD.WAC.202101.202112.REL01.01MAR2022.zip",
        2022: "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/domestic-segments/DB28SEG.DD.WAC.202201.202212.REL01.01MAR2023.zip",
        2023: "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/domestic-segments/DB28SEG.DD.WAC.202301.202312.REL01.04MAR2024.zip",
        2024: "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/domestic-segments/DB28SEG.DD.WAC.202401.202412.REL01.04MAR2025.zip",
        2025: "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/domestic-segments/DB28SEG.DD.WAC.202501.202512.REL01.03MAR2026.zip",
    },
    "international": {
        2019: "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/international-segments/DB28SEG.FD.WAC.201901.201912.REL01.02JUN2020.zip",
        2020: "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/international-segments/DB28SEG.FD.WAC.202001.202012.REL01.02JUN2021.zip",
        2021: "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/international-segments/DB28SEG.FD.WAC.202101.202112.REL01.02JUN2022.zip",
        2022: "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/international-segments/DB28SEG.FD.WAC.202201.202212.REL01.19SEP2023.zip",
        2023: "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/international-segments/DB28SEG.FD.WAC.202301.202312.REL01.04MAR2024.zip",
        2024: "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/international-segments/DB28SEG.FD.WAC.202401.202412.REL01.04MAR2025.zip",
        2025: "https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/international-segments/DB28SEG.FD.WAC.202501.202512.REL01.03MAR2026.zip",
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, retries: int = 3) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".part")
    headers = {
        "User-Agent": "FinancialPlanningPerformanceDashboard/1.0 (+https://github.com/Boatengs/financial-planning-performance-dashboard)"
    }
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as response, partial.open("wb") as out:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            partial.replace(dest)
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if partial.exists():
                partial.unlink()
            if attempt < retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed after {retries} attempts: {url}: {last_error}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="*", type=int, default=list(range(2019, 2026)))
    ap.add_argument("--scope", choices=["domestic", "international", "both"], default="both")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    years = sorted(set(args.years))
    invalid = [y for y in years if y not in range(2019, 2026)]
    if invalid:
        raise SystemExit(f"Unsupported years in bundled manifest: {invalid}")
    scopes = ["domestic", "international"] if args.scope == "both" else [args.scope]

    records = []
    for scope in scopes:
        for year in years:
            url = URLS[scope][year]
            dest = RAW / scope / Path(url).name
            status = "planned"
            error = ""
            if args.dry_run:
                print(f"DRY RUN {scope} {year}: {url} -> {dest}")
            else:
                try:
                    if dest.exists() and not args.force:
                        status = "existing"
                    else:
                        print(f"Downloading {scope} {year}: {url}")
                        download(url, dest)
                        status = "downloaded"
                except Exception as exc:
                    status = "failed"
                    error = str(exc)
            records.append({
                "scope": scope,
                "year": year,
                "official_url": url,
                "local_file": str(dest.relative_to(ROOT)),
                "status": status,
                "size_bytes": dest.stat().st_size if dest.exists() else "",
                "sha256": sha256(dest) if dest.exists() else "",
                "error": error,
                "checked_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            })

    prior = []
    if MANIFEST.exists():
        with MANIFEST.open(newline="", encoding="utf-8") as f:
            prior = list(csv.DictReader(f))
    touched = {(r["scope"], str(r["year"])) for r in records}
    merged = [r for r in prior if (r["scope"], r["year"]) not in touched] + [
        {k: str(v) for k, v in r.items()} for r in records
    ]
    merged.sort(key=lambda r: (r["scope"], int(r["year"])))
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "scope",
        "year",
        "official_url",
        "local_file",
        "status",
        "size_bytes",
        "sha256",
        "error",
        "checked_at_utc",
    ]
    with MANIFEST.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(merged)

    failed = [r for r in records if r["status"] == "failed"]
    if failed:
        raise SystemExit(f"{len(failed)} downloads failed; see {MANIFEST}")


if __name__ == "__main__":
    main()
