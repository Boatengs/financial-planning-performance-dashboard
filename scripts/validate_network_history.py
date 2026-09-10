#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.network_history import validate_network_history


def main() -> None:
    report = validate_network_history()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
