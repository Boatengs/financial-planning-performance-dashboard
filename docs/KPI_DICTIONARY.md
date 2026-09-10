# KPI Dictionary

The generated `processed/dim_metric.csv` is the machine-readable dictionary. This document is the human-readable audit view.

| KPI | Domain | Unit | Class | Formula / lineage | Availability |
|---|---|---:|---|---|---:|
| `revenue` — Revenue | Financial Performance | USD | Reported | SEC XBRL reported value | 31 |
| `passenger_revenue` — Passenger Revenue | Revenue Mix | USD | Reported | SEC XBRL reported value | 0 |
| `passenger_revenue_mainline` — Passenger Revenue - Mainline | Revenue Mix | USD | Reported | SEC XBRL reported value | 0 |
| `passenger_revenue_regional` — Passenger Revenue - Regional | Revenue Mix | USD | Reported | SEC XBRL reported value | 0 |
| `cargo_revenue` — Cargo & Freight Revenue | Revenue Mix | USD | Reported | SEC XBRL reported value | 0 |
| `operating_income` — Operating Income | Profitability | USD | Reported | SEC XBRL reported value | 31 |
| `net_income` — Net Income | Profitability | USD | Reported | SEC XBRL reported value | 26 |
| `operating_cash_flow` — Operating Cash Flow | Cash Flow | USD | Reported | SEC XBRL reported value | 15 |
| `cash` — Cash & Cash Equivalents | Liquidity | USD | Reported | SEC XBRL reported value | 30 |
| `assets` — Total Assets | Balance Sheet | USD | Reported | SEC XBRL reported value | 30 |
| `liabilities` — Total Liabilities | Balance Sheet | USD | Reported | SEC XBRL reported value | 0 |
| `long_term_debt` — Long-Term Debt | Capital Structure | USD | Reported | SEC XBRL reported value | 27 |
| `debt_total` — Total Debt (Long + Short Term) | Capital Structure | USD | Reported | SEC XBRL reported value | 8 |
| `fuel_costs` — Fuel Costs | Operating Costs | USD | Reported | SEC XBRL reported value | 30 |
| `labor_costs` — Labor & Related Expense | Operating Costs | USD | Reported | SEC XBRL reported value | 30 |
| `maintenance_costs` — Aircraft Maintenance Materials & Repairs | Operating Costs | USD | Reported | SEC XBRL reported value | 30 |
| `flight_equipment_capex` — Payments for Flight Equipment | Capital Expenditure | USD | Reported | SEC XBRL reported value | 15 |
| `ppe_net` — Property, Plant & Equipment, Net | Balance Sheet | USD | Reported | SEC XBRL reported value | 6 |
| `air_traffic_liability` — Air Traffic Liability | Working Capital | USD | Reported | SEC XBRL reported value | 0 |
| `employees` — Employees | Workforce | employee | Reported | SEC XBRL reported value | 6 |
| `passengers` — Passengers | Network / Operations | count | Reported | SUM(passengers) | n/a |
| `seats` — Available Seats | Network / Operations | count | Reported | SUM(seats) | n/a |
| `asm` — Available Seat Miles (ASM) | Network / Operations | seat-miles | Derived | SUM(seats * distance_miles) | n/a |
| `rpm` — Revenue Passenger Miles (RPM) | Network / Operations | passenger-miles | Derived | SUM(passengers * distance_miles) | n/a |
| `load_factor` — Load Factor | Network / Operations | % | Derived | RPM / ASM | n/a |
| `departures_performed` — Departures Performed | Network / Operations | count | Reported | SUM(departures_performed) | n/a |
| `departures_scheduled` — Departures Scheduled | Network / Operations | count | Reported | SUM(departures_scheduled) | n/a |
| `completion_rate` — Completion Rate | Network / Operations | % | Derived | Departures Performed / Departures Scheduled | n/a |
| `passengers_per_departure` — Passengers per Departure | Network / Operations | passengers/departure | Derived | Passengers / Departures Performed | n/a |
| `average_stage_length` — Average Stage Length | Network / Operations | miles | Derived | SUM(distance * departures performed) / SUM(departures performed) | n/a |
| `freight_pounds` — Freight Transported | Network / Operations | lb | Reported | SUM(freight_pounds) | n/a |
| `mail_pounds` — Mail Transported | Network / Operations | lb | Reported | SUM(mail_pounds) | n/a |
| `airborne_hours` — Airborne Time | Network / Operations | hours | Derived | SUM(airborne_minutes) / 60 | n/a |
| `revenue_growth_yoy` — Revenue Growth YoY | Financial Performance | % | Derived | (Revenue_t / Revenue_t-1) - 1 | n/a |
| `operating_margin` — Operating Margin | Profitability | % | Derived | Operating Income / Revenue | n/a |
| `free_cash_flow` — Free Cash Flow | Cash Flow | USD | Derived | Operating Cash Flow - capital expenditures available in model | n/a |
| `actual_vs_budget` — Actual vs Budget Variance | FP&A | USD | Modeled | Actual - Budget | n/a |
| `actual_vs_budget_pct` — Actual vs Budget Variance % | FP&A | % | Modeled | (Actual - Budget) / Budget | n/a |
| `actual_vs_forecast` — Actual vs Forecast Variance | FP&A | USD | Modeled | Actual - Forecast | n/a |
| `forecast_accuracy` — Forecast Accuracy | FP&A | % | Modeled | 1 - ABS(Actual - Forecast) / ABS(Actual) | n/a |
| `forecast_bias` — Forecast Bias | FP&A | % | Modeled | (Forecast - Actual) / ABS(Actual) | n/a |
| `fuel_cost_per_asm` — Fuel Cost per ASM | Unit Economics | USD/ASM | Derived | Fuel Costs / ASM (aligned period) | n/a |
| `revenue_per_asm` — Revenue per ASM | Unit Economics | USD/ASM | Derived | Revenue / ASM (aligned period) | n/a |

## Classification rules

- **Reported**: directly present in an official source field.
- **Derived**: calculated only from reported values with the formula shown.
- **Modeled**: depends on analyst-created Budget/Forecast/Scenario values and is not populated in the foundation.

## CompanyFacts availability warning

A metric definition can exist even when the selected SEC tag has zero usable 2019-2026 framed observations. That is not filled with a substitute value. Those gaps are intended to be addressed later from Delta filing detail or BTS Form 41 with explicit source lineage.
