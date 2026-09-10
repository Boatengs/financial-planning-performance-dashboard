# Project roadmap

## Phase 1 — Data foundation (current)

- Official-source acquisition only
- SEC CompanyFacts financial actuals
- Delta filing workbooks retained for cross-checks / management KPI extraction
- BTS T-100 network facts
- FAA airport-coordinate fallback
- Typed SQLite analytical model
- KPI dictionary, source manifest, validation, reproducibility controls

## Phase 2 — Historical operating layer

- Extend T-100 to 2019–current
- Add BTS Master Coordinate as the preferred global airport location table
- Add Form 41 cost/fuel schedules where analytically justified
- Reconcile carrier scope before any corporate-to-network blended KPI is published

## Phase 3 — FP&A model

- Driver-based budget and rolling forecast
- Actual vs budget / forecast variance bridges
- Base, upside and downside scenarios
- Fuel, capacity, load factor, labor and margin sensitivities
- Forecast accuracy and bias controls

All modeled values remain clearly labeled as analyst-created scenarios, never Delta internal plans.

## Phase 4 — BI dashboard

- Executive financial scorecard
- Revenue / margin / cash performance
- Operating KPI views
- Network and route drilldowns
- Scenario and variance workspace

## Phase 5 — Live 3D network experience

- Interactive airport nodes and route arcs
- Metric-driven encoding for passengers, ASM, RPM, load factor and capacity
- Route / airport selection linked to BI panels
- Performance safeguards for first load and mobile rendering

## Phase 6 — Release quality

- Automated data validation
- Reproducible builds
- Dashboard interaction tests
- Accessibility and performance checks
- Recruiter-facing README / architecture / screenshots
- Live deployment

## Phase 7 — Portfolio integration

Only after the standalone project is complete and validated:

- Add the project to `Boatengs/my-portfolio`
- Publish a polished project card and case study
- Link to the standalone GitHub repository and live application
