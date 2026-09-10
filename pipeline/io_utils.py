from __future__ import annotations

import csv
import hashlib
import math
import re
from datetime import date, datetime
from pathlib import Path


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        if rows:
            w.writerows(rows)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def release_date_from_name(path: Path) -> str:
    m = re.search(r"\.(\d{2})([A-Z]{3})(\d{4})\.zip$", path.name.upper())
    if m:
        return datetime.strptime("".join(m.groups()), "%d%b%Y").date().isoformat()
    if "current_202506_202605" in path.name:
        return "2026-08-04"
    return "1900-01-01"


def infer_sql_type(values: list[str]) -> str:
    nonblank = [v for v in values if v not in (None, "")]
    if not nonblank:
        return "TEXT"
    try:
        for v in nonblank:
            int(v)
        return "INTEGER"
    except (ValueError, TypeError):
        pass
    try:
        for v in nonblank:
            x = float(v)
            if not math.isfinite(x):
                raise ValueError
        return "REAL"
    except (ValueError, TypeError):
        return "TEXT"


def coerce_sql(value: str, sql_type: str):
    if value in (None, ""):
        return None
    if sql_type == "INTEGER":
        return int(value)
    if sql_type == "REAL":
        return float(value)
    return value
