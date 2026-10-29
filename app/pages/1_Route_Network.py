"""Where Delta flies: busiest city pairs on a flat map, top routes and hubs, and change since 2019."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import AMBER, BLUE, INK, csv, footnote, js, page_setup, pct, require_data

page_setup("Route Network")
require_data()
qa = js("qa_summary.json")
window = f"{qa['network']['ttm_start'][:7]} to {qa['network']['ttm_end'][:7]}"

st.title("Route network")
st.caption(f"Flights operated by Delta itself, latest twelve months ({window}). Source: BTS T-100; airport "
           "locations from BTS Master Coordinate with FAA fallback.")


def great_circle_midpoint(lat1, lon1, lat2, lon2):
    """Midpoint on the great circle, which is where plotly draws the line."""
    p1, l1, p2, l2 = map(np.radians, (lat1, lon1, lat2, lon2))
    bx, by = np.cos(p2) * np.cos(l2 - l1), np.cos(p2) * np.sin(l2 - l1)
    lat = np.arctan2(np.sin(p1) + np.sin(p2), np.sqrt((np.cos(p1) + bx) ** 2 + by ** 2))
    lon = l1 + np.arctan2(by, np.cos(p1) + bx)
    return np.degrees(lat), (np.degrees(lon) + 540) % 360 - 180


def millions(x: float) -> str:
    return f"{x / 1e6:,.1f}M" if x >= 1e6 else f"{x / 1e3:,.0f}K"


# Routes are reported once per direction; combine both directions into one city pair.
layer = csv("route_layer_ttm.csv")
ends = np.sort(layer[["origin", "destination"]].to_numpy(), axis=1)
layer["pair"] = [f"{a}\u2013{b}" for a, b in ends]
first = layer.sort_values("passengers", ascending=False).drop_duplicates("pair")
pairs = (layer.groupby("pair", as_index=False)
         .agg(passengers=("passengers", "sum"), flights=("departures_performed", "sum"))
         .merge(first[["pair", "scope", "origin", "destination", "origin_name", "destination_name",
                       "origin_lat", "origin_lon", "destination_lat", "destination_lon"]], on="pair")
         .sort_values("passengers", ascending=False))
airports = csv("airport_ttm_vs_2019.csv").merge(
    csv("airports.csv")[["airport_code", "latitude", "longitude", "airport_name", "city"]], on="airport_code")
airports = airports.dropna(subset=["latitude", "longitude"])
total = pairs["passengers"].sum()

m = st.columns(4)
m[0].metric("City pairs served", f"{len(pairs):,}")
m[1].metric("Passengers carried", millions(total))
top_hub = airports.sort_values("departing_passengers_ttm", ascending=False).iloc[0]
m[2].metric(f"Busiest airport ({top_hub.airport_code})", pct(top_hub.share_ttm),
            help="Share of all departing passengers on Delta-operated flights.")
intl = pairs.loc[pairs["scope"] == "international", "passengers"].sum() / total
m[3].metric("International share of passengers", pct(intl))

st.subheader("Where Delta flies")
st.markdown("Each line is one **city pair**, flights in both directions combined. **Thicker lines carry more "
            "passengers.** Circles are airports, sized by how many passengers depart from them; the largest "
            "are labeled. Hover over a line's midpoint or an airport for its numbers.")
c1, c2 = st.columns([1, 1])
view_choice = c1.radio("Map", ["Domestic routes (U.S.)", "International routes (world)"], horizontal=True)
top_n = c2.slider("Busiest city pairs shown", 10, 100, 30, step=5)
domestic = view_choice.startswith("Domestic")
shown = pairs[pairs["scope"] == ("domestic" if domestic else "international")].head(top_n)
color = BLUE if domestic else AMBER

fig = go.Figure()
peak = shown["passengers"].max()
for row in shown.itertuples():
    fig.add_trace(go.Scattergeo(
        lon=[row.origin_lon, row.destination_lon], lat=[row.origin_lat, row.destination_lat], mode="lines",
        line=dict(width=1 + 7 * np.sqrt(row.passengers / peak), color=color), opacity=0.55,
        hoverinfo="skip", showlegend=False))
mid_lat, mid_lon = great_circle_midpoint(shown["origin_lat"], shown["origin_lon"],
                                         shown["destination_lat"], shown["destination_lon"])
fig.add_trace(go.Scattergeo(
    lon=mid_lon, lat=mid_lat, mode="markers",
    marker=dict(size=7, color=color, opacity=0.9), showlegend=False,
    text=[f"<b>{r.pair}</b><br>{r.origin_name} \u2013 {r.destination_name}<br>{millions(r.passengers)} passengers"
          f"<br>{r.flights:,.0f} flights" for r in shown.itertuples()],
    hovertemplate="%{text}<extra></extra>"))
codes = set(shown["origin"]) | set(shown["destination"])
hubs = airports[airports["airport_code"].isin(codes)].sort_values("departing_passengers_ttm", ascending=False)
hub_peak = hubs["departing_passengers_ttm"].max()
labels = set(hubs.head(8)["airport_code"])
fig.add_trace(go.Scattergeo(
    lon=hubs["longitude"], lat=hubs["latitude"],
    mode="markers+text", text=[c if c in labels else "" for c in hubs["airport_code"]],
    textposition="top center", textfont=dict(size=12, color=INK),
    marker=dict(size=6 + 22 * np.sqrt(hubs["departing_passengers_ttm"] / hub_peak), color=INK,
                opacity=0.75, line=dict(width=1, color="white")),
    customdata=np.stack([hubs["airport_name"], hubs["departing_passengers_ttm"].map(millions)], axis=1),
    hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} departing passengers<extra></extra>",
    showlegend=False))
geo = dict(showland=True, landcolor="#f3f4f6", showcountries=True, countrycolor="#d1d5db",
           showsubunits=True, subunitcolor="#e5e7eb", showocean=True, oceancolor="#ffffff",
           showlakes=False, coastlinecolor="#d1d5db")
if domestic:
    geo.update(scope="usa")
else:
    geo.update(projection_type="natural earth", center=dict(lat=15, lon=-20), projection_scale=1.0)
fig.update_layout(geo=geo, height=560, margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig, width="stretch")
shown_share = shown["passengers"].sum() / total
missing = qa["airports"]["ttm_routes_without_coordinates"]
footnote(f"The {len(shown)} pairs shown carry {pct(shown_share)} of all passengers in the window. Lines are "
         "the shortest path between airports, not actual flight tracks."
         + (f" {missing} routes lack coordinates and are left off." if missing else ""))

b1, b2 = st.columns(2)
with b1:
    top15 = pairs.head(15).iloc[::-1]
    fig = go.Figure(go.Bar(
        x=top15["passengers"] / 1e6, y=top15["pair"], orientation="h",
        marker_color=[BLUE if s == "domestic" else AMBER for s in top15["scope"]],
        text=[millions(v) for v in top15["passengers"]], textposition="outside",
        hovertext=[f"{a} \u2013 {b}" for a, b in zip(top15["origin_name"], top15["destination_name"])]))
    fig.update_layout(title="Busiest city pairs (millions of passengers)", height=470,
                      margin=dict(l=10, r=10, t=50, b=10),
                      xaxis=dict(title=None, range=[0, top15["passengers"].max() / 1e6 * 1.18]))
    st.plotly_chart(fig, width="stretch")
with b2:
    top_hubs = airports.sort_values("departing_passengers_ttm", ascending=False).head(10).iloc[::-1]
    fig = go.Figure(go.Bar(
        x=top_hubs["share_ttm"] * 100, y=top_hubs["airport_code"] + "  " + top_hubs["city"].fillna(""),
        orientation="h", marker_color=INK, text=[pct(v) for v in top_hubs["share_ttm"]],
        textposition="outside"))
    fig.update_layout(title="Largest airports (share of departing passengers, %)", height=470,
                      margin=dict(l=10, r=10, t=50, b=10),
                      xaxis=dict(range=[0, top_hubs["share_ttm"].max() * 100 * 1.2]))
    st.plotly_chart(fig, width="stretch")
footnote("Blue bars are domestic city pairs, amber international. The largest airport's share shows how "
         "much of the network runs through one hub.")

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
