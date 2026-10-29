"""Network shift analysis: which routes and airports drive DL traffic, then versus 2019.

All measures come from the T-100 route-month fact (DL reporting carrier). The comparison
window is the latest twelve loaded months (trailing twelve months, TTM) against calendar
2019, the last full pre-pandemic year. Both windows are twelve months, so seasonality is
balanced.
"""
from __future__ import annotations

from collections import defaultdict

from .config import PROCESSED
from .io_utils import write_csv

MEASURES = ["passengers", "seats", "asm", "rpm", "departures_performed", "departures_scheduled"]


def _month_index(period: str) -> int:
    return int(period[:4]) * 12 + int(period[5:7]) - 1


def ttm_window(route_rows):
    periods = sorted({r["period"] for r in route_rows})
    if not periods:
        raise ValueError("No route-month rows")
    last = _month_index(periods[-1])
    window = [p for p in periods if last - 11 <= _month_index(p) <= last]
    if len(window) != 12:
        raise ValueError(f"Latest twelve-month window is incomplete: {len(window)} months loaded")
    return window[0], window[-1]


def _sum(rows, key_fn):
    agg = defaultdict(lambda: defaultdict(int))
    for r in rows:
        a = agg[key_fn(r)]
        for m in MEASURES:
            a[m] += int(r[m])
    return agg


def _with_ratios(a):
    a = dict(a)
    a["load_factor"] = a["rpm"] / a["asm"] if a.get("asm") else None
    a["completion_rate"] = (a["departures_performed"] / a["departures_scheduled"]
                            if a.get("departures_scheduled") else None)
    return a


def route_annual(route_rows):
    agg = _sum(route_rows, lambda r: (int(r["year"]), r["route_id"], r["origin"], r["destination"],
                                      r["market_id"], r["scope"]))
    rows = []
    for (year, route_id, origin, destination, market_id, scope), a in sorted(agg.items()):
        rows.append({"year": year, "route_id": route_id, "origin": origin, "destination": destination,
                     "market_id": market_id, "scope": scope, **_with_ratios(a)})
    return rows


def _window_rows(route_rows, start, end):
    return [r for r in route_rows if start <= r["period"] <= end]


def market_comparison(route_rows, ttm_start, ttm_end, base_year=2019):
    """Undirected market totals for TTM versus the base year, ranked by passenger change."""
    base = _sum([r for r in route_rows if int(r["year"]) == base_year], lambda r: (r["market_id"], r["scope"]))
    ttm = _sum(_window_rows(route_rows, ttm_start, ttm_end), lambda r: (r["market_id"], r["scope"]))
    rows = []
    for key in sorted(set(base) | set(ttm)):
        b, t = base.get(key, {}), ttm.get(key, {})
        bp, tp = b.get("passengers", 0), t.get("passengers", 0)
        rows.append({
            "market_id": key[0], "scope": key[1],
            "passengers_base": bp, "passengers_ttm": tp, "passenger_change": tp - bp,
            "passenger_change_pct": (tp / bp - 1) if bp else None,
            "asm_base": b.get("asm", 0), "asm_ttm": t.get("asm", 0),
            "status": "new" if not bp and tp else "exited" if bp and not tp else "continuing",
        })
    rows.sort(key=lambda r: r["passenger_change"], reverse=True)
    return rows


def airport_comparison(route_rows, ttm_start, ttm_end, base_year=2019):
    """Departing passengers and departures by origin airport, TTM versus base year."""
    base = _sum([r for r in route_rows if int(r["year"]) == base_year], lambda r: r["origin"])
    ttm = _sum(_window_rows(route_rows, ttm_start, ttm_end), lambda r: r["origin"])
    total_b = sum(a["passengers"] for a in base.values()) or 1
    total_t = sum(a["passengers"] for a in ttm.values()) or 1
    rows = []
    for code in sorted(set(base) | set(ttm)):
        b, t = base.get(code, {}), ttm.get(code, {})
        bp, tp = b.get("passengers", 0), t.get("passengers", 0)
        rows.append({
            "airport_code": code,
            "departing_passengers_base": bp, "departing_passengers_ttm": tp,
            "passenger_change": tp - bp, "passenger_change_pct": (tp / bp - 1) if bp else None,
            "share_base": bp / total_b, "share_ttm": tp / total_t,
            "share_change_pts": (tp / total_t - bp / total_b) * 100,
            "departures_base": b.get("departures_performed", 0), "departures_ttm": t.get("departures_performed", 0),
        })
    rows.sort(key=lambda r: r["departing_passengers_ttm"], reverse=True)
    return rows


