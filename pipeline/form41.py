"""BTS Form 41 schedules for the DL reporting carrier.

Schedule P-1.2 is the quarterly profit and loss statement each large U.S. carrier files
with the DOT, reported by operating region and in thousands of dollars. Schedule P-12(a)
is monthly fuel cost (dollars) and consumption (gallons). Both cover the same reporting
entity as T-100 (unique carrier DL), which makes per-ASM unit economics scope-consistent.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .config import PROCESSED, RAW
from .io_utils import write_csv

P12_AMOUNT_FIELDS = [
    "TRANS_REV_PAX", "MAIL", "TOTAL_PROPERTY", "PROP_FREIGHT", "PROP_BAG", "TOTAL_CHARTER", "TOTAL_MISC_REV",
    "RES_CANCEL_FEES", "MISC_OP_REV", "PUB_SVC_REVENUE", "TRANS_REVENUE", "OP_REVENUES", "FLYING_OPS",
    "MAINTENANCE", "PAX_SERVICE", "AIRCFT_SERVICES", "PROMOTION_SALES", "GENERAL_ADMIN", "GENERAL_SERVICES",
    "DEPREC_AMORT", "TRANS_EXPENSES", "OP_EXPENSES", "OP_PROFIT_LOSS", "INTEREST_LONG_DEBT", "NON_OP_INCOME",
    "INCOME_PRE_TAX", "INCOME_TAX", "NET_INCOME",
]
FUEL_FIELDS = ["SDOMT_GALLONS", "SINT_GALLONS", "TS_GALLONS", "TOTAL_GALLONS",
               "SDOMT_COST", "SINT_COST", "TS_COST", "TOTAL_COST"]
QUARTER_END = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}


def _normalize(name: str) -> str:
    return re.sub(r"[^0-9a-z]+", "_", name.strip().strip('"').lower()).strip("_").upper()


def _number(value, field) -> Decimal:
    text = str(value or "").strip()
    if not text:
        return Decimal(0)
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric value for {field}: {value!r}") from exc


def read_zip_csv(path: Path):
    with zipfile.ZipFile(path) as zf:
        members = [i for i in zf.infolist() if i.filename.lower().endswith(".csv")]
        if not members:
            raise ValueError(f"No CSV member found in {path}")
        member = max(members, key=lambda i: i.file_size)
        with zf.open(member) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline=""))
            if not reader.fieldnames:
                raise ValueError(f"{path.name}: CSV has no header")
            for row in reader:
                yield {_normalize(k): (v or "").strip() for k, v in row.items() if k}


def region_scope(region: str) -> str | None:
    """Map a P-1.2 operating region to the T-100 scope it corresponds to."""
    text = region.strip().lower()
    if not text:
        return None
    if text in {"d", "domestic"} or text.startswith("dom"):
        return "domestic"
    if text in {"a", "p", "l", "i"} or text.startswith(("atl", "pac", "lat", "int")):
        return "international"
    return None


def parse_p12(paths, carrier="DL"):
    rows, skipped_regions = [], defaultdict(int)
    for path in paths:
        for r in read_zip_csv(path):
            if r.get("UNIQUE_CARRIER", "").upper() != carrier:
                continue
            region = r.get("REGION", "")
            scope = region_scope(region)
            if scope is None:
                skipped_regions[region] += 1
                continue
            year, quarter = int(float(r["YEAR"])), int(float(r["QUARTER"]))
            out = {
                "year": year, "quarter": quarter, "period_label": f"{year}Q{quarter}",
                "period_end": f"{year}-{QUARTER_END[quarter]}", "scope": scope, "region": region,
                "carrier_entity": r.get("UNIQUE_CARRIER_ENTITY", ""), "source_file": path.name,
            }
            for field in P12_AMOUNT_FIELDS:
                out[field.lower()] = int(_number(r.get(field), field) * 1000)
            rows.append(out)
    keyed = {}
    for row in rows:
        key = (row["year"], row["quarter"], row["region"], row["carrier_entity"])
        keyed[key] = row  # later files (sorted by name) win for the same filing key
    result = sorted(keyed.values(), key=lambda r: (r["year"], r["quarter"], r["scope"], r["region"]))
    return result, dict(skipped_regions)


def parse_fuel(paths, carrier="DL"):
    keyed = {}
    for path in paths:
        for r in read_zip_csv(path):
            if r.get("UNIQUE_CARRIER", "").upper() != carrier:
                continue
            year, month = int(float(r["YEAR"])), int(float(r["MONTH"]))
            out = {"year": year, "month": month, "period": f"{year:04d}-{month:02d}-01",
                   "quarter": (month - 1) // 3 + 1, "source_file": path.name}
            for field in FUEL_FIELDS:
                out[field.lower()] = float(_number(r.get(field), field))
            keyed[(year, month)] = out
    return [keyed[k] for k in sorted(keyed)]


def quarterly_pnl_by_scope(p12_rows):
    """Collapse regions to domestic / international / system for each quarter."""
    agg = defaultdict(lambda: defaultdict(int))
    for r in p12_rows:
        for scope in (r["scope"], "system"):
            a = agg[(r["year"], r["quarter"], scope)]
            for field in P12_AMOUNT_FIELDS:
                a[field.lower()] += r[field.lower()]
    out = []
    for (year, quarter, scope), a in sorted(agg.items()):
        out.append({"year": year, "quarter": quarter, "period_label": f"{year}Q{quarter}",
                    "period_end": f"{year}-{QUARTER_END[quarter]}", "scope": scope, **a})
    return out


def quarterly_fuel_by_scope(fuel_rows):
    agg = defaultdict(lambda: defaultdict(float))
    months = defaultdict(set)
    for r in fuel_rows:
        key = (r["year"], r["quarter"])
        months[key].add(r["month"])
        for scope, gal, cost in (("domestic", "sdomt_gallons", "sdomt_cost"),
                                 ("international", "sint_gallons", "sint_cost"),
                                 ("system", "ts_gallons", "ts_cost")):
            agg[key + (scope,)]["scheduled_fuel_gallons"] += r[gal]
            agg[key + (scope,)]["scheduled_fuel_cost"] += r[cost]
    out = []
    for (year, quarter, scope), a in sorted(agg.items()):
        out.append({"year": year, "quarter": quarter, "period_label": f"{year}Q{quarter}", "scope": scope,
                    "months_reported": len(months[(year, quarter)]), **a})
    return out


def build_form41(raw_root: Path | None = None):
    raw_root = raw_root or RAW / "form41"
    p12_paths = sorted((raw_root / "p12").glob("*.zip"))
    fuel_paths = sorted((raw_root / "fuel").glob("*.zip"))
    if not p12_paths or not fuel_paths:
        raise FileNotFoundError(
            "Form 41 extracts are missing; run scripts/download_bts_tables.py --tables form41_p12 form41_fuel"
        )
    p12_rows, skipped = parse_p12(p12_paths)
    fuel_rows = parse_fuel(fuel_paths)
    pnl = quarterly_pnl_by_scope(p12_rows)
    fuel_q = quarterly_fuel_by_scope(fuel_rows)
    write_csv(PROCESSED / "fact_form41_pnl_region.csv", p12_rows)
    write_csv(PROCESSED / "fact_form41_pnl_quarterly.csv", pnl)
    write_csv(PROCESSED / "fact_fuel_monthly.csv", fuel_rows)
    write_csv(PROCESSED / "fact_fuel_quarterly.csv", fuel_q)
    return {
        "p12_rows": p12_rows, "pnl_quarterly": pnl, "fuel_monthly": fuel_rows, "fuel_quarterly": fuel_q,
        "skipped_regions": skipped, "sources": p12_paths + fuel_paths,
        "regions_seen": sorted({r["region"] for r in p12_rows}),
    }
