"""Driver-based FP&A model for DL mainline operating income.

Operating income is rebuilt exactly from seven drivers each quarter:

    RPM              = ASM x load factor
    passenger rev    = RPM x yield
    mainline revenue = passenger rev x (1 + non-passenger revenue ratio)
    gallons          = ASM / ASMs per gallon
    mainline expense = ASM x CASM-ex fuel + gallons x fuel price
    operating income = mainline revenue - mainline expense

Everything here is analyst-modeled from public actuals. Nothing is Delta guidance.

* Base forecast: seasonal naive by driver. Each driver for a future quarter equals the same
  quarter one year earlier. This was chosen after a rolling-origin backtest (2023Q4 onward)
  in which every trend-extrapolating alternative (median, latest and two-quarter
  year-over-year drift, with fuel either seasonal or held at the origin price) had larger
  errors. The comparison is published in analysis_forecast_method_comparison.
* Budget: the base forecast made from Q4 of the prior year, which equals the prior year's
  actual drivers quarter by quarter.
* Upside / downside: explicit shocks to the base drivers (SCENARIO_SHOCKS).
* Fuel-at-origin: the base path with fuel held at the latest quarter's actual price and no
  other driver adjusting. It isolates fuel-price exposure when fuel moves sharply.
* Bridge: change in operating income between two periods split by driver using sequential
  substitution.
"""
from __future__ import annotations

import json
from statistics import median

from .config import PROCESSED
from .io_utils import write_csv

MODEL_VERSION = "fpa-drivers-1.0"
DRIVERS = ["asm", "load_factor", "yield", "non_pax_ratio", "casm_ex", "asm_per_gallon", "fuel_price"]
DRIVER_LABELS = {
    "asm": ("Capacity (ASMs)", "seat-miles"),
    "load_factor": ("Load factor", "ratio"),
    "yield": ("Passenger yield", "USD per RPM"),
    "non_pax_ratio": ("Non-passenger revenue as share of passenger revenue", "ratio"),
    "casm_ex": ("Cost per ASM excluding fuel", "USD per ASM"),
    "asm_per_gallon": ("Fuel efficiency (ASMs per gallon)", "seat-miles per gallon"),
    "fuel_price": ("Fuel price", "USD per gallon"),
}
# Candidate base methods compared in the backtest: (drift rule, fuel rule).
METHODS = {
    "seasonal_naive": ("none", "seasonal"),
    "seasonal_naive_fuel_at_origin": ("none", "origin"),
    "median_4q_yoy_drift": ("median4", "seasonal"),
    "median_4q_yoy_drift_fuel_at_origin": ("median4", "origin"),
    "latest_yoy_drift": ("latest", "seasonal"),
    "latest_yoy_drift_fuel_at_origin": ("latest", "origin"),
    "two_quarter_yoy_drift": ("mean2", "seasonal"),
    "two_quarter_yoy_drift_fuel_at_origin": ("mean2", "origin"),
}
BASE_METHOD = "seasonal_naive"
# Origins before 2023Q4 would take their year-over-year drift from pandemic-recovery quarters
# (2022 versus 2021), which is not a repeatable trend. Budgets start the year after this origin.
BACKTEST_FIRST_ORIGIN = "2023Q4"

# Analyst assumptions, applied to the base driver path. Not company guidance.
SCENARIO_SHOCKS = {
    "UP": {"asm": ("mult", 1.01), "load_factor": ("add", 0.01), "yield": ("mult", 1.02),
           "casm_ex": ("mult", 0.99), "fuel_price": ("mult", 0.90)},
    "DOWN": {"asm": ("mult", 0.98), "load_factor": ("add", -0.02), "yield": ("mult", 0.97),
             "casm_ex": ("mult", 1.02), "fuel_price": ("mult", 1.15)},
}
SCENARIO_RATIONALE = {
    "FUEL": "Fuel held at the latest quarter's actual price for every forecast quarter; all other drivers as base.",
    "UP": "Analyst upside: capacity +1%, load factor +1 pt, yield +2%, CASM-ex -1%, fuel price -10% versus base.",
    "DOWN": "Analyst downside: capacity -2%, load factor -2 pts, yield -3%, CASM-ex +2%, fuel price +15% versus base.",
}
SENSITIVITIES = [
    ("asm", "mult", 0.01, "Capacity +1%"),
    ("load_factor", "add", 0.01, "Load factor +1 pt"),
    ("yield", "mult", 0.01, "Yield +1%"),
    ("non_pax_ratio", "mult", 0.01, "Non-passenger revenue ratio +1%"),
    ("casm_ex", "mult", 0.01, "CASM-ex +1%"),
    ("asm_per_gallon", "mult", 0.01, "Fuel efficiency +1%"),
    ("fuel_price", "add", 0.10, "Fuel price +$0.10/gal"),
]


