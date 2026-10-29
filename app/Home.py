"""Executive performance: consolidated SEC results and the question the project answers."""
import plotly.graph_objects as go
import streamlit as st

from data import BLUE, INK, MUTED, RED, financial_wide, footnote, js, page_setup, pct, require_data, usd_b

page_setup("Executive Performance")
require_data()

st.title("Delta Air Lines: capacity, profit and network")
st.markdown(
    "**How well does Delta turn capacity into revenue and margin, which routes and airports drive its "
    "traffic since 2019, and what does the next year look like under different capacity, fuel and cost "
    "assumptions?**"
)

fin = financial_wide()
latest = fin.iloc[-1]
prior_year = fin[fin["period_label"] == f"{int(latest['period_label'][:4]) - 1}{latest['period_label'][4:]}"]
ttm = fin.tail(4)

c = st.columns(6)
c[0].metric(f"Revenue {latest['period_label']}", usd_b(latest["revenue"]),
            pct(latest.get("revenue_growth_yoy")) + " YoY" if "revenue_growth_yoy" in fin else None)
c[1].metric("Operating margin", pct(latest["operating_margin"]),
            f"{(latest['operating_margin'] - prior_year['operating_margin'].iloc[0]) * 100:+.1f} pts YoY"
            if not prior_year.empty else None)
c[2].metric("Net income", usd_b(latest["net_income"]))
c[3].metric("FCF, last 4 qtrs", usd_b(ttm["free_cash_flow"].sum()))
c[4].metric("Cash", usd_b(latest["cash"]))
c[5].metric("Debt (excl. leases)", usd_b(latest["debt_total"]))
footnote("Consolidated Delta Air Lines, Inc. from SEC CompanyFacts. Q4 values are full year minus nine months; "
         "quarterly cash flow is derived from year-to-date filings.")

left, right = st.columns(2)
with left:
    fig = go.Figure()
    fig.add_bar(x=fin["period_label"], y=fin["revenue"] / 1e9, name="Revenue", marker_color=BLUE)
    fig.add_bar(x=fin["period_label"], y=fin["operating_expenses"] / 1e9, name="Operating expense",
                marker_color="#93c5fd")
    fig.update_layout(title="Quarterly revenue and operating expense ($B)", barmode="group", height=360,
                      margin=dict(l=10, r=10, t=50, b=10), legend=dict(orientation="h", y=-0.3),
                      xaxis=dict(tickangle=-45, nticks=16))
    st.plotly_chart(fig, use_container_width=True)
with right:
    fig = go.Figure()
    fig.add_scatter(x=fin["period_label"], y=fin["operating_margin"] * 100, name="Operating margin",
                    line=dict(color=INK, width=2))
    fig.add_scatter(x=fin["period_label"], y=fin["net_margin"] * 100, name="Net margin",
                    line=dict(color=MUTED, width=2, dash="dot"))
    fig.add_hline(y=0, line_color=RED, line_width=1)
    fig.update_layout(title="Operating and net margin (%)", height=360, margin=dict(l=10, r=10, t=50, b=10),
                      legend=dict(orientation="h", y=-0.3), yaxis=dict(range=[-40, 25]),
                      xaxis=dict(tickangle=-45, nticks=16))
    st.plotly_chart(fig, use_container_width=True)
    low = fin.loc[fin["operating_margin"] * 100 < -40, ["period_label", "operating_margin"]]
    if not low.empty:
        footnote("Below the axis: " + ", ".join(f"{p} ({m:.0%})" for p, m in low.itertuples(index=False)) + ".")

st.subheader("Cash generation")
fig = go.Figure()
fig.add_bar(x=fin["period_label"], y=fin["operating_cash_flow"] / 1e9, name="Operating cash flow", marker_color=BLUE)
fig.add_bar(x=fin["period_label"], y=-fin["capex_total"] / 1e9, name="Capital expenditures", marker_color="#9ca3af")
fig.add_scatter(x=fin["period_label"], y=fin["free_cash_flow"] / 1e9, name="Free cash flow", mode="lines+markers",
                line=dict(color=INK))
fig.update_layout(barmode="relative", height=340, margin=dict(l=10, r=10, t=20, b=10),
                  yaxis_title="$B", legend=dict(orientation="h", y=-0.35), xaxis=dict(tickangle=-45, nticks=20))
st.plotly_chart(fig, use_container_width=True)

summary = js("fpa_model_summary.json")
qa = js("qa_summary.json")
st.subheader("Where to look next")
st.markdown(
    f"- **Network 3D**: DL-operated routes for {qa['network']['ttm_start'][:7]} to {qa['network']['ttm_end'][:7]} "
    "compared with 2019.\n"
    f"- **Unit economics**: mainline revenue and cost per seat-mile through {summary['latest_actual']}.\n"
    "- **Profit bridge**: which drivers moved mainline operating income year over year.\n"
    f"- **Scenario lab**: base, upside and downside for {summary['forecast_quarters'][0]} to "
    f"{summary['forecast_quarters'][-1]}, with your own driver changes."
)
footnote(qa["scope_note"])
