"""Quarterly mainline unit economics for the DL reporting carrier.

Numerators come from Form 41 (P-1.2 profit and loss, P-12(a) fuel) and denominators from
T-100 segment capacity and traffic. Both are filed by the same DOT reporting entity, so
per-ASM measures are scope-consistent. They are not Delta's investor-relations TRASM/CASM:
those are consolidated and include regional capacity purchase flying, refinery sales and
special items.

"Mainline" here excludes Form 41 transport-related revenue and expense. For a network
carrier those lines mainly carry regional capacity purchase flying and other transport
services that do not run on DL-operated seat-miles.
"""
from __future__ import annotations

from collections import defaultdict

from .config import PROCESSED
from .io_utils import write_csv

QUARTER_END = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}


def t100_quarterly(route_rows):
    agg = defaultdict(lambda: defaultdict(int))
    months = defaultdict(set)
    for r in route_rows:
        year, month = int(r["year"]), int(r["month"])
        quarter = (month - 1) // 3 + 1
        for scope in (r["scope"], "system"):
            key = (year, quarter, scope)
            months[key].add(month)
            a = agg[key]
            for field in ("asm", "rpm", "passengers", "seats", "departures_performed", "departures_scheduled"):
                a[field] += int(r[field])
    out = {}
    for key, a in agg.items():
        out[key] = {**a, "months": len(months[key])}
    return out


def _safe_div(a, b):
    return a / b if b else None


def build_unit_economics(route_rows, pnl_quarterly, fuel_quarterly):
    traffic = t100_quarterly(route_rows)
    pnl = {(r["year"], r["quarter"], r["scope"]): r for r in pnl_quarterly}
    fuel = {(r["year"], r["quarter"], r["scope"]): r for r in fuel_quarterly}
    rows, skipped = [], []
    for key in sorted(set(traffic) & set(pnl)):
        year, quarter, scope = key
        t, p, f = traffic[key], pnl[key], fuel.get(key)
        if t["months"] != 3 or f is None or f["months_reported"] != 3:
            skipped.append({"period_label": f"{year}Q{quarter}", "scope": scope,
                            "t100_months": t["months"], "fuel_months": f["months_reported"] if f else 0})
            continue
        pax_revenue = p["trans_rev_pax"]
        mainline_revenue = p["op_revenues"] - p["trans_revenue"]
        mainline_expense = p["op_expenses"] - p["trans_expenses"]
        fuel_cost, gallons = f["scheduled_fuel_cost"], f["scheduled_fuel_gallons"]
        asm, rpm = t["asm"], t["rpm"]
        rows.append({
            "year": year, "quarter": quarter, "period_label": f"{year}Q{quarter}",
            "period_end": f"{year}-{QUARTER_END[quarter]}", "scope": scope,
            "asm": asm, "rpm": rpm, "passengers": t["passengers"], "seats": t["seats"],
            "departures_performed": t["departures_performed"],
            "load_factor": _safe_div(rpm, asm),
            "pax_revenue": pax_revenue, "mainline_revenue": mainline_revenue,
            "non_pax_mainline_revenue": mainline_revenue - pax_revenue,
            "mainline_expense": mainline_expense, "scheduled_fuel_cost": fuel_cost,
            "scheduled_fuel_gallons": gallons,
            "mainline_expense_ex_fuel": mainline_expense - fuel_cost,
            "mainline_operating_income": mainline_revenue - mainline_expense,
            "mainline_operating_margin": _safe_div(mainline_revenue - mainline_expense, mainline_revenue),
            "op_revenues_total": p["op_revenues"], "op_expenses_total": p["op_expenses"],
            "transport_related_revenue": p["trans_revenue"], "transport_related_expense": p["trans_expenses"],
            "prasm_cents": _safe_div(pax_revenue * 100, asm),
            "trasm_cents": _safe_div(mainline_revenue * 100, asm),
            "casm_cents": _safe_div(mainline_expense * 100, asm),
            "casm_ex_fuel_cents": _safe_div((mainline_expense - fuel_cost) * 100, asm),
            "yield_cents": _safe_div(pax_revenue * 100, rpm),
            "fuel_cost_per_gallon": _safe_div(fuel_cost, gallons),
            "asm_per_gallon": _safe_div(asm, gallons),
        })
    write_csv(PROCESSED / "fact_unit_economics_quarterly.csv", rows)
    return rows, skipped


def form41_vs_sec(pnl_quarterly, financial_rows):
    """Compare Form 41 system operating revenue with SEC consolidated revenue each quarter."""
    sec = {r["period_label"]: float(r["value"]) for r in financial_rows
           if r["metric_id"] == "revenue" and r["period_type"] != "FY"}
    sec_oi = {r["period_label"]: float(r["value"]) for r in financial_rows
              if r["metric_id"] == "operating_income" and r["period_type"] != "FY"}
    out = []
    for r in pnl_quarterly:
        if r["scope"] != "system" or r["period_label"] not in sec:
            continue
        out.append({
            "period_label": r["period_label"],
            "form41_op_revenues": r["op_revenues"], "sec_revenue": sec[r["period_label"]],
            "revenue_ratio": _safe_div(r["op_revenues"], sec[r["period_label"]]),
            "form41_op_profit": r["op_profit_loss"], "sec_operating_income": sec_oi.get(r["period_label"]),
        })
    write_csv(PROCESSED / "check_form41_vs_sec.csv", out)
    return out
