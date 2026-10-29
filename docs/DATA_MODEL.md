# Data Model

`make build` writes every table below to `processed/` and loads them into one SQLite database,
`processed/delta_fpna_foundation.sqlite`. Reported actuals are never overwritten by modeled values;
modeled rows carry a scenario ID and a forecast origin.

## Fact tables

| Table | Grain | Source | Purpose |
|---|---|---|---|
| `fact_financial_actual` | metric x quarter or fiscal year | SEC CompanyFacts | Consolidated actuals with filing lineage and the method used to obtain each quarter |
| `fact_financial_kpi_derived` | derived metric x period | Derived | Operating and net margin, YoY revenue growth, free cash flow, total liabilities, fuel share of cost |
| `fact_route_aircraft_monthly` | month x origin x destination x entity x service class x aircraft | T-100 | Lowest retained DL segment grain |
| `fact_route_monthly` | month x directional route x scope | T-100 | Route performance with ASM, RPM, load factor, completion |
| `fact_route_annual` | year x directional route x scope | T-100 | Route totals by calendar year |
| `fact_network_kpi_monthly` | month x scope | T-100 | Domestic and international network rollup |
| `fact_form41_pnl_region` | quarter x P-1.2 region | Form 41 P-1.2 | DL profit and loss as filed, in USD |
| `fact_form41_pnl_quarterly` | quarter x scope | Form 41 P-1.2 | Regions collapsed to domestic, international and system |
| `fact_fuel_monthly` / `fact_fuel_quarterly` | month or quarter x scope | Form 41 P-12(a) | Scheduled-service fuel gallons and cost |
| `fact_unit_economics_quarterly` | quarter x scope | Form 41 + T-100 | Mainline PRASM, TRASM, CASM, CASM-ex, yield, fuel price and efficiency |
| `fact_budget_forecast` | quarter x metric x scenario x origin | Model | ACT, BUD, FCT, UP, DOWN values for mainline revenue, expense, income, margin, fuel |
| `fact_driver_assumption` | quarter x driver x scenario x origin | Model | The seven driver values behind every modeled row |
| `fact_budget_variance` | quarter x metric | Model | Actual versus budget |
| `fact_forecast_backtest` | origin x target x metric | Model | Rolling-origin forecast errors, driver model and seasonal naive |

## Analysis tables

| Table | Purpose |
|---|---|
| `analysis_operating_income_bridge` | Operating income change by driver for each year pair and the latest four quarters |
| `analysis_sensitivity` | Change in next-four-quarter operating income for a one-unit move in each driver |
| `analysis_market_ttm_vs_2019` | City-pair passengers, latest twelve months versus 2019, with new and exited markets |
| `analysis_airport_ttm_vs_2019` | Departing passengers and network share by airport, latest twelve months versus 2019 |
| `analysis_network_structure` | Passengers, international share, markets served and concentration by year and TTM |
| `layer_route_ttm` | Latest-twelve-month directional routes with coordinates for the 3D map |
| `check_form41_vs_sec` | Form 41 system revenue as a share of SEC consolidated revenue each quarter |

## Dimensions

| Table | Key | Purpose |
|---|---|---|
| `dim_date` | `date_key` / `period` | Monthly calendar 2019-2027 (covers the forecast horizon) |
| `dim_route` | `route_id` | Directional route, undirected market ID, distance |
| `dim_airport` | `airport_code` | Every observed airport; BTS Master Coordinate first, FAA fallback, unresolved flagged |
| `dim_metric` | `metric_id` | Classification (Reported, Derived, Modeled), unit, formula, source |
| `dim_scenario` | `scenario_id` | ACT, BUD, FCT, UP, DOWN |

## SQLite views

- `vw_network_monthly`: total monthly network performance, domestic plus international.
- `vw_route_12m`: route totals for the latest twelve loaded months (a true trailing window).
- `vw_financial_kpi_long`: reported and derived financial measures in one long table with lineage.
- `vw_financial_quarterly_wide`: one row per quarter with the main SEC measures as columns.

## Keys and rules

T-100 detail natural key: `year + month + origin + destination + carrier_code + carrier_entity_code +
service_class + aircraft_group + aircraft_type + aircraft_configuration + scope`. If overlapping extracts
contain the same key, the later snapshot wins.

SEC facts: one value per reported start and end date, latest filing wins.

Form 41 P-1.2: one row per year, quarter, region and carrier entity; amounts converted from thousands.

Scope: T-100 and Form 41 describe the DL reporting carrier (mainline). SEC figures are consolidated. The
two are compared, never mixed in one ratio.
