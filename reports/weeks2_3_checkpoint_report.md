# Weeks 2–3 Data Validation Checkpoint

> Historical checkpoint: this report records the halfway state through August 2026. It has been superseded by [`weeks2_3_final_report.md`](weeks2_3_final_report.md), which includes September 2026, completed EDA, and mortgage-rate enrichment.

**Reporting date:** October 10, 2026<br>
**Project:** IDX Exchange Data Analyst Internship<br>
**Status:** Week 1 complete; Weeks 2–3 approximately halfway complete

## Executive summary

The monthly CRMLS listing and sold extracts have been combined into two Residential-only analysis datasets. The first half of the Weeks 2–3 validation work is complete: file availability, row counts, month coverage, schema integrity, missingness, and selected numeric distributions have been checked.

The datasets passed the structural checks, but the exploratory analysis identified substantial missingness in several optional fields and extreme or implausible values in price, area, acreage, bedroom, bathroom, DaysOnMarket, and YearBuilt fields. No records or columns have been deleted. These results define the questions and validation rules needed before producing final market metrics.

## Work completed

- Repaired and regenerated the damaged January 2026 listing extract.
- Combined monthly listing and sold files covering January 2024 through August 2026.
- Filtered both combined datasets to `PropertyType == "Residential"`.
- Preserved source-month tracking and historically filled coordinate fields.
- Validated expected row counts, 32-month coverage, Residential-only scope, and absence of duplicate processed-data column names.
- Profiled missing values across every column.
- Calculated descriptive statistics for nine important numeric fields.
- Confirmed that all non-missing values in the selected numeric fields convert successfully to numeric values.
- Kept all reporting aggregate-only; no confidential row-level MLS data appears in this report.

## Dataset coverage

| Dataset | Combined input rows | Residential rows | Columns | Source months | Non-Residential rows |
|---|---:|---:|---:|---:|---:|
| Listings | 996,267 | 633,662 | 75 | 32 | 0 |
| Sold | 714,370 | 480,486 | 86 | 32 | 0 |

The processed files cover January 2024 through August 2026. Row counts currently represent records in the combined extracts. They should not yet be described as counts of unique properties or unique transactions until listing-identifier duplication is analyzed.

## Preliminary market snapshot

| Measure | Listings | Sold |
|---|---:|---:|
| Median relevant price | ListPrice: $840,000 | ClosePrice: $825,000 |
| Median LivingArea | 1,670 sq. ft. | 1,647 sq. ft. |
| Median DaysOnMarket | 11 days | 19 days |
| Mean DaysOnMarket | 20.75 days | 37.51 days |

These are record-level descriptive statistics, not final market KPIs. Differences in population, repeated identifiers, missing values, and outliers must be evaluated before drawing conclusions about market trends or list-to-sale performance.

## Key discoveries

### 1. Structural quality is strong

- Both processed datasets contain all 32 expected source months.
- Both contain only Residential records.
- The processed headers have no duplicate column names.
- Selected numeric fields produced zero conversion failures.

This means the Week 1 aggregation created structurally usable analysis inputs.

### 2. Missingness is concentrated in specific fields

- Listings: 63 of 75 columns have at least one missing value; 13 are more than 90% missing.
- Sold: 74 of 86 columns have at least one missing value; 15 are more than 90% missing.
- Eight fields are completely empty in both datasets: `TaxAnnualAmount`, `AboveGradeFinishedArea`, `FireplacesTotal`, `TaxYear`, `ElementarySchoolDistrict`, `BusinessType`, `CoveredSpaces`, and `MiddleOrJuniorSchoolDistrict`.
- Other highly sparse fields include `BelowGradeFinishedArea`, `BuilderName`, `LotSizeDimensions`, `BuildingAreaTotal`, and `CoBuyerAgentFirstName`.
- `WaterfrontYN` and `BasementYN` are especially sparse in the sold data.

Interpretation: these columns are candidates for exclusion from some analyses, but they should not be deleted automatically. Missingness may reflect optional MLS entry practices rather than invalid records.

