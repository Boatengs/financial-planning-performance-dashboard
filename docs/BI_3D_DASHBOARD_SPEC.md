# BI + Live 3D Dashboard Build Specification

## Product goal

A finance-first performance application: executive KPIs and FP&A questions drive the experience; the 3D network is an analytical surface, not decoration.

## Page 1 — Executive Performance

Primary questions:
- How is revenue/profitability trending?
- Which reported KPIs are improving or deteriorating?
- How do network demand/capacity/utilization trends support the financial story?

Core components:
- Revenue, operating income, operating margin, net income, OCF, debt/cash KPI cards.
- YoY trend and variance tiles.
- Network passengers, ASM, RPM, load factor, completion rate.
- Period and domestic/international filters.

## Page 2 — Network 3D

Primary question: where is capacity and demand concentrated?

Required data:
- `fact_route_monthly`
- `dim_airport`
- `dim_route`

3D behavior:
- Origin and destination coordinates define route arcs.
- Arc weight selectable by passengers / ASM / RPM / departures.
- Airport node size selectable by total passengers / seats / departures.
- Clicking an airport or route filters the side panel and monthly trend.
- Routes missing coordinates are excluded from the globe only and counted visibly in a data-coverage control.

## Page 3 — KPI Explorer

- Reported vs Derived vs Modeled classification always visible.
- Formula/lineage drawer sourced from `dim_metric`.
- No metric appears without unit and source/classification.

## Page 4 — FP&A Scenario Lab

Not populated until the modeling phase.

Required scenario labels:
- Actual — reported
- Budget — analyst-modeled
- Forecast — analyst-modeled
- Upside — analyst-modeled
- Downside — analyst-modeled

Scenario controls will eventually include demand/capacity/fuel/labor assumptions only after source-compatible driver data are integrated. No UI should imply these are Delta internal forecasts.

## Page 5 — Cash & Cost Drivers

Requires Form 41 extension before full implementation. Target measures include fuel gallons/cost, aircraft operating expense components, operating cash flow, flight-equipment capex, and liquidity/debt.

## Page 6 — Methods & Data Quality

Must expose:
- source registry
- current data coverage
- carrier-scope note
- coordinate coverage
- reported/derived/modeled definitions
- build/validation status

## Performance target

For the live web application, the browser should receive aggregated route layers rather than the 46k-row raw aircraft detail unless a drill-down explicitly requests it. `vw_route_12m` is the initial route layer for the 3D map; detailed rows stay server/data-layer side.
