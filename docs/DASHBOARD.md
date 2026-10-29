# Dashboard

The Streamlit app in `app/` reads only `data/published/`, so it runs without downloading any source data.

```bash
pip install -r requirements.txt
streamlit run app/Home.py
```

To deploy on Streamlit Community Cloud, point a new app at this repository with `app/Home.py` as the
entry file. The monthly data build refreshes `data/published/`, and the deployed app picks up the new
files on its next restart.

## Pages

| Page | Question it answers | Main data |
|---|---|---|
| Home | How are Delta's consolidated revenue, margin and cash generation trending? | `financial_actual.csv`, `financial_derived.csv` |
| Network 3D | Where is DL capacity and demand today, and what changed since 2019? | `route_layer_ttm.csv`, `airport_ttm_vs_2019.csv`, `market_ttm_vs_2019.csv`, `network_structure.csv` |
| Unit Economics | How do mainline revenue and cost per seat-mile move, by domestic and international? | `unit_economics_quarterly.csv` |
| Profit Bridge | Which drivers moved mainline operating income between two periods? | `operating_income_bridge.csv` |
| Scenario Lab | What do the next four quarters look like under base, upside, downside or your own assumptions, and how accurate has the model been? | `budget_forecast.csv`, `driver_assumptions.csv`, `sensitivity.csv`, `budget_variance.csv`, `fpa_model_summary.json` |
| Methods and Data Quality | Where does each number come from and did the build pass validation? | `validation_report.json`, `source_manifest.csv`, `metric_dictionary.csv` |

The Scenario Lab recomputes operating income with the same `pipeline.fpa_model.outcomes` function the
build uses, so slider results and published scenarios follow one identity.

## Tableau Public

`tableau/` holds a CSV extract built from the same tables, with a route file already in Tableau's path
format. See `tableau/README.md`.
