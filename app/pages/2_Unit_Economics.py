"""Mainline revenue and cost per seat-mile from Form 41 over T-100 capacity."""
import plotly.graph_objects as go
import streamlit as st

from data import AMBER, BLUE, INK, MUTED, RED, csv, footnote, page_setup, q_sort_key, require_data

page_setup("Unit Economics")
require_data()

st.title("Unit economics")
st.caption("DL mainline: Form 41 revenue and expense (excluding transport-related lines) over T-100 seat-miles. "
           "These are scope-matched public measures, not Delta's investor-relations TRASM and CASM.")

ue = csv("unit_economics_quarterly.csv")
ue["order"] = ue["period_label"].map(q_sort_key)
ue = ue.sort_values("order")
scope = st.radio("Scope", ["system", "domestic", "international"], horizontal=True, format_func=str.title)
view = ue[ue["scope"] == scope]
latest = view.iloc[-1]
year_ago = view[view["order"] == latest["order"] - 4]

def delta(col, fmt="{:+.2f}", scale=1.0):
    if year_ago.empty:
        return None
    return fmt.format((latest[col] - year_ago[col].iloc[0]) * scale) + " YoY"

c = st.columns(6)
c[0].metric(f"TRASM {latest['period_label']}", f"{latest['trasm_cents']:.2f}¢", delta("trasm_cents"))
c[1].metric("CASM", f"{latest['casm_cents']:.2f}¢", delta("casm_cents"), delta_color="inverse")
c[2].metric("CASM-ex fuel", f"{latest['casm_ex_fuel_cents']:.2f}¢", delta("casm_ex_fuel_cents"), delta_color="inverse")
c[3].metric("Yield", f"{latest['yield_cents']:.2f}¢", delta("yield_cents"))
c[4].metric("Load factor", f"{latest['load_factor'] * 100:.1f}%", delta("load_factor", "{:+.1f} pts", 100))
c[5].metric("Fuel $/gal", f"${latest['fuel_cost_per_gallon']:.2f}", delta("fuel_cost_per_gallon", "{:+.2f}"),
            delta_color="inverse")

left, right = st.columns(2)
with left:
    fig = go.Figure()
    fig.add_scatter(x=view["period_label"], y=view["trasm_cents"], name="TRASM", line=dict(color=BLUE, width=2))
    fig.add_scatter(x=view["period_label"], y=view["casm_cents"], name="CASM", line=dict(color=RED, width=2))
    fig.add_scatter(x=view["period_label"], y=view["casm_ex_fuel_cents"], name="CASM-ex fuel",
                    line=dict(color=RED, dash="dot"))
    fig.add_scatter(x=view["period_label"], y=view["prasm_cents"], name="PRASM", line=dict(color=MUTED, dash="dash"))
    fig.update_layout(title="Revenue and cost per ASM (cents)", height=380, margin=dict(l=10, r=10, t=50, b=10),
                      legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True)
with right:
    fig = go.Figure()
    fig.add_bar(x=view["period_label"], y=(view["trasm_cents"] - view["casm_cents"]),
                marker_color=[BLUE if v >= 0 else RED for v in (view["trasm_cents"] - view["casm_cents"])],
                name="TRASM minus CASM")
    fig.update_layout(title="Unit margin: TRASM minus CASM (cents per ASM)", height=380,
                      margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)

a, b = st.columns(2)
with a:
    fig = go.Figure()
    fig.add_scatter(x=view["period_label"], y=view["load_factor"] * 100, name="Load factor", line=dict(color=INK))
    fig.update_layout(title="Load factor (%)", height=320, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)
with b:
    fig = go.Figure()
    fig.add_scatter(x=view["period_label"], y=view["fuel_cost_per_gallon"], name="Fuel $/gal", line=dict(color=AMBER))
    fig.add_scatter(x=view["period_label"], y=view["asm_per_gallon"], name="ASMs per gallon", yaxis="y2",
                    line=dict(color=MUTED, dash="dot"))
    fig.update_layout(title="Fuel price and efficiency", height=320, margin=dict(l=10, r=10, t=50, b=10),
                      yaxis=dict(title="$ per gallon"), yaxis2=dict(title="ASMs per gallon", overlaying="y", side="right"),
                      legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig, use_container_width=True)

with st.expander("Quarterly table"):
    cols = ["period_label", "asm", "load_factor", "pax_revenue", "mainline_revenue", "mainline_expense",
            "mainline_operating_margin", "prasm_cents", "trasm_cents", "casm_cents", "casm_ex_fuel_cents",
            "yield_cents", "fuel_cost_per_gallon"]
    st.dataframe(view[cols], hide_index=True, use_container_width=True)

check = csv("check_form41_vs_sec.csv")
footnote(f"Scope check: DL's Form 41 total operating revenue equals {check['revenue_ratio'].min():.2%} to "
         f"{check['revenue_ratio'].max():.2%} of SEC consolidated revenue across quarters, so the two sources "
         "agree. Mainline measures remove Form 41 transport-related revenue and expense (mainly regional "
         "partner flying) so the numerators match DL-operated seat-miles.")
