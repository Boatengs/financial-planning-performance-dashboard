# Acquisition Status

## Acquired and used now

- SEC CompanyFacts JSON — Delta Air Lines, Inc. / CIK 27904.
- BTS T-100 Domestic Segment — rolling June 2025 through May 2026.
- BTS T-100 International Segment — rolling June 2025 through May 2026.
- FAA NASR Airport CSV — current uploaded airport package, used as coordinate fallback.

## Acquired and retained for cross-check / next extraction phase

- Delta 2025 10-K XBRL workbook.
- Delta 2026 Q2 10-Q XBRL workbook.

## Prepared but not physically downloaded in this runtime

### Historical T-100 2019-2025

`scripts/download_t100_history.py` contains 14 official bts.gov URLs: domestic and international annual archives for each year 2019-2025. Run it in an internet-enabled environment, then rebuild. The build's release-date precedence handles overlap with the current rolling 12-month files.

### BTS Master Coordinate

Official live table:

`https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=N8vn6v10&gnoyr_VQ=FLL`

This table includes domestic and foreign airport codes, airport/city/country information, latitude and longitude. The local builder automatically detects a Master Coordinate CSV placed under `raw/` and uses it ahead of FAA.

An official USDOT/BTS ROSA P archival ZIP from 2021 is also documented as a fallback source, but the binary could not be pulled into this runtime. It was not replaced with a mirror.

## Deferred official source

BTS Form 41 (P-1.2, P-12(a), P-5.2) is deliberately deferred until the base history/coordinate layer is complete. It will be used for detailed cost/fuel/operating-driver extensions rather than mixed prematurely into the first model.
