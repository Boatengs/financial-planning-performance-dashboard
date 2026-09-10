# Technical Roadmap

## Phase 1 — Data foundation

- SEC CompanyFacts financial actuals
- Delta 10-K and 10-Q filing ingestion
- BTS T-100 domestic and international segment ingestion
- FAA airport-coordinate fallback
- typed SQLite analytical model
- KPI dictionary and source lineage
- deterministic validation and reproducibility controls

## Phase 2 — Historical operating model

- extend monthly T-100 coverage to 2019–2026;
- integrate BTS Airport Master Coordinate for global airport coverage;
- reconcile revised and overlapping BTS releases;
- add route, airport, geographic, and aircraft historical dimensions;
- validate period completeness and carrier scope across the historical series.

## Phase 3 — Cost and driver model

- integrate BTS Form 41 operating-cost schedules;
- add fuel cost and consumption measures;
- model maintenance, labor, aircraft operating expense, and capacity drivers;
- reconcile company-level and network-level periods before publishing blended KPIs.

## Phase 4 — FP&A model

- driver-based budget and rolling forecast;
- actual-versus-budget and actual-versus-forecast variance analysis;
- base, upside, and downside scenarios;
- capacity, load factor, fuel, labor, revenue, and margin sensitivities;
- forecast-accuracy and forecast-bias measurement.

## Phase 5 — BI and 3D application

- executive financial scorecard;
- revenue, margin, cash-flow, and capital-performance views;
- operating KPI dashboards;
- route and airport drilldowns;
- scenario and variance workspace;
- interactive 3D airport nodes and route arcs;
- metric-driven network encoding for passengers, ASM, RPM, load factor, and capacity.

## Phase 6 — Production hardening

- automated data-quality tests;
- repeatable source acquisition and deterministic builds;
- application-level interaction tests;
- accessibility and responsive-layout checks;
- first-load and rendering performance validation;
- deployment documentation and release versioning.