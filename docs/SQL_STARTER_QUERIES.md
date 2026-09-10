# Starter SQL Queries

These queries target `processed/delta_fpna_foundation.sqlite`.

## Top routes by passengers

```sql
SELECT route_id, origin, destination, scope, passengers, seats, load_factor
FROM vw_route_12m
ORDER BY passengers DESC
LIMIT 25;
```

## Monthly whole-network trend

```sql
SELECT period, passengers, seats, asm, rpm, load_factor, completion_rate
FROM vw_network_monthly
ORDER BY period;
```

## 3D route layer with coordinate coverage

```sql
SELECT
  r.route_id,
  r.origin,
  o.latitude  AS origin_latitude,
  o.longitude AS origin_longitude,
  r.destination,
  d.latitude  AS destination_latitude,
  d.longitude AS destination_longitude,
  r.passengers,
  r.asm,
  r.rpm,
  r.load_factor
FROM vw_route_12m r
JOIN dim_airport o ON o.airport_code = r.origin
JOIN dim_airport d ON d.airport_code = r.destination
WHERE o.latitude IS NOT NULL
  AND o.longitude IS NOT NULL
  AND d.latitude IS NOT NULL
  AND d.longitude IS NOT NULL
ORDER BY r.passengers DESC;
```

## Reported + safe derived financial KPI history

```sql
SELECT metric_id, metric_name, period_end, period_type, value, unit, source
FROM vw_financial_kpi_long
WHERE metric_id IN ('revenue','operating_income','operating_margin','revenue_growth_yoy')
ORDER BY period_end, metric_id;
```

## Metrics intentionally unavailable from selected CompanyFacts tags

```sql
SELECT metric_id, metric_name, source_field, availability_count_2019_2026
FROM dim_metric
WHERE source_system = 'SEC CompanyFacts'
  AND COALESCE(availability_count_2019_2026,0) = 0;
```

## Coordinate control

```sql
SELECT coordinate_status, COUNT(*) AS airport_count
FROM dim_airport
GROUP BY coordinate_status
ORDER BY airport_count DESC;
```
