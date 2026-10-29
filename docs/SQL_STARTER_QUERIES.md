# Starter SQL Queries

These queries target `processed/delta_fpna_foundation.sqlite`, built by `make build`.

## Top routes, latest twelve months

```sql
SELECT route_id, scope, passengers, seats, load_factor, window_start, window_end
FROM vw_route_12m
ORDER BY passengers DESC
LIMIT 25;
```

## Monthly whole-network trend

```sql
SELECT period, passengers, asm, rpm, load_factor, completion_rate
FROM vw_network_monthly
ORDER BY period;
```

## Consolidated quarterly results (SEC)

```sql
SELECT period_label, revenue, operating_income, net_income, operating_cash_flow, capex_total
FROM vw_financial_quarterly_wide
ORDER BY period_end;
```

## How each quarterly SEC value was obtained

```sql
SELECT metric_id, method, COUNT(*) AS quarters
FROM fact_financial_actual
WHERE period_type <> 'FY'
GROUP BY metric_id, method
ORDER BY metric_id, method;
```

## Mainline unit economics

```sql
SELECT period_label, scope, trasm_cents, casm_cents, casm_ex_fuel_cents, yield_cents, load_factor
FROM fact_unit_economics_quarterly
WHERE scope = 'system'
ORDER BY year, quarter;
```

## Budget versus actual

```sql
SELECT period, metric_id, budget, actual, actual_vs_budget, actual_vs_budget_pct
FROM fact_budget_variance
ORDER BY period;
```

## Next four quarters by scenario

```sql
SELECT scenario_id, SUM(value) AS operating_income
FROM fact_budget_forecast
WHERE metric_id = 'mainline_operating_income'
  AND scenario_id IN ('FCT', 'UP', 'DOWN')
  AND forecast_origin = (SELECT MAX(forecast_origin) FROM fact_budget_forecast WHERE scenario_id = 'FCT')
GROUP BY scenario_id;
```

## Airports gaining and losing share since 2019

```sql
SELECT airport_code, departing_passengers_base, departing_passengers_ttm, share_change_pts
FROM analysis_airport_ttm_vs_2019
ORDER BY share_change_pts DESC;
```
