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
    map_style="light",
    initial_view_state=pdk.ViewState(latitude=36, longitude=-60, zoom=1.6, pitch=40),
    layers=[
        pdk.Layer("ArcLayer", data=view, get_source_position=["origin_lon", "origin_lat"],
                  get_target_position=["destination_lon", "destination_lat"], get_source_color="color",
                  get_target_color="color", get_width="width", pickable=True, auto_highlight=True),
        pdk.Layer("ScatterplotLayer", data=airports, get_position=["longitude", "latitude"], get_radius="radius",
                  get_fill_color=[31, 41, 55, 140], pickable=True),
    ],
    tooltip={"text": "{route_id}{airport_code}\n{passengers}{departing_passengers_ttm} passengers"},
)
st.pydeck_chart(deck, use_container_width=True, height=560)
footnote(f"{qa['airports']['ttm_routes_without_coordinates']} routes lack coordinates and are left off the map; "
         f"mapped routes carry {pct(qa['airports']['ttm_passenger_share_on_mapped_routes'], 2)} of passengers in "
         "the window. Blue: domestic. Amber: international.")

st.subheader("What changed since 2019")
structure = csv("network_structure.csv")
s1, s2 = st.columns(2)
with s1:
    fig = go.Figure()
    fig.add_bar(x=structure["window"], y=structure["passengers"] / 1e6, marker_color=BLUE, name="Passengers")
    fig.update_layout(title="Passengers by year (millions)", height=320, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)
with s2:
    fig = go.Figure()
    fig.add_scatter(x=structure["window"], y=structure["international_asm_share"] * 100, name="International share of ASMs",
                    line=dict(color=INK))
    fig.add_scatter(x=structure["window"], y=structure["top20_market_passenger_share"] * 100,
                    name="Top 20 markets' share of passengers", line=dict(color=BLUE, dash="dot"))
    fig.update_layout(title="Network mix (%)", height=320, margin=dict(l=10, r=10, t=50, b=10),
                      legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig, use_container_width=True)
footnote("Years with fewer than twelve loaded months are partial; compare the TTM bar with 2019.")

a1, a2 = st.columns(2)
markets = csv("market_ttm_vs_2019.csv")
with a1:
    st.markdown("**City pairs with the largest passenger gains (TTM vs 2019)**")
    st.dataframe(markets.head(15)[["market_id", "scope", "passengers_base", "passengers_ttm", "passenger_change",
                                   "passenger_change_pct"]], hide_index=True, use_container_width=True)
with a2:
    st.markdown("**City pairs with the largest passenger declines**")
    st.dataframe(markets.sort_values("passenger_change").head(15)[
        ["market_id", "scope", "passengers_base", "passengers_ttm", "passenger_change", "status"]],
        hide_index=True, use_container_width=True)

st.markdown("**Airports: departing passengers and share of the network**")
air = csv("airport_ttm_vs_2019.csv")
st.dataframe(air.head(30)[["airport_code", "departing_passengers_base", "departing_passengers_ttm",
                           "passenger_change_pct", "share_base", "share_ttm", "share_change_pts"]],
             hide_index=True, use_container_width=True)
counts = pd.Series(markets["status"]).value_counts()
footnote(f"Markets in the comparison: {counts.get('continuing', 0)} served in both windows, "
         f"{counts.get('new', 0)} new since 2019, {counts.get('exited', 0)} no longer served.")
