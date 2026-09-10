from __future__ import annotations

import json
import re

from .config import FINANCIAL_METRICS, PROCESSED, RAW
from .io_utils import write_csv


def frame_period(frame: str | None):
    if not frame:
        return None, None
    m = re.fullmatch(r"CY(\d{4})", frame)
    if m:
        return f"{m.group(1)}-12-31", "FY"
    m = re.fullmatch(r"CY(\d{4})Q([1-4])I?", frame)
    if m:
        y, q = int(m.group(1)), int(m.group(2))
        end_month = q * 3
        end_day = {3: 31, 6: 30, 9: 30, 12: 31}[end_month]
        return f"{y:04d}-{end_month:02d}-{end_day:02d}", f"Q{q}"
    return None, None


def build_financial_actuals():
    d = json.load((RAW / "delta_companyfacts.json").open(encoding="utf-8"))
    if int(d.get("cik", -1)) != 27904 or "DELTA AIR LINES" not in d.get("entityName", "").upper():
        raise AssertionError("CompanyFacts entity check failed; expected Delta Air Lines CIK 27904")
    facts = d["facts"]
    output, metric_meta = [], []
    for metric_id, spec in FINANCIAL_METRICS.items():
        ns = facts.get(spec["namespace"], {})
        selected_tag = next((t for t in spec["tags"] if t in ns), None)
        if not selected_tag:
            metric_meta.append({**spec, "metric_id": metric_id, "selected_tag": "", "available": 0})
            continue
        fact = ns[selected_tag]
        units = fact.get("units", {})
        unit_key = spec["unit"] if spec["unit"] in units else next(iter(units), None)
        if not unit_key:
            metric_meta.append({**spec, "metric_id": metric_id, "selected_tag": selected_tag, "available": 0})
            continue
        candidates = {}
        for item in units[unit_key]:
            period_end, period_type = frame_period(item.get("frame"))
            if not period_end or not (2019 <= int(period_end[:4]) <= 2026):
                continue
            if item.get("form") not in {"10-K", "10-Q", "10-K/A", "10-Q/A"}:
                continue
            key = (metric_id, period_end, period_type)
            filed = item.get("filed") or ""
            if key not in candidates or filed >= (candidates[key].get("filed") or ""):
                candidates[key] = item
        for (mid, period_end, period_type), item in candidates.items():
            output.append({
                "metric_id": mid, "metric_name": spec["label"], "domain": spec["domain"], "period_end": period_end,
                "period_type": period_type, "value": item.get("val"), "unit": unit_key,
                "taxonomy_namespace": spec["namespace"], "taxonomy_tag": selected_tag,
                "form": item.get("form"), "fiscal_year": item.get("fy"), "fiscal_period": item.get("fp"),
                "filed_date": item.get("filed"), "accession_number": item.get("accn"), "frame": item.get("frame"),
                "source": "SEC CompanyFacts"
            })
        metric_meta.append({**spec, "metric_id": metric_id, "selected_tag": selected_tag, "available": len(candidates)})
    output.sort(key=lambda r: (r["period_end"], r["metric_id"]))
    write_csv(PROCESSED / "fact_financial_actual.csv", output)
    return output, metric_meta


def build_financial_derived(financial_rows):
    by_key = {(r["metric_id"], r["period_end"], r["period_type"]): r for r in financial_rows}
    rows = []

    for (metric_id, period_end, period_type), revenue in sorted(by_key.items()):
        if metric_id != "revenue":
            continue
        op = by_key.get(("operating_income", period_end, period_type))
        rev = revenue.get("value")
        if op is None or rev in (None, 0):
            continue
        rows.append({
            "metric_id": "operating_margin", "metric_name": "Operating Margin", "domain": "Profitability",
            "period_end": period_end, "period_type": period_type, "value": float(op["value"]) / float(rev), "unit": "%",
            "formula": "operating_income / revenue", "input_metric_ids": "operating_income,revenue",
            "source": "Derived from SEC CompanyFacts"
        })

    for (metric_id, period_end, period_type), revenue in sorted(by_key.items()):
        if metric_id != "revenue":
            continue
        year = int(period_end[:4])
        prior_end = f"{year-1:04d}{period_end[4:]}"
        prior = by_key.get(("revenue", prior_end, period_type))
        cur = revenue.get("value")
        prev = prior.get("value") if prior else None
        if cur is None or prev in (None, 0):
            continue
        rows.append({
            "metric_id": "revenue_growth_yoy", "metric_name": "Revenue Growth YoY", "domain": "Financial Performance",
            "period_end": period_end, "period_type": period_type, "value": float(cur) / float(prev) - 1.0, "unit": "%",
            "formula": "revenue_t / revenue_t-1year - 1", "input_metric_ids": "revenue",
            "source": "Derived from SEC CompanyFacts"
        })

    rows.sort(key=lambda r: (r["period_end"], r["metric_id"]))
    write_csv(PROCESSED / "fact_financial_kpi_derived.csv", rows, [
        "metric_id", "metric_name", "domain", "period_end", "period_type", "value", "unit",
        "formula", "input_metric_ids", "source"
    ])
    return rows
