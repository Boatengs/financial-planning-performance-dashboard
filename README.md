# Delta Air Lines: FP&A and Network Analytics

[![Python CI](https://github.com/Boatengs/financial-planning-performance-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/Boatengs/financial-planning-performance-dashboard/actions/workflows/ci.yml)
[![Full Data Build](https://github.com/Boatengs/financial-planning-performance-dashboard/actions/workflows/data-build.yml/badge.svg)](https://github.com/Boatengs/financial-planning-performance-dashboard/actions/workflows/data-build.yml)

A reproducible FP&A model of Delta Air Lines built only from public filings. It joins SEC financial statements, DOT Form 41 airline accounts and BTS T-100 flight segment data, rebuilds operating income from seven operating drivers, and serves the results in a Streamlit dashboard with a 3D route map and a Tableau Public extract.

## The question

**How well does Delta turn capacity into revenue and margin, which routes and airports drive its traffic since 2019, and what does the next year look like under different capacity, fuel and cost assumptions?**

## What the data shows

Figures below come from the build committed in `data/published/` (SEC through Q3 2026, Form 41 through Q2 2026, T-100 through July 2026). "Mainline" means flights Delta operates itself; see [Scope](#scope).

**1. Delta earns less margin on each seat mile than in 2019, because cost outside fuel grew faster than revenue.** Mainline revenue per available seat mile (TRASM) rose 16%, from 15.73¢ in 2019 to 18.19¢ in 2025. Cost per seat mile excluding fuel (CASM-ex) rose 36%, from 10.46¢ to 14.21¢. Mainline operating margin fell from 15.1% to 4.7%. Consolidated SEC figures tell the same story with smaller numbers: operating margin 14.1% in 2019 and 9.2% in 2025, while salaries and related costs went from $11.6B to $17.5B.

**2. The domestic network carries most of that squeeze.** On Form 41's regional split, domestic mainline margin went from 13.5% in 2019 to 0.8% in 2025. International held up better, at 18.3% then and 11.9% now.

**3. Fuel has hidden the cost problem, until 2026.** Year over year, cheaper fuel added $0.92B to mainline operating income in 2024 and $0.99B in 2025. Higher CASM-ex took back $1.09B and $0.82B. In 2025, a 1.5 point drop in load factor cost another $0.92B. In Q2 2026 fuel jumped to $3.91 a gallon, 73% above Q2 2025. Yield rose 11% in the same quarter, but mainline margin still fell from 9.1% to 6.8%.

**4. The next four quarters depend mostly on whether fuel stays high.** The base forecast for Q3 2026 to Q2 2027 is $2.12B of mainline operating income. If fuel stays at the Q2 2026 price and nothing else adjusts, that becomes a $2.24B loss. The upside and downside cases give $5.35B and a $3.05B loss. Load factor and yield matter far more than growth: one point of load factor is worth $0.64B over the year and 1% of yield $0.53B, while 1% more capacity adds only $0.02B, because at today's margins an extra seat mile earns barely more than it costs.

**5. The network is bigger but less full and less concentrated than in 2019.** Comparing the latest twelve months (August 2025 to July 2026) with 2019: seat miles up 11.8%, passengers up only 2.2%, and load factor down from 86.8% to 84.0%. The top 20 city pairs now carry 14.5% of passengers, down from 16.2%.

**6. Growth has moved away from the big hubs.** Atlanta's share of departing passengers fell from 24.1% to 23.1%, Minneapolis from 6.4% to 6.0%, Detroit from 5.8% to 5.4%. Boston grew 47%, to 4.4 million departing passengers. Austin grew 51% and Salt Lake City 11%. Several of the fastest growing city pairs are short routes from Atlanta (Asheville, Lexington, Gainesville, Knoxville). T-100 for DL excludes Delta Connection partners, so part of that growth may be flying moved onto Delta's own aircraft rather than new demand. I haven't added partner carriers to test it.

**7. Simple beats clever for the point forecast.** In a rolling origin backtest from Q4 2023 (34 forecasts, one to four quarters ahead), carrying each driver forward from the same quarter a year earlier had the lowest errors: 3.96% on revenue and $0.225B on operating income. Every method that extrapolated recent trends did worse; the closest, a two quarter trend, reached 4.89% and $0.246B. So the base case uses the simple method. The model's value is in the decomposition, scenarios and bridge, not in beating a naive baseline on point accuracy.

## Scope

Three sources, two reporting scopes. They are compared but never mixed in one ratio.

| Source | Covers | Used for |
|---|---|---|
| SEC CompanyFacts | Delta Air Lines, Inc., consolidated | Revenue, costs, income, cash flow, capex, cash, debt |
| DOT Form 41 (P-1.2, P-12(a)) | DL reporting carrier | Passenger revenue, operating revenue and expense by region, fuel gallons and cost |
| BTS T-100 segments | DL reporting carrier | Seat miles, passenger miles, passengers, departures, routes |

DL's Form 41 operating revenue equals 100.0% to 100.4% of SEC consolidated revenue in every quarter, so the two sources agree. Form 41 revenue includes partner flights that T-100 for DL doesn't count. Mainline unit measures therefore remove the Form 41 lines for transport related revenue and expense, the lines that hold regional partner flying. They are public measures matched to one scope, not Delta's investor relations TRASM and CASM.

Budget, forecast and scenario values are my own models built on these public actuals. They are not Delta guidance.

## How the model works

Operating income is rebuilt exactly from seven drivers each quarter:

```text
revenue  = ASM x load factor x yield x (1 + other revenue ratio)
expense  = ASM x CASM-ex fuel + (ASM / ASMs per gallon) x fuel price
income   = revenue - expense
```

| Output | Method |
|---|---|
| Base forecast | Each driver equals the same quarter a year earlier (chosen by backtest) |
| Budget | The base method run from Q4 of the prior year |
| Fuel at latest price | Base, with fuel held at the latest quarter's actual price |
| Upside / downside | Base with stated shocks: capacity +1% / -2%, load factor +1 / -2 pts, yield +2% / -3%, CASM-ex -1% / +2%, fuel -10% / +15% |
| Sensitivity | Change in next four quarters' income for one unit of each driver |
| Bridge | Year over year change in income split by driver, by sequential substitution |
| Backtest | Eight methods, rolling origin from Q4 2023; earlier origins are excluded because their trends come from the pandemic recovery |

## Data fixes behind these numbers

The first version of this repository had gaps that would have distorted every chart. They are now fixed and checked by the validator.

| Problem | Fix |
|---|---|
| SEC data selected by calendar "frame" dropped every Q4 and most quarterly cash flow | Read each fact's start and end dates; Q4 = full year minus nine months; Q2 and Q3 cash flow from year to date differences |
| Annual net income missing for 2021 to 2025 | Same fix |
| Total capex not tagged in 2026 filings | Flight equipment plus ground and technology (the identity holds within $2M where all three exist) |
| Total debt not tagged for Q1 to Q3 2020 | Filled from a second SEC tag that matches wherever both exist |
| 111 then 177 airports had no coordinates, including LHR, CDG and YYZ | Download the BTS Master Coordinate table; every airport in the latest twelve months is now mapped |
| The "12 month" route view summed every loaded month | Now a true trailing twelve months |
| Two separate builds wrote the same files and neither produced one database | One build, one SQLite database, one validator |
| SEC refuses GitHub's cloud runners | A dated, filtered CompanyFacts snapshot is committed and used as a fallback; the build records which source it used |

## Dashboard

```bash
pip install -r requirements.txt
streamlit run app/Home.py
```

| Page | Shows |
|---|---|
| Home | Consolidated revenue, margins and cash generation |
| Network 3D | Latest twelve months of routes as 3D arcs, airports sized by passengers, change versus 2019 |
| Unit Economics | Mainline TRASM, CASM, CASM-ex, yield, load factor and fuel by domestic and international |
| Profit Bridge | Operating income change by driver for any year pair |
| Scenario Lab | Base, fuel, upside and downside paths, your own driver sliders, sensitivity, budget variance, method backtest |
| Methods and Data Quality | Validation checks, sources, metric dictionary |

The `tableau/` folder holds the same data as CSV files ready for Tableau Public, including a route file in Tableau's path format. See [tableau/README.md](tableau/README.md).

## Rebuild

Python 3.11 or later. The pipeline uses only the standard library.

```bash
make download   # SEC, FAA, T-100 2019 to 2026, Form 41, Master Coordinate
make build      # every mart, the model and processed/delta_fpna_foundation.sqlite
make validate   # independent checks; fails the build on any error
make check      # compile and run the unit tests
```

The [Full Data Build](.github/workflows/data-build.yml) workflow runs the same steps monthly and commits refreshed `data/published/`, `tableau/` and the data quality docs.

## Validation

The validator checks 24 conditions on every build, including: every quarter from Q1 2019 has the core SEC metrics; four quarters sum to the reported year within $3M; T-100 route and network totals reconcile; Form 41 domestic plus international equals system; Form 41 revenue is within 2% of SEC revenue; the map covers at least 99% of passengers; the drivers rebuild reported income to the dollar; every bridge closes. Results: [docs/DATA_QUALITY.md](docs/DATA_QUALITY.md).

## Repository

```text
app/              Streamlit dashboard (reads data/published only)
pipeline/         acquisition, parsing, marts, unit economics, FP&A model, publishing
scripts/          download, build, validate, regenerate docs
tests/            unit tests on synthetic fixtures
data/published/   compact validated outputs, committed
tableau/          Tableau Public extract, committed
raw/              source landing area; manifests and the SEC snapshot are committed, extracts are not
processed/        full build outputs and the SQLite database, not committed
docs/             data model, sources, KPI dictionary, data quality, dashboard, SQL examples
```

## Limitations

- Mainline only. Delta Connection partners report under their own carrier codes, so network and unit measures exclude them.
- Form 41 regional splits are Delta's own allocations; domestic versus international margins depend on them.
- The fuel scenario holds price flat with no fare response. A futures curve would be a better input.
- The backtest has 34 forecasts over ten origins, so the ranking of methods is itself uncertain.
- The 2026 calendar year is partial in the network tables; compare the trailing twelve months with 2019.

## Sources

SEC CompanyFacts for CIK 0000027904; BTS TranStats T-100 Domestic (table 259) and International (261) Segment; Form 41 Schedules P-1.2 (295) and P-12(a) (294); Aviation Support Tables Master Coordinate (288); FAA NASR airport data. Full URLs and roles: [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).
