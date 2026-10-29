# Data Sources

This project uses public regulatory, company, and U.S. government datasets. Raw source files are written to `raw/`, while governed analytical outputs and source-lineage artifacts are generated under `processed/`.

## 1. SEC CompanyFacts

**Publisher:** U.S. Securities and Exchange Commission  
**Entity:** Delta Air Lines, Inc.  
**CIK:** `0000027904`  
**API endpoint:** https://data.sec.gov/api/xbrl/companyfacts/CIK0000027904.json  
**SEC API documentation:** https://www.sec.gov/search-filings/edgar-application-programming-interfaces

**Model use:** consolidated quarterly and annual revenue, operating expense, operating and net income,
fuel, labor, maintenance, depreciation, operating cash flow, capital expenditures, cash, debt, assets and
equity for `fact_financial_actual`.

**How periods are built.** CompanyFacts assigns a calendar frame to only one fact per period and SEC does
not publish standalone fourth quarters or standalone quarterly cash flows. The pipeline therefore reads
each fact's reported start and end dates rather than its frame:

| Method | Rule |
|---|---|
| `reported` | A three-month (or full-year, or balance-sheet) value as filed |
| `derived_fy_minus_9m` | Q4 = full year minus the nine-month year-to-date value |
| `derived_ytd_difference` | Q2 and Q3 cash flow = year-to-date minus the prior year-to-date value |
| `derived_sum_of_components` | Total capex = flight equipment + ground property, equipment and technology (Delta stopped tagging the total in 2026) |

The most recently filed value wins when a period is restated.

**Pinned snapshot.** SEC refuses requests from some cloud networks, including GitHub-hosted runners. When a
fresh download is not possible the build uses the newest snapshot under `raw/sec/`, filtered to the
concepts above by `scripts/subset_companyfacts.py`. The QA summary records which source a build used.

## 2. Delta Air Lines filings

The filings behind CompanyFacts are listed on Delta's investor relations site
(https://ir.delta.com/financials/sec-filings/default.aspx) and on EDGAR. The pipeline does not parse filing
documents directly. Earlier versions downloaded two XBRL workbooks that were never used; they were removed.

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
**TranStats table:** 288, https://transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FLL&QO_fu146_anzr=N8vn6v10

Downloaded by `scripts/download_bts_tables.py --tables master_coordinate` to `raw/bts/master_coordinate.zip`.
It is the primary coordinate source for every observed airport, domestic and foreign. Only rows flagged
`AIRPORT_IS_LATEST` are used.

## 7. FAA NASR Airports and Other Landing Facilities

**Publisher:** Federal Aviation Administration  
**NASR cycle:** September 3, 2026  
**Subscription page:** https://www.faa.gov/air_traffic/flight_info/aeronav/Aero_Data/NASR_Subscription/2026-09-03/  
**Direct airport CSV archive:** https://nfdc.faa.gov/webContent/28DaySub/extra/03_Sep_2026_APT_CSV.zip

FAA NASR airport data is a U.S. fallback used only where Master Coordinate has no latitude and longitude, and for airport elevation. The build continues without it if the FAA cycle file is no longer published.

## 8. BTS Form 41 financial schedules

**Publisher:** U.S. Department of Transportation, Bureau of Transportation Statistics, Air Carrier Financial Reports

| Schedule | TranStats table | Form | Use |
|---|---|---|---|
| P-1.2 Statement of Operations (quarterly, by region, $000) | 295 | https://transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FMI&QO_fu146_anzr=Nv4%20Pn44vr4%20Sv0n0pvny | Passenger revenue, operating revenue and expense, transport-related lines |
| P-12(a) Fuel Cost and Consumption (monthly) | 294 | https://transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FMH&QO_fu146_anzr=Nv4%20Pn44vr4%20Sv0n0pvny | Scheduled-service fuel gallons and cost, domestic and international |

Both are downloaded one calendar year per request by `scripts/download_bts_tables.py` and filtered to
unique carrier `DL`. P-1.2 regions are mapped to T-100 scope: Domestic to `domestic`; Atlantic, Pacific
and Latin America to `international`. Any unmapped region fails validation.

Form 41 covers the same DOT reporting entity as T-100, so revenue and cost per ASM use matching scope.
These measures are not Delta's investor-relations TRASM and CASM, which are consolidated, include regional
capacity purchase flying and exclude special items.

## Lineage

`data/published/source_manifest.csv` records source URL, local filename, file size, checksum, analytical role, and pipeline status for every input to a build. `raw/t100_history_download_manifest.csv` and `raw/bts_download_manifest.csv` record every TranStats request. Reported financial facts retain SEC taxonomy and filing identifiers, while derived KPI definitions are maintained in `docs/KPI_DICTIONARY.md`.