# ---------------------------------------------------------------- quarter arithmetic
def q_index(label: str) -> int:
    return int(label[:4]) * 4 + int(label[5]) - 1


def q_label(index: int) -> str:
    return f"{index // 4}Q{index % 4 + 1}"


# ---------------------------------------------------------------- drivers and identity
def drivers_from_actuals(row) -> dict:
    asm, rpm = float(row["asm"]), float(row["rpm"])
    pax = float(row["pax_revenue"])
    gallons = float(row["scheduled_fuel_gallons"])
    return {
        "asm": asm,
        "load_factor": rpm / asm,
        "yield": pax / rpm,
        "non_pax_ratio": float(row["non_pax_mainline_revenue"]) / pax,
        "casm_ex": float(row["mainline_expense_ex_fuel"]) / asm,
        "asm_per_gallon": asm / gallons,
        "fuel_price": float(row["scheduled_fuel_cost"]) / gallons,
    }


def outcomes(d: dict) -> dict:
    rpm = d["asm"] * d["load_factor"]
    pax = rpm * d["yield"]
    revenue = pax * (1 + d["non_pax_ratio"])
    gallons = d["asm"] / d["asm_per_gallon"]
    fuel = gallons * d["fuel_price"]
    expense = d["asm"] * d["casm_ex"] + fuel
    income = revenue - expense
    return {"rpm": rpm, "pax_revenue": pax, "revenue": revenue, "fuel_gallons": gallons, "fuel_cost": fuel,
            "expense": expense, "operating_income": income, "operating_margin": income / revenue if revenue else None}


def _yoy_drift(history: dict, driver: str, origin: int, rule: str) -> float:
    if rule == "none":
        return 0.0
    quarters = {"median4": range(origin - 3, origin + 1), "latest": [origin], "mean2": [origin - 1, origin]}[rule]
    changes = []
    for i in quarters:
        cur, prev = history.get(i), history.get(i - 4)
        if cur is None or prev is None or not prev[driver]:
            raise ValueError(f"Need eight quarters of history before {q_label(origin)} to forecast")
        changes.append(cur[driver] / prev[driver] - 1)
    return median(changes) if rule == "median4" else sum(changes) / len(changes)


def forecast(history: dict, origin: int, horizon: int = 4, method: str = BASE_METHOD) -> dict:
    """Driver path for quarters origin+1 .. origin+horizon using only history up to origin."""
    drift_rule, fuel_rule = METHODS[method]
    if origin - 4 not in history:
        raise ValueError(f"Need at least five quarters of history up to {q_label(origin)} to forecast")
    drift = {d: _yoy_drift(history, d, origin, drift_rule) for d in DRIVERS}
    path = {}
    for h in range(1, horizon + 1):
        target = origin + h
        reference = history.get(target - 4) if target - 4 <= origin else path[target - 4]
        point = {d: reference[d] * (1 + drift[d]) for d in DRIVERS}
        if fuel_rule == "origin":
            point["fuel_price"] = history[origin]["fuel_price"]
        path[target] = point
    return path


def apply_shocks(path: dict, shocks: dict) -> dict:
    shocked = {}
    for idx, point in path.items():
        p = dict(point)
        for driver, (kind, amount) in shocks.items():
            p[driver] = p[driver] * amount if kind == "mult" else p[driver] + amount
        shocked[idx] = p
    return shocked


# ---------------------------------------------------------------- bridge
def _period_drivers(rows) -> dict:
    """Drivers for a multi-quarter period computed from summed amounts (not averaged ratios)."""
    total = {k: sum(float(r[k]) for r in rows) for k in
             ("asm", "rpm", "pax_revenue", "non_pax_mainline_revenue", "mainline_expense_ex_fuel",
              "scheduled_fuel_gallons", "scheduled_fuel_cost")}
    return drivers_from_actuals(total)


def bridge(prior_rows, current_rows, prior_label, current_label):
    order = ["asm", "load_factor", "yield", "non_pax_ratio", "casm_ex", "asm_per_gallon", "fuel_price"]
    d0, d1 = _period_drivers(prior_rows), _period_drivers(current_rows)
    current = dict(d0)
    start = outcomes(current)["operating_income"]
    steps, running = [], start
    for driver in order:
        current[driver] = d1[driver]
        value = outcomes(current)["operating_income"]
        steps.append({"from_period": prior_label, "to_period": current_label, "driver": driver,
                      "driver_label": DRIVER_LABELS[driver][0], "prior_value": d0[driver],
                      "current_value": d1[driver], "operating_income_effect": value - running})
        running = value
    return {"from_period": prior_label, "to_period": current_label, "start_operating_income": start,
            "end_operating_income": running, "steps": steps}


