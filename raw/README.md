# Raw Data

Large publisher source files are stored locally under `raw/` and excluded from Git history. Acquisition scripts record source URLs, file sizes, SHA-256 checksums, and timestamps for reproducibility.

## Combined current foundation

```bash
python scripts/download_official_sources.py
python scripts/download_t100_history.py --years 2025 2026
```

The fixed-source downloader retrieves SEC CompanyFacts, Delta filing workbooks, and FAA NASR airport reference data. T-100 segment data is acquired separately from the official BTS TranStats annual download forms.

## Historical operating series

```bash
python scripts/download_official_sources.py --group network
python scripts/download_t100_history.py --years 2019 2020 2021 2022 2023 2024 2025 2026
```

T-100 extracts are written as dated snapshots beneath:

```text
raw/t100/domestic/
raw/t100/international/
```

`raw/t100_history_download_manifest.csv` records the scope, year, TranStats table ID, exact public form URL, snapshot filename, file size, SHA-256 checksum, status, and acquisition timestamp.

## Source documentation

Exact publisher pages, acquisition endpoints, dataset roles, and field usage are documented in [`docs/DATA_SOURCES.md`](../docs/DATA_SOURCES.md).

## Generated lineage

`processed/source_manifest.csv` records source lineage for the combined analytical foundation. `processed/network_source_manifest.csv` records the corresponding lineage for the independently built historical network model.
