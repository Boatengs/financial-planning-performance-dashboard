"""Consolidated Delta Air Lines financial actuals from SEC CompanyFacts.

CompanyFacts only assigns a calendar "frame" to one fact per period, and SEC does not
publish standalone fourth quarters or standalone quarterly cash flows. Selecting facts by
frame therefore drops every Q4 and every Q2/Q3 cash-flow quarter. This module works from
each fact's reported start and end dates instead:

* a reported three-month fact is used as is (method ``reported``);
* Q2 and Q3 cash-flow amounts are the difference between consecutive year-to-date facts
  (method ``derived_ytd_difference``);
* Q4 is the full-year fact minus the nine-month year-to-date fact
  (method ``derived_fy_minus_9m``).

Balance-sheet (instant) facts are read at each quarter end.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from .config import ANALYSIS_END_YEAR, ANALYSIS_START_YEAR, DERIVED_KPIS, FINANCIAL_METRICS, PROCESSED, RAW
from .io_utils import write_csv

DELTA_CIK = 27904
ANNUAL_AND_QUARTERLY_FORMS = {"10-K", "10-Q", "10-K/A", "10-Q/A"}
QUARTER_ENDS = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}

FINANCIAL_FIELDS = [
    "metric_id", "metric_name", "domain", "period_label", "period_type", "fiscal_year", "fiscal_quarter",
    "period_start", "period_end", "value", "unit", "method", "taxonomy_namespace", "taxonomy_tag",
    "form", "filed_date", "accession_number", "source",
]
DERIVED_FIELDS = [
    "metric_id", "metric_name", "domain", "period_label", "period_type", "fiscal_year", "fiscal_quarter",
    "period_start", "period_end", "value", "unit", "formula", "input_metric_ids", "source",
]


def quarter_bounds(year: int, quarter: int) -> tuple[str, str]:
    start_month = (quarter - 1) * 3 + 1
    end_month, end_day = QUARTER_ENDS[quarter]
    return date(year, start_month, 1).isoformat(), date(year, end_month, end_day).isoformat()


def _duration_days(item: dict) -> int | None:
    if not item.get("start") or not item.get("end"):
        return None
    return (date.fromisoformat(item["end"]) - date.fromisoformat(item["start"])).days


def _latest_by_period(items: list[dict], *, instant: bool) -> dict:
    """Keep the most recently filed fact for each reported period."""
    chosen: dict = {}
    for item in items:
        if item.get("form") not in ANNUAL_AND_QUARTERLY_FORMS or item.get("val") is None:
            continue
        key = item["end"] if instant else (item.get("start"), item["end"])
        if not instant and key[0] is None:
            continue
        current = chosen.get(key)
        if current is None or (item.get("filed") or "") >= (current.get("filed") or ""):
            chosen[key] = item
    return chosen


def load_companyfacts(path: Path | None = None) -> dict:
    path = path or RAW / "delta_companyfacts.json"
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if int(data.get("cik", -1)) != DELTA_CIK or "DELTA AIR LINES" not in data.get("entityName", "").upper():
        raise AssertionError("CompanyFacts entity check failed; expected Delta Air Lines CIK 27904")
    return data


def _row(metric_id, spec, tag, unit, *, period_type, year, quarter, start, end, value, method, sources):
    label = f"{year}FY" if period_type == "FY" else f"{year}Q{quarter}"
    return {
        "metric_id": metric_id, "metric_name": spec["label"], "domain": spec["domain"],
        "period_label": label, "period_type": period_type, "fiscal_year": year,
        "fiscal_quarter": "" if period_type == "FY" else quarter,
        "period_start": start or "", "period_end": end, "value": value, "unit": unit, "method": method,
        "taxonomy_namespace": spec["namespace"], "taxonomy_tag": tag,
        "form": ";".join(sorted({s.get("form", "") for s in sources})),
        "filed_date": max((s.get("filed") or "") for s in sources),
        "accession_number": ";".join(sorted({s.get("accn", "") for s in sources})),
        "source": "SEC CompanyFacts",
    }


def _duration_rows(metric_id, spec, tag, unit, facts, years):
    rows = []
    for year in years:
        jan1 = date(year, 1, 1).isoformat()
        fy = facts.get((jan1, date(year, 12, 31).isoformat()))
        if fy and 350 <= _duration_days(fy) <= 380:
            rows.append(_row(metric_id, spec, tag, unit, period_type="FY", year=year, quarter=None,
                             start=jan1, end=fy["end"], value=fy["val"], method="reported", sources=[fy]))
        for quarter in range(1, 5):
            start, end = quarter_bounds(year, quarter)
            direct = facts.get((start, end))
            if direct is not None:
                rows.append(_row(metric_id, spec, tag, unit, period_type=f"Q{quarter}", year=year, quarter=quarter,
                                 start=start, end=end, value=direct["val"], method="reported", sources=[direct]))
                continue
            if quarter == 4:
                nine = facts.get((jan1, quarter_bounds(year, 3)[1]))
                if fy is not None and nine is not None:
                    rows.append(_row(metric_id, spec, tag, unit, period_type="Q4", year=year, quarter=4,
                                     start=start, end=end, value=fy["val"] - nine["val"],
                                     method="derived_fy_minus_9m", sources=[fy, nine]))
                continue
            ytd = facts.get((jan1, end))
            prior_end = quarter_bounds(year, quarter - 1)[1] if quarter > 1 else None
            prior_ytd = facts.get((jan1, prior_end)) if prior_end else None
            if ytd is not None and prior_ytd is not None:
                rows.append(_row(metric_id, spec, tag, unit, period_type=f"Q{quarter}", year=year, quarter=quarter,
                                 start=start, end=end, value=ytd["val"] - prior_ytd["val"],
                                 method="derived_ytd_difference", sources=[ytd, prior_ytd]))
    return rows


def _instant_rows(metric_id, spec, tag, unit, facts, years):
    rows = []
    for year in years:
        for quarter in range(1, 5):
            _, end = quarter_bounds(year, quarter)
            item = facts.get(end)
            if item is None:
                continue
            rows.append(_row(metric_id, spec, tag, unit, period_type=f"Q{quarter}", year=year, quarter=quarter,
                             start=None, end=end, value=item["val"], method="reported", sources=[item]))
            if quarter == 4:
                rows.append(_row(metric_id, spec, tag, unit, period_type="FY", year=year, quarter=None,
                                 start=None, end=end, value=item["val"], method="reported", sources=[item]))
    return rows


def extract_financial_actuals(data: dict, years=range(ANALYSIS_START_YEAR, ANALYSIS_END_YEAR + 1)):
    output, metric_meta = [], []
    for metric_id, spec in FINANCIAL_METRICS.items():
        namespace = data["facts"].get(spec["namespace"], {})
        tag = next((t for t in spec["tags"] if t in namespace), None)
        units = namespace[tag].get("units", {}) if tag else {}
        unit = spec["unit"] if spec["unit"] in units else next(iter(units), None)
        if not tag or not unit:
            metric_meta.append({**spec, "metric_id": metric_id, "selected_tag": tag or "", "available": 0})
            continue
        instant = spec["kind"] == "instant"
        facts = _latest_by_period(units[unit], instant=instant)
        if instant:
            rows = _instant_rows(metric_id, spec, tag, unit, facts, years)
        else:
            rows = _duration_rows(metric_id, spec, tag, unit, facts, years)
        output.extend(rows)
        metric_meta.append({**spec, "metric_id": metric_id, "selected_tag": tag, "available": len(rows)})
    added = _fill_capex_total_from_components(output)
    for meta in metric_meta:
        if meta["metric_id"] == "capex_total":
            meta["available"] += added
    output.sort(key=lambda r: (r["period_end"], r["period_type"] == "FY", r["metric_id"]))
    return output, metric_meta


def _fill_capex_total_from_components(rows) -> int:
    """Delta stopped tagging total capex in 2026 filings but still tags both components.

    Total capex = flight equipment + ground property, equipment and technology. Where all three
    are tagged, the identity holds to within $2 million of rounding (SEC values are in millions).
    """
    by_key = {(r["metric_id"], r["period_label"]): r for r in rows}
    labels = {r["period_label"] for r in rows if r["metric_id"] == "capex_flight_equipment"}
    added = 0
    for label in sorted(labels):
        if ("capex_total", label) in by_key:
            continue
        flight = by_key.get(("capex_flight_equipment", label))
        ground = by_key.get(("capex_ground_technology", label))
        if flight is None or ground is None:
            continue
        spec = FINANCIAL_METRICS["capex_total"]
        row = dict(flight)
        row.update({
            "metric_id": "capex_total", "metric_name": spec["label"], "domain": spec["domain"],
            "value": flight["value"] + ground["value"], "method": "derived_sum_of_components",
            "taxonomy_tag": f'{flight["taxonomy_tag"]}+{ground["taxonomy_tag"]}',
            "accession_number": ";".join(sorted(set(flight["accession_number"].split(";"))
                                                | set(ground["accession_number"].split(";")))),
        })
        rows.append(row)
        added += 1
    return added


def build_financial_actuals(path: Path | None = None):
    output, metric_meta = extract_financial_actuals(load_companyfacts(path))
    write_csv(PROCESSED / "fact_financial_actual.csv", output, FINANCIAL_FIELDS)
    return output, metric_meta


def quarterly_reconciliation(rows):
    """Sum of four quarters versus the reported full year, for every duration metric and year."""
    by_key = {(r["metric_id"], r["period_label"]): r for r in rows}
    checks = []
    for metric_id, spec in FINANCIAL_METRICS.items():
        if spec["kind"] != "duration":
            continue
        years = {r["fiscal_year"] for r in rows if r["metric_id"] == metric_id and r["period_type"] == "FY"}
        for year in sorted(years):
            quarters = [by_key.get((metric_id, f"{year}Q{q}")) for q in range(1, 5)]
            if any(q is None for q in quarters):
                continue
            fy = by_key[(metric_id, f"{year}FY")]["value"]
            total = sum(q["value"] for q in quarters)
            checks.append({"metric_id": metric_id, "fiscal_year": year, "full_year": fy,
                           "sum_of_quarters": total, "difference": total - fy})
    return checks


def build_financial_derived(financial_rows):
    by_key = {(r["metric_id"], r["period_label"]): r for r in financial_rows}
    periods = {(r["period_label"], r["period_type"], r["fiscal_year"], r["fiscal_quarter"],
                r["period_start"], r["period_end"]) for r in financial_rows if r["metric_id"] == "revenue"}
    periods |= {(r["period_label"], r["period_type"], r["fiscal_year"], r["fiscal_quarter"],
                 "", r["period_end"]) for r in financial_rows if r["metric_id"] == "stockholders_equity"}
    meta = {m[0]: m for m in DERIVED_KPIS}
    rows = []

    def value(metric_id, label):
        row = by_key.get((metric_id, label))
        return None if row is None or row["value"] in (None, "") else float(row["value"])

    def add(metric_id, period, result, inputs):
        _, label_text, unit, _, formula, domain, source = meta[metric_id]
        label, period_type, year, quarter, start, end = period
        rows.append({
            "metric_id": metric_id, "metric_name": label_text, "domain": domain, "period_label": label,
            "period_type": period_type, "fiscal_year": year, "fiscal_quarter": quarter, "period_start": start,
            "period_end": end, "value": result, "unit": unit, "formula": formula,
            "input_metric_ids": ",".join(inputs), "source": source,
        })

    seen = set()
    for period in sorted(periods, key=lambda p: (p[5], p[1] == "FY")):
        label, period_type, year = period[0], period[1], period[2]
        if (label, period[5]) in seen:
            continue
        seen.add((label, period[5]))
        revenue = value("revenue", label)
        prior_label = f"{int(year) - 1}FY" if period_type == "FY" else f"{int(year) - 1}{period_type}"
        ocf, capex = value("operating_cash_flow", label), value("capex_total", label)
        if ocf is not None and capex is not None:
            add("free_cash_flow", period, ocf - capex, ["operating_cash_flow", "capex_total"])
        le, se = value("liabilities_and_equity", label), value("stockholders_equity", label)
        if le is not None and se is not None:
            add("total_liabilities", period, le - se, ["liabilities_and_equity", "stockholders_equity"])
        if revenue:
            op = value("operating_income", label)
            if op is not None:
                add("operating_margin", period, op / revenue, ["operating_income", "revenue"])
            ni = value("net_income", label)
            if ni is not None:
                add("net_margin", period, ni / revenue, ["net_income", "revenue"])
            prior = value("revenue", prior_label)
            if prior:
                add("revenue_growth_yoy", period, revenue / prior - 1.0, ["revenue"])
        fuel, opex = value("fuel_costs", label), value("operating_expenses", label)
        if fuel is not None and opex:
            add("fuel_share_of_opex", period, fuel / opex, ["fuel_costs", "operating_expenses"])

    rows.sort(key=lambda r: (r["period_end"], r["period_type"] == "FY", r["metric_id"]))
    write_csv(PROCESSED / "fact_financial_kpi_derived.csv", rows, DERIVED_FIELDS)
    return rows


def latest_period(rows) -> str | None:
    quarters = [r["period_end"] for r in rows if r["metric_id"] == "revenue" and r["period_type"] != "FY"]
    return max(quarters) if quarters else None


def coverage_summary(rows):
    counts = defaultdict(lambda: defaultdict(int))
    for r in rows:
        counts[r["metric_id"]][r["method"]] += 1
    return {metric: dict(methods) for metric, methods in sorted(counts.items())}