### 3. ClosePrice behaves differently across the two datasets

- Listings ClosePrice is 70.74% missing, which is broadly consistent with records that have not become closed sales.
- Sold ClosePrice is present for all but two records.

Interpretation: the two datasets serve different analytical purposes. Listings are useful for supply and asking-price analysis; sold records are the stronger source for completed transaction analysis. The two missing sold ClosePrice records require a later aggregate-safe investigation.

### 4. Numeric extremes require explicit business rules

| Field | Listings observed range | Sold observed range | Validation concern |
|---|---:|---:|---|
| DaysOnMarket | -75 to 1,155 | -288 to 12,430 | Negative and extremely large durations |
| ListPrice | $0 to $400 million | $1 to $170 million | Zero or extreme price values |
| ClosePrice | $360 to $820 million | $0 to $989.5 million | Zero or extreme transaction values |
| LivingArea | 0 to 17,021,321 sq. ft. | 0 to 17,021,321 sq. ft. | Zero and implausibly large areas |
| BedroomsTotal | 0 to 94 | 0 to 45 | Possible data-entry or property-type issues |
| BathroomsTotalInteger | 0 to 2,208 | 0 to 175 | Likely unit or data-entry issues at the extreme |
| YearBuilt | 1776 to 2028 | 1776 to 2027 | Future construction years require interpretation |

Interpretation: medians and percentiles are safer than means for the initial description because extreme values strongly affect averages. Suspicious values will be flagged first; they will not be silently removed.

## Decisions made so far

- Do not delete high-missingness columns solely because they are sparse.
- Do not delete extreme records until defensible domain rules are documented.
- Use sold data for completed-sale metrics and listings data for listing-side metrics.
- Treat current statistics as preliminary until repeated listing identifiers and date consistency are checked.
- Keep private CSV files, handbooks, and extraction scripts out of GitHub.

## Questions for the supervisor

1. Should the primary analytical unit be a monthly record, a unique listing, a property, or a completed transaction?
2. Which identifier should be used to detect repeat listings or repeated monthly records?
3. Are negative DaysOnMarket values expected under any CRMLS workflow, or should they always be flagged as invalid?
4. Should future YearBuilt values represent planned/new construction, or should they be excluded from general resale analysis?
5. Which sparse fields are important enough to preserve for later business questions?
6. Which geographic level should drive the first market summaries: county, city, ZIP code, or another MLS area?
7. For mortgage-rate enrichment, should we use the FRED 30-year fixed mortgage series, and should weekly observations be converted to monthly means or month-end values?

## Next work

1. Analyze repeated listing identifiers and confirm the correct unit of analysis.
2. Review property categories and geographic coverage using aggregate counts.
3. Validate listing, pending, and closing date relationships.
4. Create safe distributions and time-series visuals using validated records or clearly labeled flags.
5. Save reusable aggregate missingness and numeric-quality reports.
6. Obtain the approved FRED mortgage-rate series and convert it to the project month key.
7. Merge mortgage rates, validate the join, and document the enriched dataset.

## Suggested meeting talk track

> I completed the monthly aggregation and the first half of data validation. We now have two Residential-only datasets covering 32 months: 633,662 listing records and 480,486 sold records. Structurally, the datasets passed our checks. The main discoveries are concentrated missingness in optional MLS fields and several numeric extremes, including negative DaysOnMarket and implausibly large price or property values. I have not removed these records because I want the cleaning rules to reflect the intended business use. My next priority is confirming whether our unit of analysis should be a monthly record, unique listing, property, or sale, then validating dates and creating market visuals. I would like guidance on the identifier, geography, and mortgage-rate aggregation choices.

## Reproducibility references

- Active analysis notebook: `notebooks/02_03_data_validation_eda.ipynb`
- Validation code: `src/weeks2_3_validate.py`
- Aggregation code: `src/week1_aggregate.py`
- Detailed chronological notes: `docs/project_log.md`
- Latest checkpoint commit: `7cc3d8b`
