# Data Sources

This project uses public regulatory, company, and U.S. government datasets. Raw source files are written to `raw/`, while governed analytical outputs and source-lineage artifacts are generated under `processed/`.

## 1. SEC CompanyFacts

**Publisher:** U.S. Securities and Exchange Commission  
**Entity:** Delta Air Lines, Inc.  
**CIK:** `0000027904`  
**API endpoint:** https://data.sec.gov/api/xbrl/companyfacts/CIK0000027904.json  
**SEC API documentation:** https://www.sec.gov/search-filings/edgar-application-programming-interfaces

**Model use**

- historical GAAP financial facts;
- reported statement values from XBRL;
- filing date, form, accession number, taxonomy, frame, and unit lineage;
- source for `fact_financial_actual`.

## 2. Delta Air Lines filings

### 2025 Form 10-K

**SEC filing:** https://www.sec.gov/Archives/edgar/data/27904/000002790426000013/0000027904-26-000013-index.htm  
**Period ended:** December 31, 2025  
**Filed:** February 11, 2026

The annual filing provides audited financial statements, operating statistics, revenue composition, expenses, cash flow, capital expenditures, fleet information, and management disclosures.

### Q2 2026 Form 10-Q

**SEC filing:** https://www.sec.gov/Archives/edgar/data/27904/000002790426000031/0000027904-26-000031-index.htm  
**Period ended:** June 30, 2026  
**Filed:** July 10, 2026  
**Delta Investor Relations filing page:** https://ir.delta.com/financials/sec-filings/sec-filings-details/default.aspx?FilingId=19602814

The quarterly filing extends the financial layer with current-period statements and operating disclosures.

### Delta Investor Relations

**SEC filings index:** https://ir.delta.com/financials/sec-filings/default.aspx

Company-published filing workbooks are retained as filing-level cross-check sources where available.

## 3. BTS T-100 Domestic Segment

**Publisher:** U.S. Department of Transportation, Bureau of Transportation Statistics  
**System:** BTS TranStats  
**Table ID:** `259`  
**Annual extract form:** https://transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FIM&QO_fu146_anzr=Nv4%20Pn44vr45  
**Field definitions:** https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FIM

The pipeline requests one calendar year per TranStats download and selects the segment fields needed for the analytical model. The parser then restricts records to reporting carrier code `DL`.

**Fields used**

- year and month;
- unique carrier and carrier entity;
- origin and destination airport identifiers;
- origin and destination city/WAC fields;
- aircraft group, type, and configuration;
- service class;
- distance;
- scheduled and performed departures;
- payload, seats, and passengers;
- freight and mail;
- ramp-to-ramp and airborne time.

## 4. BTS T-100 International Segment

**Publisher:** U.S. Department of Transportation, Bureau of Transportation Statistics  
**System:** BTS TranStats  
**Table ID:** `261`  
**Annual extract form:** https://transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FJE&QO_fu146_anzr=Nv4%20Pn44vr45  
**Field definitions:** https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FJE

The international segment table supplies the same core operating measures for international nonstop segments. The ingestion path normalizes domestic and international extracts into one canonical T-100 schema while retaining `scope` as part of the record grain.

## 5. T-100 acquisition and lineage

`scripts/download_t100_history.py` acquires annual domestic and international segment extracts for 2019–2026 directly from the two TranStats forms above. Each extract is stored as a dated snapshot under `raw/t100/{scope}/` and the acquisition manifest records:

- domestic or international scope;
- calendar year;
- TranStats table ID;
- exact public form URL;
- local snapshot filename;
- file size;
- SHA-256 checksum;
- acquisition timestamp;
- acquisition status.

The generated TranStats CSV is normalized into the same canonical fields used by the route and network KPI layers. Source snapshot dates provide deterministic precedence if overlapping extracts are present.

**Derived operating measures**

- `ASM = Seats × Distance`
- `RPM = Passengers × Distance`
- `Load Factor = RPM / ASM`
- `Completion Rate = Departures Performed / Departures Scheduled`
- `Passengers per Departure = Passengers / Departures Performed`

## 6. BTS Airport Master Coordinate

**Publisher:** U.S. Department of Transportation, Bureau of Transportation Statistics  
**TranStats table:** https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=N8vn6v10&gnoyr_VQ=FLL

This support table is the preferred geographic reference for the 3D network because it includes domestic and foreign airport identifiers with city, country, latitude, and longitude fields.

The airport dimension records coordinate provenance so the application can distinguish BTS-resolved coordinates from fallback sources.

## 7. FAA NASR Airports and Other Landing Facilities

**Publisher:** Federal Aviation Administration  
**NASR cycle:** September 3, 2026  
**Subscription page:** https://www.faa.gov/air_traffic/flight_info/aeronav/Aero_Data/NASR_Subscription/2026-09-03/  
**Direct airport CSV archive:** https://nfdc.faa.gov/webContent/28DaySub/extra/03_Sep_2026_APT_CSV.zip

FAA NASR airport data is used as a U.S. airport coordinate and metadata fallback. BTS Airport Master Coordinate remains the preferred global reference for international coverage.

## 8. Planned Form 41 extension

BTS Form 41 schedules are planned for detailed operating-cost and fuel-driver analysis. Relevant public tables include:

- **Schedule P-1.2 — Statement of Operations:** https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=Nv4+Pn44vr4+Sv0n0pvny&gnoyr_VQ=FMI
- **Schedule P-12(a) — Fuel Cost and Consumption:** https://www.transtats.bts.gov/Tables.asp?QO_VQ=EGI
- **Schedule P-5.2 — Aircraft Operating Expenses:** https://www.transtats.bts.gov/TableInfo.asp?QO_fu146_anzr=Nv4+Pn44vr4+Sv0n0pvny&V0s1_b0yB=D&gnoyr_VQ=FMK

These tables will support cost-per-capacity, fuel, maintenance, labor, and margin-driver analysis after period and carrier-scope reconciliation.

## Lineage

`processed/source_manifest.csv` records source URL, local filename, file size, checksum, analytical role, and pipeline status for the combined foundation. `processed/network_source_manifest.csv` provides the equivalent source audit for the historical operating model. Reported financial facts retain SEC taxonomy and filing identifiers, while derived KPI definitions are maintained in `docs/KPI_DICTIONARY.md`.
