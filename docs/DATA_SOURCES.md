# Data Sources

This project uses public regulatory, company, and U.S. government datasets. Raw files are downloaded into `raw/` and transformed into governed analytical tables under `processed/` and SQLite.

## 1. SEC CompanyFacts

**Publisher:** U.S. Securities and Exchange Commission  
**Entity:** Delta Air Lines, Inc.  
**CIK:** `0000027904`  
**API endpoint:** https://data.sec.gov/api/xbrl/companyfacts/CIK0000027904.json  
**SEC API documentation:** https://www.sec.gov/search-filings/edgar-application-programming-interfaces

**Use in the model**

- historical GAAP financial facts;
- statement values reported through XBRL;
- period, form, accession number, filing date, taxonomy, and unit lineage;
- source for the core financial actuals table.

The ingestion layer retains filing metadata so reported values remain traceable to the originating SEC filing.

## 2. Delta Air Lines filings

### 2025 Form 10-K

**SEC filing:** https://www.sec.gov/Archives/edgar/data/27904/000002790426000013/0000027904-26-000013-index.htm  
**Period ended:** December 31, 2025  
**Filed:** February 11, 2026

The 10-K provides audited annual financial statements, operating statistics, revenue composition, expenses, cash flow, capital expenditures, fleet information, and management disclosures.

### Q2 2026 Form 10-Q

**SEC filing:** https://www.sec.gov/Archives/edgar/data/27904/000002790426000031/0000027904-26-000031-index.htm  
**Period ended:** June 30, 2026  
**Filed:** July 10, 2026  
**Delta Investor Relations filing page:** https://ir.delta.com/financials/sec-filings/sec-filings-details/default.aspx?FilingId=19602814

The quarterly filing extends the annual financial layer with current-period financial statements and operating disclosures.

### Delta Investor Relations

**SEC filings index:** https://ir.delta.com/financials/sec-filings/default.aspx

This source is used for company-published filing workbooks and related financial materials where available.

## 3. BTS T-100 Domestic Segment

**Publisher:** U.S. Department of Transportation, Bureau of Transportation Statistics  
**Dataset page:** https://www.bts.gov/browse-statistical-products-and-data/bts-publications/data-bank-28ds-t-100-domestic-segment-data  
**TranStats field definitions:** https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=GEE

The segment dataset contains monthly nonstop traffic and capacity records by carrier, origin, destination, aircraft type, and service class.

**Fields used**

- passengers;
- seats;
- distance;
- scheduled departures;
- performed departures;
- freight and mail where applicable;
- aircraft and service-class identifiers.

**Derived measures**

- `ASM = Seats × Distance`
- `RPM = Passengers × Distance`
- `Load Factor = RPM / ASM`
- `Completion Rate = Departures Performed / Departures Scheduled`

## 4. BTS T-100 International Segment

**Publisher:** U.S. Department of Transportation, Bureau of Transportation Statistics  
**Dataset page:** https://www.bts.gov/browse-statistical-products-and-data/bts-publications/%E2%80%A2-data-bank-28is-t-100-and-t-100f  
**TranStats download/table page:** https://www.transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=Nv4+Pn44vr45&gnoyr_VQ=FJE  
**Field definitions:** https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FJE

The international segment table supplies the same core operational measures for international nonstop segments when at least one point of service is in the United States or a U.S. territory.

## 5. BTS Airport Master Coordinate

**Publisher:** U.S. Department of Transportation, Bureau of Transportation Statistics  
**TranStats table:** https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=N8vn6v10&gnoyr_VQ=FLL

This support table is the preferred geographic reference for the 3D network because it includes domestic and foreign airport identifiers with city, country, latitude, and longitude fields.

The airport dimension records coordinate provenance so the application can distinguish BTS-resolved coordinates from fallback sources.

## 6. FAA NASR Airports and Other Landing Facilities

**Publisher:** Federal Aviation Administration  
**NASR cycle:** September 3, 2026  
**Subscription page:** https://www.faa.gov/air_traffic/flight_info/aeronav/Aero_Data/NASR_Subscription/2026-09-03/  
**Direct airport CSV archive:** https://nfdc.faa.gov/webContent/28DaySub/extra/03_Sep_2026_APT_CSV.zip

FAA NASR airport data is used as a U.S. airport coordinate and metadata fallback. The BTS Master Coordinate table remains the preferred global airport reference because the network contains international airports.

## 7. Historical T-100 archives

Historical annual archives for 2019–2025 are enumerated in `scripts/download_t100_history.py`. Each downloaded archive is recorded with:

- dataset scope;
- year;
- public source URL;
- local filename;
- file size;
- SHA-256 checksum;
- acquisition timestamp.

The transformation layer applies release-date precedence to overlapping BTS releases so revised records do not create duplicate route-month observations.

## 8. Planned Form 41 extension

BTS Form 41 schedules are planned for detailed operating-cost and fuel-driver analysis. The relevant public tables include:

- **Schedule P-1.2 — Statement of Operations:** https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=Nv4+Pn44vr4+Sv0n0pvny&gnoyr_VQ=FMI
- **Schedule P-12(a) — Fuel Cost and Consumption:** https://www.transtats.bts.gov/Tables.asp?QO_VQ=EGI
- **Schedule P-5.2 — Aircraft Operating Expenses:** https://www.transtats.bts.gov/TableInfo.asp?QO_fu146_anzr=Nv4+Pn44vr4+Sv0n0pvny&V0s1_b0yB=D&gnoyr_VQ=FMK

These tables will support cost-per-capacity, fuel, maintenance, labor, and margin-driver analysis once period and carrier-scope reconciliation is complete.

## Lineage

`processed/source_manifest.csv` stores source URL, local filename, file size, checksum, role, and pipeline status for the currently loaded source files. Reported financial facts retain their SEC taxonomy and filing identifiers, and derived KPIs are defined in `docs/KPI_DICTIONARY.md`.