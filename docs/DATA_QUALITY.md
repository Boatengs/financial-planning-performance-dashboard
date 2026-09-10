# Data Quality Report

## Build result

**PASS** — the independent validator reconciles CSV totals to SQLite, verifies typed numeric fields, checks airport-dimension completeness for observed codes, confirms every retained T-100 detail row uses reporting carrier code `DL`, and confirms both modeled scenario templates are empty.

## Current validated counts

| Check | Result |
|---|---:|
| SEC financial facts | 315 |
| Safely derived financial KPI rows | 57 |
| T-100 aircraft-detail rows | 46,666 |
| T-100 route-month rows | 22,332 |
| Directional routes | 5,017 |
| Observed airports | 334 |
| Airport dimension rows | 334 |
| Airports currently geocoded | 223 |
| Airports pending BTS Master Coordinate | 111 |
| Detail rows flagged passengers > seats | 0 |
| Budget/Forecast populated rows | 0 |
| Driver-assumption populated rows | 0 |

## Current network reconciliation

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

## Known limitations — intentionally not hidden

1. **History not yet physically acquired in this runtime.** Current T-100 coverage is 2025-06-01 through 2026-05-01. The official 2019-2025 archive URLs are bundled in `download_t100_history.py`, but binary retrieval from BTS failed in this execution environment. No third-party mirror was substituted.
2. **Global coordinate table pending.** FAA resolves 223 observed codes; 111 remain un-geocoded until an official BTS Master Coordinate CSV is ingested. The builder already supports it.
3. **Carrier scope.** `DL` is the reporting-carrier filter. This should be described as DL-reported segment operations, not automatically as all Delta-marketed / Delta Connection flying.
4. **SEC taxonomy gaps.** Some airline-specific CompanyFacts tags have no framed 2019-2026 rows even though the tag exists historically. They remain unavailable rather than being silently replaced.
5. **10-K / 10-Q workbooks retained raw.** They are preserved for filing-level cross-checks and later management-KPI extraction; the current foundation does not claim every worksheet has been normalized yet.

## Reproducibility evidence

See `processed/validation_report.json` for output hashes and machine-readable PASS checks. `processed/reproducibility_report.json` records the two-build byte-for-byte determinism test for deterministic CSV outputs. Source-file SHA-256 hashes are in `processed/source_manifest.csv`.
