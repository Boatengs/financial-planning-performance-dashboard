#!/usr/bin/env python3
"""Write a dated snapshot of SEC CompanyFacts filtered to the concepts the model uses.

Usage: python scripts/subset_companyfacts.py [path/to/CIK0000027904.json]

The full CompanyFacts file is about 3 MB and SEC blocks downloads from some cloud networks,
so the build falls back to this committed snapshot when a fresh download is not available.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.config import ANALYSIS_START_YEAR, FINANCIAL_METRICS, RAW
from pipeline.financials import load_companyfacts

KEEP = ("start", "end", "val", "accn", "fy", "fp", "form", "filed", "frame")


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else RAW / "delta_companyfacts.json"
    data = load_companyfacts(source)
    out = {"cik": data["cik"], "entityName": data["entityName"], "facts": {}}
    for spec in FINANCIAL_METRICS.values():
        ns = data["facts"].get(spec["namespace"], {})
        for tag in spec["tags"]:
            if tag not in ns:
                continue
            units = {k: [{f: x.get(f) for f in KEEP} for x in v if (x.get("fy") or 0) >= ANALYSIS_START_YEAR]
                     for k, v in ns[tag]["units"].items()}
            out["facts"].setdefault(spec["namespace"], {})[tag] = {"label": ns[tag].get("label"), "units": units}
    target = RAW / "sec" / f"companyfacts_subset_{date.today().isoformat()}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out), encoding="utf-8")
    print(f"Wrote {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
