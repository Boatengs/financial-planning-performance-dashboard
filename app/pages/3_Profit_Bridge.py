"""Which drivers moved mainline operating income from one period to the next."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import BLUE, GREEN, RED, csv, footnote, js, page_setup, require_data, usd_b

page_setup("Profit Bridge")
require_data()

st.title("Operating income bridge")
st.caption("Change in DL mainline operating income split into seven drivers by sequential substitution, "
           "in the order shown. The steps add up exactly to the total change.")

bridge = csv("operating_income_bridge.csv").astype({"from_period": str, "to_period": str})
summary = js("fpa_model_summary.json")
pairs = [(b["from_period"], b["to_period"]) for b in summary["bridges"]]
labels = [f"{a} to {b}" for a, b in pairs]
choice = st.selectbox("Periods", labels, index=len(labels) - 1)
frm, to = pairs[labels.index(choice)]
meta = next(b for b in summary["bridges"] if b["from_period"] == frm and b["to_period"] == to)
steps = bridge[(bridge["from_period"] == frm) & (bridge["to_period"] == to)]

SHORT = {"asm": "Capacity", "load_factor": "Load factor", "yield": "Yield", "non_pax_ratio": "Other revenue",
         "casm_ex": "CASM-ex fuel", "asm_per_gallon": "Fuel efficiency", "fuel_price": "Fuel price"}
fig = go.Figure(go.Waterfall(
    x=[f"{frm}"] + steps["driver"].map(SHORT).tolist() + [f"{to}"],
    y=[meta["start_operating_income"] / 1e9] + (steps["operating_income_effect"] / 1e9).tolist()
      + [meta["end_operating_income"] / 1e9],
    measure=["absolute"] + ["relative"] * len(steps) + ["total"],
    increasing=dict(marker=dict(color=GREEN)), decreasing=dict(marker=dict(color=RED)),
    totals=dict(marker=dict(color=BLUE)), connector=dict(line=dict(color="#d1d5db")),
))
fig.update_layout(height=460, margin=dict(l=10, r=10, t=20, b=10), yaxis_title="$B")
st.plotly_chart(fig, use_container_width=True)

c = st.columns(3)
c[0].metric(f"Operating income {frm}", usd_b(meta["start_operating_income"]))
c[1].metric(f"Operating income {to}", usd_b(meta["end_operating_income"]),
            usd_b(meta["end_operating_income"] - meta["start_operating_income"]))
largest = steps.loc[steps["operating_income_effect"].abs().idxmax()]
c[2].metric("Largest single driver", largest["driver_label"], usd_b(largest["operating_income_effect"]))

UNITS = {"asm": ("{:,.1f}B", 1e-9), "load_factor": ("{:.1%}", 1), "yield": ("{:.2f}¢", 100),
         "non_pax_ratio": ("{:.1%}", 1), "casm_ex": ("{:.2f}¢", 100), "asm_per_gallon": ("{:.1f}", 1),
         "fuel_price": ("${:.2f}", 1)}
table = pd.DataFrame({
    "Driver": steps["driver_label"],
    frm: [UNITS[d][0].format(v * UNITS[d][1]) for d, v in zip(steps["driver"], steps["prior_value"])],
    to: [UNITS[d][0].format(v * UNITS[d][1]) for d, v in zip(steps["driver"], steps["current_value"])],
    "Effect on operating income": [usd_b(v) for v in steps["operating_income_effect"]],
})
st.dataframe(table, hide_index=True, use_container_width=True)
footnote("Order matters in sequential substitution: capacity first, then load factor, yield, non-passenger "
         "revenue, cost per ASM excluding fuel, fuel efficiency and fuel price. Each driver is computed from "
         "summed amounts for the period, not from averaged quarterly ratios.")
