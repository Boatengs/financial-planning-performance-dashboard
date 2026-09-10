# Data Quality Report

## Validation status

**PASS** — the independent validator reconciles CSV totals to SQLite, verifies numeric typing, checks airport-dimension completeness for observed codes, confirms the reporting-carrier filter, and verifies that modeled scenario tables remain unpopulated until the FP&A model is introduced.

## Current validated counts

| Check | Result |
|---|---:|
| SEC financial facts | 315 |
| Derived financial KPI rows | 57 |
| T-100 aircraft-detail rows | 46,666 |
| T-100 route-month rows | 22,332 |
| Directional routes | 5,017 |
| Observed airports | 334 |
| Airport dimension rows | 334 |
| Airports currently geocoded | 223 |
| Airports pending BTS Master Coordinate | 111 |
| Detail rows with passengers greater than seats | 0 |
| Budget / forecast populated rows | 0 |
| Driver-assumption populated rows | 0 |

## Network reconciliation

| Measure | Current loaded data |
|---|---:|
| Passengers | 166,507,545 |
| Seats | 200,719,700 |
| ASM | 280,000,460,693 |
| RPM | 234,982,498,965 |
| Load factor | 83.9222% |
| Departures performed | 1,179,217 |
| Departures scheduled | 1,186,146 |
| Completion rate | 99.4158% |

## Coverage and scope

1. **Historical coverage.** The currently loaded T-100 snapshot spans June 2025 through May 2026. Annual 2019–2025 archive endpoints are enumerated in `scripts/download_t100_history.py` for the historical extension.
2. **Airport coordinates.** FAA NASR currently resolves 223 observed airport codes. The BTS Airport Master Coordinate table is the preferred global coordinate source and will provide broader international coverage.
3. **Carrier scope.** T-100 records are filtered to reporting carrier code `DL`. Delta Connection affiliates and marketed itineraries outside that reporting-carrier scope are not included in the current network layer.
4. **SEC taxonomy coverage.** Some airline-specific taxonomy concepts do not provide usable framed observations for every selected period. Missing observations remain null until a source-compatible filing or Form 41 field is integrated.
5. **Filing workbook normalization.** The Delta 10-K and 10-Q workbooks are retained as filing-level reference inputs. The current model does not normalize every worksheet; fields are added only when their analytical role and lineage are defined.

## Reproducibility evidence

`processed/validation_report.json` contains machine-readable validation checks and output hashes. `processed/reproducibility_report.json` records the two-build byte-for-byte determinism test for deterministic CSV outputs. Source-file SHA-256 hashes and public endpoints are stored in `processed/source_manifest.csv`.