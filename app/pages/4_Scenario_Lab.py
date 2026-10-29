"""Forecast, budget, scenarios and your own driver changes for the next four quarters."""
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import (BLUE, INK, RED, ROOT, SCENARIO_COLORS, SCENARIO_NAMES, csv, footnote, js, page_setup,
                  q_sort_key, require_data, usd_b)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from pipeline.fpa_model import DRIVERS, outcomes  # noqa: E402  (same identity the build uses)

page_setup("Scenario Lab")
require_data()
summary = js("fpa_model_summary.json")

st.title("Scenario lab")
st.caption(f"DL mainline operating income. Forecast origin {summary['latest_actual']}. Forward values are "
           "modeled from public data and are not Delta guidance.")

plan = csv("budget_forecast.csv")
plan["order"] = plan["period"].map(q_sort_key)
income = plan[plan["metric_id"] == "mainline_operating_income"]
origin = summary["latest_actual"]

fig = go.Figure()
act = income[income["scenario_id"] == "ACT"].sort_values("order")
fig.add_scatter(x=act["period"], y=act["value"] / 1e9, name="Actual", line=dict(color=INK, width=2))
bud = income[income["scenario_id"] == "BUD"].sort_values("order")
fig.add_scatter(x=bud["period"], y=bud["value"] / 1e9, name="Budget (set each Q4)", mode="markers",
                marker=dict(color=SCENARIO_COLORS["BUD"], size=7, symbol="diamond"))
for s in ("FCT", "FUEL", "UP", "DOWN"):
    rows = income[(income["scenario_id"] == s) & (income["forecast_origin"] == origin)].sort_values("order")
    anchor = act.tail(1)
    fig.add_scatter(x=pd.concat([anchor["period"], rows["period"]]),
                    y=pd.concat([anchor["value"], rows["value"]]) / 1e9, name=SCENARIO_NAMES[s],
                    line=dict(color=SCENARIO_COLORS[s], dash="solid" if s == "FCT" else "dot"))
fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="$B per quarter",
                  legend=dict(orientation="h", y=-0.2), xaxis=dict(tickangle=-45, nticks=20))
st.plotly_chart(fig, use_container_width=True)

sc = summary["scenario_next4_operating_income"]
c = st.columns(4)
c[0].metric("Base, next 4 quarters", usd_b(summary["base_next4_operating_income"]))
c[1].metric("Fuel stays at latest price", usd_b(sc["FUEL"]), usd_b(sc["FUEL"] - summary["base_next4_operating_income"]))
c[2].metric("Upside", usd_b(sc["UP"]))
c[3].metric("Downside", usd_b(sc["DOWN"]))

st.subheader("Try your own assumptions")
drivers = csv("driver_assumptions.csv")
base = drivers[(drivers["scenario_id"] == "FCT") & (drivers["forecast_origin"] == origin)]
path = {p: dict(zip(g["driver_id"], g["value"])) for p, g in base.groupby("period")}
s = st.columns(5)
cap = s[0].slider("Capacity vs base (%)", -10.0, 10.0, 0.0, 0.5)
lf = s[1].slider("Load factor vs base (pts)", -5.0, 5.0, 0.0, 0.5)
yld = s[2].slider("Yield vs base (%)", -10.0, 10.0, 0.0, 0.5)
casm = s[3].slider("CASM-ex fuel vs base (%)", -10.0, 10.0, 0.0, 0.5)
fuel = s[4].slider("Fuel price vs base (%)", -40.0, 40.0, 0.0, 5.0)

custom_total, base_total = 0.0, 0.0
for p, d in path.items():
    point = {k: d[k] for k in DRIVERS}
    base_total += outcomes(point)["operating_income"]
    point["asm"] *= 1 + cap / 100
    point["load_factor"] += lf / 100
    point["yield"] *= 1 + yld / 100
    point["casm_ex"] *= 1 + casm / 100
    point["fuel_price"] *= 1 + fuel / 100
    custom_total += outcomes(point)["operating_income"]
st.metric("Your scenario, next 4 quarters", usd_b(custom_total), usd_b(custom_total - base_total) + " vs base")

left, right = st.columns(2)
with left:
    st.markdown("**Sensitivity of next-4-quarter operating income**")
    sens = csv("sensitivity.csv").sort_values("operating_income_change")
    fig = go.Figure(go.Bar(x=sens["operating_income_change"] / 1e9, y=sens["shock"], orientation="h",
                           marker_color=[BLUE if v >= 0 else RED for v in sens["operating_income_change"]]))
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="$B change vs base")
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.markdown("**Budget versus actual (budget set each Q4 for the next year)**")
    var = csv("budget_variance.csv")
    var = var[var["metric_id"] == "mainline_operating_income"].copy()
    shown = pd.DataFrame({"Quarter": var["period"], "Budget": var["budget"].map(usd_b),
                          "Actual": var["actual"].map(usd_b), "Variance": var["actual_vs_budget"].map(usd_b)})
    st.dataframe(shown, hide_index=True, use_container_width=True, height=320)
    footnote("Budget for each year is set at the prior Q4 with the base method, so it equals the prior year's "
             "drivers quarter by quarter; the variance is therefore the year-over-year change in operating income.")

st.subheader("Why the base case is 'same quarter last year'")
comp = csv("forecast_method_comparison.csv")
overall = comp[comp["horizon"] == "all"].copy().sort_values("operating_income_mae")
overall["Revenue error (MAPE)"] = (overall["revenue_mape"] * 100).round(2).astype(str) + "%"
overall["Operating income error ($B)"] = (overall["operating_income_mae"] / 1e9).round(3)
overall["Margin error (pts)"] = overall["operating_margin_mae_pts"].round(2)
overall["Base"] = overall["is_base_method"].map({True: "yes", False: ""})
st.dataframe(overall[["method", "forecasts", "Revenue error (MAPE)", "Operating income error ($B)",
                      "Margin error (pts)", "Base"]], hide_index=True, use_container_width=True)
footnote("Rolling-origin backtest from 2023Q4, one to four quarters ahead: at each origin a method sees only "
         "data up to that quarter. Methods that extrapolate recent year-over-year trends did worse than carrying "
         "each driver forward from the same quarter a year earlier, so that is the base. Earlier origins are "
         "excluded because their trends come from the pandemic recovery.")
