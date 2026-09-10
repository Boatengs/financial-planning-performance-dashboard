from __future__ import annotations

from datetime import date

from .config import FPNA_KPIS, NETWORK_KPIS, PROCESSED, RAW, ROOT
from .io_utils import sha256_file, write_csv
from .transtats import form_url


def build_date_dimension(start_year: int = 2019, end_year: int = 2026):
    dates = []
    for y in range(start_year, end_year + 1):
        for m in range(1, 13):
            q = (m - 1) // 3 + 1
            dates.append({
                "date_key": y * 100 + m,
                "period": f"{y:04d}-{m:02d}-01",
                "year": y,
                "quarter": f"Q{q}",
                "month": m,
                "month_name": date(y, m, 1).strftime("%B"),
            })
    write_csv(PROCESSED / "dim_date.csv", dates)
    return dates


def build_route_dimension(route_rows):
    routes = {}
    for r in route_rows:
        routes[r["route_id"]] = {
            "route_id": r["route_id"],
            "market_id": r["market_id"],
            "origin": r["origin"],
            "destination": r["destination"],
            "scope": r["scope"],
            "distance_miles": r["distance_miles"],
        }
    route_dim = sorted(routes.values(), key=lambda x: x["route_id"])
    write_csv(PROCESSED / "dim_route.csv", route_dim)
    return route_dim


def build_dimensions(fin_meta, route_rows):
    dates = build_date_dimension()
    route_dim = build_route_dimension(route_rows)

    metric_rows = []
    for m in fin_meta:
        metric_rows.append({
            "metric_id": m["metric_id"], "metric_name": m["label"], "domain": m["domain"], "unit": m["unit"],
            "metric_type": "Reported", "formula": "SEC XBRL reported value", "source_system": "SEC CompanyFacts",
            "source_field": f'{m["namespace"]}:{m["selected_tag"]}' if m["selected_tag"] else "NOT AVAILABLE",
            "availability_count_2019_2026": m["available"]
        })
    for mid, label, unit, typ, formula in NETWORK_KPIS:
        metric_rows.append({"metric_id": mid, "metric_name": label, "domain": "Network / Operations", "unit": unit, "metric_type": typ,
                            "formula": formula, "source_system": "BTS T-100 Segment", "source_field": mid if typ == "Reported" else "derived from T-100 reported fields", "availability_count_2019_2026": ""})
    for mid, label, unit, typ, formula, domain in FPNA_KPIS:
        metric_rows.append({"metric_id": mid, "metric_name": label, "domain": domain, "unit": unit, "metric_type": typ,
                            "formula": formula, "source_system": "Analytical model" if typ == "Modeled" else "Derived from reported facts",
                            "source_field": "model formula", "availability_count_2019_2026": ""})
    write_csv(PROCESSED / "dim_metric.csv", metric_rows)

    scenarios = [
        {"scenario_id": "ACT", "scenario_name": "Actual", "scenario_type": "Reported", "editable": 0, "description": "Reported historical actuals only."},
        {"scenario_id": "BUD", "scenario_name": "Budget", "scenario_type": "Modeled", "editable": 1, "description": "Analyst-created budget based on documented assumptions."},
        {"scenario_id": "FCT", "scenario_name": "Forecast", "scenario_type": "Modeled", "editable": 1, "description": "Analyst-created rolling forecast based on public actuals and documented assumptions."},
        {"scenario_id": "UP", "scenario_name": "Upside", "scenario_type": "Modeled", "editable": 1, "description": "Analyst-created upside scenario."},
        {"scenario_id": "DOWN", "scenario_name": "Downside", "scenario_type": "Modeled", "editable": 1, "description": "Analyst-created downside scenario."},
    ]
    write_csv(PROCESSED / "dim_scenario.csv", scenarios)
    write_csv(PROCESSED / "fact_budget_forecast_template.csv", [], ["period", "metric_id", "scenario_id", "value", "unit", "assumption_set_id", "model_version", "notes"])
    write_csv(PROCESSED / "fact_driver_assumption_template.csv", [], ["period", "driver_id", "driver_name", "scenario_id", "value", "unit", "source_or_rationale", "model_version"])
    return dates, route_dim, metric_rows, scenarios


def _t100_source_metadata(path):
    scope = path.parent.name
    if path.name.startswith("transtats_"):
        return (
            f"BTS TranStats T-100 {scope.title()} Segment",
            form_url(scope),
        )
    folder = "domestic-segments" if scope == "domestic" else "international-segments"
    if path.name == "current_202506_202605.zip":
        source_basename = (
            "DB28SEG.DD.WAC.202506.202605.REL01.04AUG2026.zip"
            if scope == "domestic"
            else "DB28SEG.FD.WAC.202506.202605.REL01.04AUG2026.zip"
        )
    else:
        source_basename = path.name
    return (
        f"BTS T-100 {scope.title()} Segment",
        f"https://www.bts.gov/sites/bts.dot.gov/files/docs/airline-data/{folder}/{source_basename}",
    )


def build_source_manifest(t100_sources, bts_master_path):
    source_defs = [
        (RAW / "delta_companyfacts.json", "SEC CompanyFacts", "https://data.sec.gov/api/xbrl/companyfacts/CIK0000027904.json", "Core GAAP financial actuals", "used"),
        (RAW / "delta_2025_10k.xls", "Delta 2025 10-K XBRL workbook", "https://d18rn0p25nwr6d.cloudfront.net/CIK-0000027904/0db061b6-3e78-4a3a-8131-9b65c5210ab7.xls", "Retained raw filing workbook for cross-checks and future management-KPI extraction", "retained_raw"),
        (RAW / "delta_2026_q2_10q.xls", "Delta 2026 Q2 10-Q XBRL workbook", "https://d18rn0p25nwr6d.cloudfront.net/CIK-0000027904/47a4a84f-7c64-4145-b2b4-288bed9a4037.xls", "Retained raw filing workbook for current-quarter cross-checks and future management-KPI extraction", "retained_raw"),
        (RAW / "faa_airports_2026-09-03.zip", "FAA NASR airport CSV", "https://nfdc.faa.gov/webContent/28DaySub/extra/03_Sep_2026_APT_CSV.zip", "U.S. airport coordinate fallback/enrichment", "used_fallback"),
    ]
    for p in t100_sources:
        source_name, url = _t100_source_metadata(p)
        source_defs.append((p, source_name, url, "DL-reported segment traffic and capacity", "used"))
    if bts_master_path:
        source_defs.append((bts_master_path, "BTS Master Coordinate", "https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=N8vn6v10&gnoyr_VQ=FLL", "Canonical global airport coordinates", "used"))
    rows = []
    for p, name, url, role, status in source_defs:
        rows.append({"source_name": name, "local_file": str(p.relative_to(ROOT)), "size_bytes": p.stat().st_size,
                     "sha256": sha256_file(p), "official_url": url, "role": role, "pipeline_status": status})
    write_csv(PROCESSED / "source_manifest.csv", rows)
    return rows
