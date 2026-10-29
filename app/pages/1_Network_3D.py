"""DL route network on a 3D map, and how it shifted versus 2019."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from data import BLUE, INK, csv, footnote, js, page_setup, pct, require_data

page_setup("Network 3D")
require_data()
qa = js("qa_summary.json")
window = f"{qa['network']['ttm_start'][:7]} to {qa['network']['ttm_end'][:7]}"

st.title("Network 3D")
st.caption(f"DL-operated segments, latest twelve months ({window}). Source: BTS T-100; coordinates from BTS "
           "Master Coordinate with FAA fallback.")

layer = csv("route_layer_ttm.csv")
c1, c2, c3 = st.columns([1, 1, 2])
metric = c1.selectbox("Arc weight", ["passengers", "asm", "departures_performed", "seats"],
                      format_func=lambda m: {"passengers": "Passengers", "asm": "Available seat-miles",
                                             "departures_performed": "Departures", "seats": "Seats"}[m])
scope = c2.selectbox("Scope", ["all", "domestic", "international"], format_func=str.title)
top_n = c3.slider("Routes shown (largest first)", 100, int(min(3000, len(layer))), min(800, len(layer)), step=100)

view = layer if scope == "all" else layer[layer["scope"] == scope]
view = view.sort_values(metric, ascending=False).head(top_n).copy()
scale = view[metric].max() or 1
view["width"] = 1 + 9 * np.sqrt(view[metric] / scale)
view["color"] = view["scope"].map({"domestic": [29, 78, 216, 150], "international": [180, 83, 9, 170]})

airports = csv("airport_ttm_vs_2019.csv").merge(csv("airports.csv")[["airport_code", "latitude", "longitude",
                                                                      "airport_name"]], on="airport_code")
airports = airports.dropna(subset=["latitude", "longitude"])
airports = airports[airports["departing_passengers_ttm"] > 0].copy()
airports["radius"] = 4000 + 60000 * np.sqrt(airports["departing_passengers_ttm"] / airports["departing_passengers_ttm"].max())

deck = pdk.Deck(
    map_provider="carto",
    map_style=pdk.map_styles.CARTO_LIGHT,
    initial_view_state=pdk.ViewState(latitude=32, longitude=-45, zoom=1.2, pitch=35),
    layers=[
        pdk.Layer("ArcLayer", data=view, get_source_position=["origin_lon", "origin_lat"],
                  get_target_position=["destination_lon", "destination_lat"], get_source_color="color",
                  get_target_color="color", get_width="width", pickable=True, auto_highlight=True),
        pdk.Layer("ScatterplotLayer", data=airports, get_position=["longitude", "latitude"], get_radius="radius",
                  get_fill_color=[31, 41, 55, 140], pickable=True),
    ],
    tooltip={"text": "{route_id}{airport_code}\n{passengers}{departing_passengers_ttm} passengers"},
)
st.pydeck_chart(deck, width="stretch", height=560)
footnote(f"{qa['airports']['ttm_routes_without_coordinates']} routes lack coordinates and are left off the map; "
         f"mapped routes carry {pct(qa['airports']['ttm_passenger_share_on_mapped_routes'], 2)} of passengers in "
         "the window. Blue: domestic. Amber: international.")

st.subheader("What changed since 2019")
structure = csv("network_structure.csv").astype({"window": str})
s1, s2 = st.columns(2)
with s1:
    fig = go.Figure()
    fig.add_bar(x=structure["window"], y=structure["passengers"] / 1e6, marker_color=BLUE, name="Passengers")
    fig.update_layout(title="Passengers by year (millions)", height=320, margin=dict(l=10, r=10, t=50, b=10),
                      xaxis=dict(type="category"))
    st.plotly_chart(fig, width="stretch")
with s2:
    fig = go.Figure()
    fig.add_scatter(x=structure["window"], y=structure["international_asm_share"] * 100, name="International share of ASMs",
                    line=dict(color=INK))
    fig.add_scatter(x=structure["window"], y=structure["top20_market_passenger_share"] * 100,
                    name="Top 20 markets' share of passengers", line=dict(color=BLUE, dash="dot"))
    fig.update_layout(title="Network mix (%)", height=320, margin=dict(l=10, r=10, t=50, b=10),
                      legend=dict(orientation="h", y=-0.25), xaxis=dict(type="category"))
    st.plotly_chart(fig, width="stretch")
footnote("Years with fewer than twelve loaded months are partial; compare the TTM bar with 2019.")

a1, a2 = st.columns(2)
markets = csv("market_ttm_vs_2019.csv")
market_cols = {"market_id": "City pair", "scope": "Scope", "passengers_base": "2019", "passengers_ttm": "Latest 12 months",
               "passenger_change": "Change", "passenger_change_pct": "Change %", "status": "Status"}
fmt = {"2019": "{:,.0f}", "Latest 12 months": "{:,.0f}", "Change": "{:+,.0f}", "Change %": "{:+.0%}"}
with a1:
    st.markdown("**City pairs with the largest passenger gains (latest 12 months vs 2019)**")
    top = markets.head(15)[list(market_cols)].rename(columns=market_cols)
    st.dataframe(top.style.format(fmt, na_rep="new"), hide_index=True, width="stretch")
with a2:
    st.markdown("**City pairs with the largest passenger declines**")
    bottom = markets.sort_values("passenger_change").head(15)[list(market_cols)].rename(columns=market_cols)
    st.dataframe(bottom.style.format(fmt, na_rep="new"), hide_index=True, width="stretch")

st.markdown("**Airports: departing passengers and share of the network**")
air = csv("airport_ttm_vs_2019.csv")
air_cols = {"airport_code": "Airport", "departing_passengers_base": "2019", "departing_passengers_ttm": "Latest 12 months",
            "passenger_change_pct": "Change %", "share_base": "Share 2019", "share_ttm": "Share now",
            "share_change_pts": "Share change (pts)"}
st.dataframe(air.head(30)[list(air_cols)].rename(columns=air_cols).style.format(
    {"2019": "{:,.0f}", "Latest 12 months": "{:,.0f}", "Change %": "{:+.1%}", "Share 2019": "{:.1%}",
     "Share now": "{:.1%}", "Share change (pts)": "{:+.2f}"}, na_rep="new"), hide_index=True, width="stretch")
footnote("Delta Connection partners report under their own carrier codes, so growth on short routes can reflect "
         "flying moved onto Delta-operated aircraft rather than new demand.")
counts = pd.Series(markets["status"]).value_counts()
footnote(f"Markets in the comparison: {counts.get('continuing', 0)} served in both windows, "
         f"{counts.get('new', 0)} new since 2019, {counts.get('exited', 0)} no longer served.")