def network_structure_by_year(route_rows, ttm_start, ttm_end):
    """Scope mix, route count and concentration per calendar year plus the TTM window."""
    windows = {str(y): [r for r in route_rows if int(r["year"]) == y]
               for y in sorted({int(r["year"]) for r in route_rows})}
    windows["TTM"] = _window_rows(route_rows, ttm_start, ttm_end)
    out = []
    for label, rows in windows.items():
        months = len({r["period"] for r in rows})
        totals = _sum(rows, lambda r: "all")["all"]
        by_scope = _sum(rows, lambda r: r["scope"])
        markets = _sum(rows, lambda r: r["market_id"])
        ranked = sorted((a["passengers"] for a in markets.values()), reverse=True)
        total_pax = totals["passengers"] or 1
        out.append({
            "window": label, "months": months,
            "passengers": totals["passengers"], "asm": totals["asm"],
            "load_factor": totals["rpm"] / totals["asm"] if totals["asm"] else None,
            "international_asm_share": by_scope["international"]["asm"] / totals["asm"] if totals["asm"] else None,
            "markets_served": sum(1 for a in markets.values() if a["passengers"] > 0),
            "top20_market_passenger_share": sum(ranked[:20]) / total_pax,
            "top100_market_passenger_share": sum(ranked[:100]) / total_pax,
        })
    return out


def route_layer(route_rows, airports, ttm_start, ttm_end):
    """Directional TTM route layer with coordinates for the 3D map."""
    coords = {a["airport_code"]: a for a in airports}
    ttm = _sum(_window_rows(route_rows, ttm_start, ttm_end),
               lambda r: (r["route_id"], r["origin"], r["destination"], r["scope"]))
    rows, missing = [], 0
    for (route_id, origin, destination, scope), a in sorted(ttm.items()):
        o, d = coords.get(origin, {}), coords.get(destination, {})
        if o.get("latitude") in (None, "") or d.get("latitude") in (None, ""):
            missing += 1
            continue
        rows.append({
            "route_id": route_id, "origin": origin, "destination": destination, "scope": scope,
            "origin_name": o.get("airport_name", ""), "destination_name": d.get("airport_name", ""),
            "origin_lat": float(o["latitude"]), "origin_lon": float(o["longitude"]),
            "destination_lat": float(d["latitude"]), "destination_lon": float(d["longitude"]),
            **_with_ratios(a),
        })
    return rows, missing


def build_network_analysis(route_rows, airports):
    ttm_start, ttm_end = ttm_window(route_rows)
    annual = route_annual(route_rows)
    markets = market_comparison(route_rows, ttm_start, ttm_end)
    airport_cmp = airport_comparison(route_rows, ttm_start, ttm_end)
    structure = network_structure_by_year(route_rows, ttm_start, ttm_end)
    layer, missing = route_layer(route_rows, airports, ttm_start, ttm_end)
    write_csv(PROCESSED / "fact_route_annual.csv", annual)
    write_csv(PROCESSED / "analysis_market_ttm_vs_2019.csv", markets)
    write_csv(PROCESSED / "analysis_airport_ttm_vs_2019.csv", airport_cmp)
    write_csv(PROCESSED / "analysis_network_structure.csv", structure)
    write_csv(PROCESSED / "layer_route_ttm.csv", layer)
    return {
        "ttm_start": ttm_start, "ttm_end": ttm_end, "route_annual_rows": len(annual),
        "markets_compared": len(markets), "route_layer_rows": len(layer),
        "routes_without_coordinates": missing,
        "annual": annual, "markets": markets, "airports": airport_cmp, "structure": structure, "layer": layer,
    }
