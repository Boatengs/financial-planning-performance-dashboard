from __future__ import annotations

from datetime import date

from .config import DERIVED_KPIS, FPNA_KPIS, NETWORK_KPIS, PROCESSED, RAW, ROOT, UNIT_ECONOMICS_KPIS
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
    dates = build_date_dimension(2019, 2027)
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
    for mid, label, unit, typ, formula, domain, source in DERIVED_KPIS:
        metric_rows.append({"metric_id": mid, "metric_name": label, "domain": domain, "unit": unit, "metric_type": typ,
                            "formula": formula, "source_system": source, "source_field": "derived",
                            "availability_count_2019_2026": ""})
    for mid, label, unit, typ, formula in UNIT_ECONOMICS_KPIS:
        metric_rows.append({"metric_id": mid, "metric_name": label, "domain": "Unit Economics (Mainline)", "unit": unit,
                            "metric_type": typ, "formula": formula, "source_system": "BTS Form 41 + T-100",
                            "source_field": "Form 41 P-1.2, P-12(a); T-100 segment", "availability_count_2019_2026": ""})
    for mid, label, unit, typ, formula, domain in FPNA_KPIS:
        metric_rows.append({"metric_id": mid, "metric_name": label, "domain": domain, "unit": unit, "metric_type": typ,
                            "formula": formula, "source_system": "Analytical model",
                            "source_field": "model formula", "availability_count_2019_2026": ""})
    write_csv(PROCESSED / "dim_metric.csv", metric_rows)

    scenarios = [
        {"scenario_id": "ACT", "scenario_name": "Actual", "scenario_type": "Reported", "editable": 0, "description": "Reported historical actuals (Form 41 and T-100)."},
        {"scenario_id": "BUD", "scenario_name": "Budget", "scenario_type": "Modeled", "editable": 1, "description": "Analyst-modeled budget: base driver model run from Q4 of the prior year."},
        {"scenario_id": "FCT", "scenario_name": "Forecast", "scenario_type": "Modeled", "editable": 1, "description": "Analyst-modeled rolling forecast from the latest actual quarter (seasonal naive with drift)."},
        {"scenario_id": "UP", "scenario_name": "Upside", "scenario_type": "Modeled", "editable": 1, "description": "Analyst-modeled upside: explicit driver shocks to the base forecast; not company guidance."},
        {"scenario_id": "DOWN", "scenario_name": "Downside", "scenario_type": "Modeled", "editable": 1, "description": "Analyst-modeled downside: explicit driver shocks to the base forecast; not company guidance."},
    ]
    write_csv(PROCESSED / "dim_scenario.csv", scenarios)
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


def build_source_manifest(t100_sources, bts_master_path, form41_sources=()):
    from .financials import resolve_companyfacts_path
    sec_path, sec_label = resolve_companyfacts_path()
    source_defs = [
        (sec_path, sec_label, "https://data.sec.gov/api/xbrl/companyfacts/CIK0000027904.json", "Consolidated GAAP financial actuals", "used"),
    ]
    faa = RAW / "faa_airports_2026-09-03.zip"
    if faa.exists():
        source_defs.append((faa, "FAA NASR airport CSV", "https://nfdc.faa.gov/webContent/28DaySub/extra/03_Sep_2026_APT_CSV.zip", "U.S. airport coordinate fallback/enrichment", "used_fallback"))
    for p in t100_sources:
        source_name, url = _t100_source_metadata(p)
        source_defs.append((p, source_name, url, "DL-reported segment traffic and capacity", "used"))
    from .transtats import TABLES, table_url
    for p in form41_sources:
        key = "form41_p12" if p.parent.name == "p12" else "form41_fuel"
        source_defs.append((p, TABLES[key].title, table_url(TABLES[key]), "DL mainline revenue, cost and fuel", "used"))
    if bts_master_path:
        source_defs.append((bts_master_path, "BTS Master Coordinate", "https://transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FLL&QO_fu146_anzr=N8vn6v10", "Canonical global airport coordinates", "used"))
    rows = []
    for p, name, url, role, status in source_defs:
        rows.append({"source_name": name, "local_file": str(p.relative_to(ROOT)), "size_bytes": p.stat().st_size,
                     "sha256": sha256_file(p), "official_url": url, "role": role, "pipeline_status": status})
    write_csv(PROCESSED / "source_manifest.csv", rows)
    return rows
