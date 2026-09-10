# Raw Data

Large source files are stored locally under `raw/` and excluded from Git history. The acquisition scripts download each dataset from its public publisher endpoint and record SHA-256 checksums for lineage and reproducibility.

## Current acquisition

```bash
python scripts/download_official_sources.py
```

The script retrieves the current SEC CompanyFacts, Delta filing workbooks, BTS T-100 segment archives, and FAA NASR airport data required by the build pipeline.

Historical T-100 archives can be retrieved with:

```bash
python scripts/download_t100_history.py --years 2019 2020 2021 2022 2023 2024 2025
```

## Source documentation

Exact publisher pages, direct endpoints, dataset roles, and field usage are documented in [`docs/DATA_SOURCES.md`](../docs/DATA_SOURCES.md).

## Lineage

`processed/source_manifest.csv` records the currently loaded source files with their public URL, local filename, file size, SHA-256 checksum, analytical role, and pipeline status.