# ---------------------------------------------------------------- orchestration
def build_fpa_model(unit_rows, scope: str = "system", horizon: int = 4):
    rows = sorted((r for r in unit_rows if r["scope"] == scope), key=lambda r: q_index(r["period_label"]))
    if len(rows) < 9:
        raise ValueError(f"Need at least nine quarters of {scope} unit economics; got {len(rows)}")
    history = {q_index(r["period_label"]): drivers_from_actuals(r) for r in rows}
    actual = {i: outcomes(d) for i, d in history.items()}
    for r in rows:  # identity check: drivers rebuild the reported amounts
        o = actual[q_index(r["period_label"])]
        if abs(o["operating_income"] - float(r["mainline_operating_income"])) > 1.0:
            raise AssertionError(f"Driver identity failed for {r['period_label']}")
    indexes = sorted(history)
    if indexes != list(range(indexes[0], indexes[-1] + 1)):
        raise ValueError("Unit economics quarters are not contiguous")
    latest = indexes[-1]

    plan_rows, assumption_rows = [], []

    def record(scenario, idx, point, notes, origin):
        o = outcomes(point)
        for metric, value, unit in (("mainline_revenue", o["revenue"], "USD"),
                                    ("mainline_expense", o["expense"], "USD"),
                                    ("mainline_operating_income", o["operating_income"], "USD"),
                                    ("mainline_operating_margin", o["operating_margin"], "%"),
                                    ("fuel_cost", o["fuel_cost"], "USD")):
            plan_rows.append({"period": q_label(idx), "metric_id": metric, "scenario_id": scenario, "value": value,
                              "unit": unit, "assumption_set_id": f"{scenario}-{q_label(origin)}",
                              "forecast_origin": q_label(origin), "model_version": MODEL_VERSION, "notes": notes})
        for d in DRIVERS:
            assumption_rows.append({"period": q_label(idx), "driver_id": d, "driver_name": DRIVER_LABELS[d][0],
                                    "scenario_id": scenario, "value": point[d], "unit": DRIVER_LABELS[d][1],
                                    "forecast_origin": q_label(origin), "source_or_rationale": notes,
                                    "model_version": MODEL_VERSION})

    for idx in indexes:  # actuals in the same long format
        record("ACT", idx, history[idx], "Reported Form 41 and T-100 actuals", idx)

    base = forecast(history, latest, horizon)
    fuel_at_origin = forecast(history, latest, horizon, method="seasonal_naive_fuel_at_origin")
    for idx, point in base.items():
        record("FCT", idx, point, "Base: seasonal naive by driver (same quarter one year earlier)", latest)
    for idx, point in fuel_at_origin.items():
        record("FUEL", idx, point, SCENARIO_RATIONALE["FUEL"], latest)
    for scenario, shocks in SCENARIO_SHOCKS.items():
        for idx, point in apply_shocks(base, shocks).items():
            record(scenario, idx, point, SCENARIO_RATIONALE[scenario], latest)

    budgets, variances = [], []
    for year in sorted({i // 4 for i in indexes}):
        origin = year * 4 - 1  # Q4 of prior year
        if origin < q_index(BACKTEST_FIRST_ORIGIN) or origin not in history or origin - 4 not in history:
            continue
        for idx, point in forecast(history, origin, 4).items():
            record("BUD", idx, point, f"Budget: base method run from {q_label(origin)} (prior-year drivers)", origin)
            budgets.append(idx)
            if idx in actual:
                b, a = outcomes(point), actual[idx]
                for metric, key in (("mainline_revenue", "revenue"), ("mainline_operating_income", "operating_income")):
                    variances.append({"period": q_label(idx), "metric_id": metric, "budget": b[key], "actual": a[key],
                                      "actual_vs_budget": a[key] - b[key],
                                      "actual_vs_budget_pct": (a[key] - b[key]) / abs(b[key]) if b[key] else None})

    backtest = []
    first = max(q_index(BACKTEST_FIRST_ORIGIN), indexes[0] + 7)
    for method in METHODS:
        for origin in range(first, latest):
            for idx, point in forecast(history, origin, horizon, method=method).items():
                if idx not in actual:
                    continue
                f, a = outcomes(point), actual[idx]
                for metric, key in (("mainline_revenue", "revenue"), ("mainline_operating_income", "operating_income"),
                                    ("mainline_operating_margin", "operating_margin")):
                    backtest.append({"method": method, "origin": q_label(origin), "target": q_label(idx),
                                     "horizon": idx - origin, "metric_id": metric, "actual": a[key],
                                     "forecast": f[key], "error": f[key] - a[key]})
    comparison = method_comparison(backtest)
    summary = {r["method"] + (f'|h{r["horizon"]}' if r["horizon"] != "all" else ""): r for r in comparison}

    base_total = {k: sum(outcomes(p)[k] for p in base.values()) for k in ("revenue", "operating_income")}
    sensitivity = []
    for driver, kind, amount, label in SENSITIVITIES:
        shocked = apply_shocks(base, {driver: (kind, (1 + amount) if kind == "mult" else amount)})
        income = sum(outcomes(p)["operating_income"] for p in shocked.values())
        sensitivity.append({"driver": driver, "shock": label, "base_operating_income": base_total["operating_income"],
                            "shocked_operating_income": income,
                            "operating_income_change": income - base_total["operating_income"],
                            "horizon_quarters": horizon, "forecast_origin": q_label(latest)})
    sensitivity.sort(key=lambda r: abs(r["operating_income_change"]), reverse=True)

    by_label = {r["period_label"]: r for r in rows}
    bridges = []
    years = sorted({i // 4 for i in indexes})
    for y in years[1:]:
        cur = [by_label.get(f"{y}Q{q}") for q in range(1, 5)]
        pri = [by_label.get(f"{y - 1}Q{q}") for q in range(1, 5)]
        if all(cur) and all(pri):
            bridges.append(bridge(pri, cur, str(y - 1), str(y)))
    if latest - 7 >= indexes[0]:
        cur = [by_label[q_label(i)] for i in range(latest - 3, latest + 1)]
        pri = [by_label[q_label(i)] for i in range(latest - 7, latest - 3)]
        bridges.append(bridge(pri, cur, f"{q_label(latest - 7)}-{q_label(latest - 4)}",
                              f"{q_label(latest - 3)}-{q_label(latest)}"))
    bridge_rows = [step for b in bridges for step in b["steps"]]

    write_csv(PROCESSED / "fact_budget_forecast.csv", plan_rows)
    write_csv(PROCESSED / "fact_driver_assumption.csv", assumption_rows)
    write_csv(PROCESSED / "fact_budget_variance.csv", variances)
    write_csv(PROCESSED / "fact_forecast_backtest.csv", backtest)
    write_csv(PROCESSED / "analysis_forecast_method_comparison.csv", comparison)
    write_csv(PROCESSED / "analysis_sensitivity.csv", sensitivity)
    write_csv(PROCESSED / "analysis_operating_income_bridge.csv", bridge_rows)
    result = {
        "model_version": MODEL_VERSION, "scope": scope, "first_actual": q_label(indexes[0]),
        "latest_actual": q_label(latest), "forecast_quarters": [q_label(i) for i in sorted(base)],
        "base_next4_revenue": base_total["revenue"], "base_next4_operating_income": base_total["operating_income"],
        "base_method": BASE_METHOD,
        "scenario_next4_operating_income": {
            **{s: sum(outcomes(p)["operating_income"] for p in apply_shocks(base, sh).values())
               for s, sh in SCENARIO_SHOCKS.items()},
            "FUEL": sum(outcomes(p)["operating_income"] for p in fuel_at_origin.values())},
        "backtest": summary, "bridges": [{k: v for k, v in b.items() if k != "steps"} for b in bridges],
        "budget_quarters": [q_label(i) for i in sorted(set(budgets))],
    }
    (PROCESSED / "fpa_model_summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def method_comparison(backtest):
    """Mean errors by method, overall and by horizon. Lower is better on every column."""
    out = []
    for method in METHODS:
        for horizon in ("all", 1, 2, 3, 4):
            sel = [r for r in backtest if r["method"] == method and (horizon == "all" or r["horizon"] == horizon)]
            rev = [r for r in sel if r["metric_id"] == "mainline_revenue"]
            inc = [r for r in sel if r["metric_id"] == "mainline_operating_income"]
            mar = [r for r in sel if r["metric_id"] == "mainline_operating_margin"]
            if not rev:
                continue
            out.append({
                "method": method, "horizon": horizon, "forecasts": len(rev),
                "revenue_mape": sum(abs(r["error"]) / abs(r["actual"]) for r in rev) / len(rev),
                "revenue_bias": sum(r["error"] / abs(r["actual"]) for r in rev) / len(rev),
                "operating_income_mae": sum(abs(r["error"]) for r in inc) / len(inc),
                "operating_margin_mae_pts": sum(abs(r["error"]) for r in mar) / len(mar) * 100,
                "is_base_method": method == BASE_METHOD,
            })
    return out
