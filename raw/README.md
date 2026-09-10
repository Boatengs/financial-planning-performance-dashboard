# Raw official sources

Large raw source files are intentionally not committed to Git. They are downloaded from first-party sources into this directory.

## Current foundation

Run:

```bash
python scripts/download_official_sources.py
```

This acquires the current SEC, Delta Investor Relations, FAA, and BTS T-100 inputs at the exact filenames expected by the build pipeline and prints SHA-256 checksums.

For the historical T-100 extension (2019 onward), run:

```bash
python scripts/download_t100_history.py --years 2019 2020 2021 2022 2023 2024 2025
```

The generated `processed/source_manifest.csv` records the source URLs, local file names, sizes, checksums, roles, and pipeline status.

## Source rule

No Kaggle or third-party mirrors. If an official endpoint is unavailable, acquisition fails visibly rather than silently substituting a different source.
