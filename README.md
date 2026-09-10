# Financial Planning & Performance Dashboard — Data Foundation

Delta Air Lines case-study data foundation for a portfolio-grade FP&A + BI + 3D network dashboard.

## Current state

The build is reproducible from official-source files only. It currently combines SEC CompanyFacts financial actuals with BTS T-100 DL-reported segment traffic/capacity, plus FAA airport coordinates as a U.S.-focused fallback.

**Current validated coverage**

- Financial actual rows: 315
- Safely derived financial KPI rows: 57
- T-100 aircraft-detail rows: 46,666
- T-100 route-month rows: 22,332
- Directional routes: 5,017
- Airports observed: 334
- Airports with coordinates: 223
- Current T-100 period: 2025-06-01 through 2026-05-01
- KPI dictionary rows: 43
- Modeled scenario rows populated: **0**

## Source policy

No Kaggle datasets. Reported facts come only from official company/regulatory/government sources. Derived KPIs are formula-labeled. Budget/Forecast/Upside/Downside values are analyst-modeled and must never be presented as Delta internal planning data.

## One-command rebuild

```bash
python scripts/build_data_foundation.py
python scripts/validate_foundation.py
```

Both scripts use only the Python standard library.

## Historical T-100 acquisition

```bash
python scripts/download_t100_history.py --years 2019 2020 2021 2022 2023 2024 2025
python scripts/build_data_foundation.py
python scripts/validate_foundation.py
```

The downloader contains official bts.gov archive URLs and writes SHA-256 hashes after download. The build uses release-date precedence so overlapping rolling releases do not double count revised records.

## BTS Master Coordinate

For the 3D network, place the official BTS Master Coordinate CSV in `raw/` as any of:

- `bts_master_coordinate.csv`
- `Master_Coordinate.csv`
- `T_MASTER_CORD.csv`

The builder automatically prefers BTS latitude/longitude when present and falls back to FAA. Airports still unresolved remain flagged `pending_bts_master_coordinate`; no coordinates are fabricated.

## Important scope statement

The current T-100 layer includes records whose **reporting carrier code is `DL`**. Do not label it as every Delta-marketed flight or all Delta Connection affiliate flying unless those carriers are explicitly added in a later scope expansion.

## Key folders

- `raw/` — official source files retained byte-for-byte locally; acquisition scripts reproduce them
- `processed/` — BI-ready analytical outputs; heavy generated marts/database are not versioned in Git
- `scripts/` — deterministic build, validation and official-source acquisition scripts
- `docs/` — model, KPI, source and quality documentation

## Repository workflow

The standalone project is built and validated here first. Only the finished, production-ready project is later surfaced in `Boatengs/my-portfolio`.
