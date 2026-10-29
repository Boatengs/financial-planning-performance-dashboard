# Roadmap

## Done

- SEC consolidated actuals with every quarter, including Q4 and quarterly cash flow, 2019 onward
- T-100 domestic and international segments for the DL reporting carrier, January 2019 onward
- BTS Master Coordinate airport coordinates with FAA fallback
- Form 41 P-1.2 profit and loss and P-12(a) fuel for scope-matched mainline unit economics
- One build, one SQLite database, one validator
- Network shift analysis: latest twelve months versus 2019 by airport and city pair
- Driver-based FP&A model: rolling forecast, budget, upside and downside, sensitivity, operating income
  bridge, rolling-origin backtest against a seasonal naive baseline
- Streamlit dashboard with a route network map, and a Tableau Public extract
- Monthly scheduled rebuild in GitHub Actions that commits refreshed published outputs

## Possible next steps

- Regional partner flying: add Delta Connection carriers (for example 9E, OO, YX) from T-100 and
  Form 41 to approach consolidated capacity
- Fuel price scenarios from a public forward or futures series instead of holding the origin quarter flat
- Form 41 P-6 and P-5.2 cost detail (labor, maintenance, aircraft ownership) as separate CASM drivers
- Peer comparison with United and American on the same mainline unit-economics basis
