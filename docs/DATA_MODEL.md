# Data Model

## Design principle

A star-schema-style analytical layer separates reported financial facts, route operations, dimensions, and future analyst-created planning scenarios. Reported actuals are never overwritten by modeled values.

## Fact tables

| Table | Grain | Purpose |
|---|---|---|
| `fact_financial_actual` | metric × period-end | SEC/XBRL reported financial actuals with accession, form, filed date and taxonomy provenance. |
| `fact_financial_kpi_derived` | derived metric × period-end | Operating margin and YoY revenue growth calculated only from matched SEC periods. |
| `fact_route_aircraft_monthly` | month × origin × destination × carrier entity × service class × aircraft type/config | Lowest retained T-100 DL segment grain. |
| `fact_route_monthly` | month × directional route × domestic/international scope | BI-ready route performance with ASM, RPM, load factor and completion metrics. |
| `fact_network_kpi_monthly` | month × scope | Domestic/international network rollup. |
| `fact_budget_forecast_template` | period × metric × scenario | Empty schema for modeled Budget / Forecast / Upside / Downside values. |
| `fact_driver_assumption_template` | period × driver × scenario | Empty schema for documented FP&A assumptions. |

## Dimensions

| Table | Key | Purpose |
|---|---|---|
| `dim_date` | `date_key` / `period` | Monthly calendar from 2019-2026. |
| `dim_route` | `route_id` | Directional route plus undirected market ID and distance. |
| `dim_airport` | `airport_code` | All observed T-100 airport codes; BTS coordinate preferred, FAA fallback, unresolved explicitly flagged. |
| `dim_metric` | `metric_id` | KPI classification, unit, formula, source system and source-field lineage. |
| `dim_scenario` | `scenario_id` | ACT/BUD/FCT/UP/DOWN with Reported vs Modeled distinction. |

## SQLite views

- `vw_network_monthly` — total monthly network performance across domestic + international.
- `vw_route_12m` — current loaded-period route rollup for 3D/network ranking.
- `vw_financial_actual_latest` — latest-filed observation by metric and period.
- `vw_financial_kpi_long` — normalized union of reported and safely derived financial KPIs.

## Natural-key/revision rule for T-100

The detail natural key is:

`year + month + origin + destination + carrier_code + carrier_entity_code + service_class + aircraft_group + aircraft_type + aircraft_configuration`

If multiple official rolling releases contain the same key, the row from the later source release date wins. This is necessary because BTS may revise recent months.

## Join paths for dashboard

`fact_route_monthly.origin -> dim_airport.airport_code`

`fact_route_monthly.destination -> dim_airport.airport_code`

`fact_route_monthly.period -> dim_date.period`

`fact_financial_actual.metric_id -> dim_metric.metric_id`

Future planning facts join to `dim_metric`, `dim_date`, and `dim_scenario`.
