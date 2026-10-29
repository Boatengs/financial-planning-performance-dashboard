# Tableau Public extract

These CSV files are built by the pipeline from the same validated tables as the Streamlit app.
In Tableau Public: Connect > Text file, open one file, then drag the others onto the canvas as
related tables where you need them.

| File | Grain | Use |
|---|---|---|
| financial_quarterly_long.csv | metric x quarter or year | SEC consolidated financials, reported and derived |
| unit_economics_quarterly.csv | quarter x scope | Mainline PRASM, TRASM, CASM, yield, fuel (Form 41 + T-100) |
| network_monthly.csv | month x scope | Passengers, ASMs, load factor, completion |
| route_paths_ttm.csv | route x endpoint | Route map: Marks = Line, Path = path_order, Detail = route_id |
| airport_ttm_vs_2019.csv | airport | Departing passengers, latest 12 months versus 2019 |
| market_ttm_vs_2019.csv | market | Passenger change by city pair versus 2019 |
| budget_forecast.csv | quarter x metric x scenario | Actual, budget, forecast, upside, downside |
| operating_income_bridge.csv | period pair x driver | Waterfall of operating income change by driver |

All Budget, Forecast, Upside and Downside values are analyst-modeled from public data. They are
not Delta guidance.
