# Weeks 4–5 Data Cleaning and Preparation — Final Report

**Reporting date:** October 17, 2026<br>
**Project:** IDX Exchange Data Analyst Internship<br>
**Status:** Weeks 4–5 complete; ready to begin Week 6

## Executive summary

The handbook's Weeks 4–5 cleaning requirements are complete for both enriched Residential datasets. Four date fields and 21 analytical numeric fields are now standardized by a reproducible Python workflow. Completely empty fields and unnecessary row-level contact/address fields were removed from the analysis-ready copies. Date-order, invalid-numeric, and geographic-quality flags were added without silently deleting any records.

The final private outputs retain all 655,943 listing records and all 495,334 sold records across 33 source months. Both files passed independent post-write checks for row counts, Residential-only scope, standardized date formats, required flag columns, flag completeness, and absence of all-null or intentionally removed fields.

No private CSV, row-level MLS output, handbook file, or extraction credential is included in Git.

## Handbook completion checklist

| Requirement | Implementation | Status |
|---|---|---|
| Convert four date fields to datetime | `CloseDate`, `PurchaseContractDate`, `ListingContractDate`, and `ContractStatusChangeDate` parsed and saved as ISO dates | Complete |
| Remove unnecessary or redundant columns | Eight all-null fields and twelve unnecessary contact/address fields removed from analysis-ready copies | Complete |
| Handle missing values appropriately | No unsupported imputation; all-null fields removed, legitimate optional nulls retained, coordinate nulls flagged | Complete |
| Ensure numeric fields are numeric | 21 analytical measures converted and validated; zero coercion failures | Complete |
| Remove or flag invalid numeric values | Five required conditions plus a combined flag added; no records silently deleted | Complete |
| Create date-consistency flags | All three handbook flags added with documented definitions | Complete |
| Create geographic-quality flags | Missing, zero, positive-longitude, implausible, and combined coordinate flags added | Complete |
| Report before/after rows and data types | Included below and printed by the cleaning script | Complete |
| Save analysis-ready CSV and transformation script | Two private CSVs plus `src/weeks4_5_clean.py` | Complete |

## Inputs and outputs

The cleaning workflow uses the mortgage-enriched Weeks 2–3 outputs as inputs, so `year_month` and `rate_30yr_fixed` are preserved.

| Dataset | Input rows | Output rows | Input columns | Output columns | Source months |
|---|---:|---:|---:|---:|---:|
| Listings | 655,943 | 655,943 | 77 | 74 | 33 |
| Sold | 495,334 | 495,334 | 88 | 85 | 33 |

The output column counts reflect 20 removals and 17 new quality flags in each dataset. The private outputs are:

- `data/processed/analysis_ready_listings_residential.csv`
- `data/processed/analysis_ready_sold_residential.csv`

The enriched inputs remain unchanged, providing a recoverable audit trail.

## Missing-value and column-removal decisions

### Completely empty fields removed

The same eight fields were 100% missing in both datasets and provide no analytical information:

- `AboveGradeFinishedArea`
- `BusinessType`
- `CoveredSpaces`
- `ElementarySchoolDistrict`
- `FireplacesTotal`
- `MiddleOrJuniorSchoolDistrict`
- `TaxAnnualAmount`
- `TaxYear`

### Unnecessary row-level fields removed

The following twelve address, agent-name, agent-ID, and contact fields are unnecessary for the handbook's later aggregate market analysis and increase disclosure risk:

- `UnparsedAddress`
- `StreetNumberNumeric`
- `ListAgentEmail`
- `ListAgentFirstName`
- `ListAgentLastName`
- `ListAgentFullName`
- `CoListAgentFirstName`
- `CoListAgentLastName`
- `BuyerAgentMlsId`
- `BuyerAgentFirstName`
- `BuyerAgentLastName`
- `CoBuyerAgentFirstName`

These fields were removed only from the analysis-ready copies. They remain available in the private source files if a future approved business question requires them. Office fields such as `ListOfficeName` and `BuyerOfficeName` were retained because the Week 6 handbook explicitly requests office-level segment analysis.

### Remaining missing values

Optional missing values were retained as missing rather than filled with invented values. For example, a missing `ClosePrice` in the listings dataset may reflect a listing that did not close, while missing coordinates require a quality flag rather than an arbitrary replacement. No mean, median, zero, or text-placeholder imputation was applied.

## Data type confirmation

All four required date fields converted with zero nonblank parse failures:

- `CloseDate`: `datetime64`
- `PurchaseContractDate`: `datetime64`
- `ListingContractDate`: `datetime64`
- `ContractStatusChangeDate`: `datetime64`

Twenty-one analytical fields were passed through numeric conversion and confirmed as numeric, including prices, areas, lot measures, bedroom/bathroom counts, days on market, year built, parking/garage measures, coordinates, and the mortgage rate. There were zero numeric coercion failures in either dataset.

Dates were written to the CSV outputs in `YYYY-MM-DD` format. Independent checks found zero incorrectly formatted non-missing date values.

## Date-consistency flags

The three flags have explicit, non-overlapping interpretations:

- `listing_after_close_flag`: `ListingContractDate > CloseDate`
- `purchase_after_close_flag`: `PurchaseContractDate > CloseDate`
- `negative_timeline_flag`: `PurchaseContractDate < ListingContractDate`

Comparisons are performed only when both relevant dates are present. Missing dates are not automatically labeled chronological violations.

| Flag | Listings | Listings share | Sold | Sold share |
|---|---:|---:|---:|---:|
| `listing_after_close_flag` | 88 | 0.013% | 75 | 0.015% |
| `purchase_after_close_flag` | 264 | 0.040% | 243 | 0.049% |
| `negative_timeline_flag` | 320 | 0.049% | 316 | 0.064% |
| `date_parse_error_flag` | 0 | 0.000% | 0 | 0.000% |
| `missing_required_date_flag` | 0 | 0.000% | 0 | 0.000% |

For listings, the required date is `ListingContractDate`; for sold records, it is `CloseDate`. Every record contains its dataset's required date.

## Invalid numeric flags

The handbook permits invalid values to be removed or flagged. This workflow flags them so the source population remains auditable.

| Flag | Definition | Listings | Sold |
|---|---|---:|---:|
| `invalid_close_price_flag` | Non-missing `ClosePrice <= 0` | 0 | 1 |
| `invalid_living_area_flag` | Non-missing `LivingArea <= 0` | 426 | 177 |
| `invalid_days_on_market_flag` | `DaysOnMarket < 0` | 33 | 56 |
| `negative_bedrooms_flag` | `BedroomsTotal < 0` | 0 | 0 |
| `negative_bathrooms_flag` | `BathroomsTotalInteger < 0` | 0 | 0 |
| `invalid_numeric_flag` | Any required numeric condition above | 459 (0.070%) | 234 (0.047%) |
| `numeric_parse_error_flag` | Nonblank value failed numeric conversion | 0 | 0 |

Missing values are not treated as nonpositive values. For example, an absent listings-side `ClosePrice` does not trigger `invalid_close_price_flag`.

## Geographic data-quality summary

| Flag | Listings | Listings share | Sold | Sold share |
|---|---:|---:|---:|---:|
| `missing_coordinates_flag` | 81,364 | 12.404% | 4,797 | 0.968% |
| `zero_coordinates_flag` | 90 | 0.014% | 46 | 0.009% |
| `positive_longitude_flag` | 95 | 0.014% | 35 | 0.007% |
| `implausible_coordinates_flag` | 361 | 0.055% | 115 | 0.023% |
| `invalid_coordinates_flag` | 81,725 | 12.459% | 4,912 | 0.992% |

`implausible_coordinates_flag` uses a deliberately broad California screening rectangle: latitude 32.0–42.5 and longitude -125.0–-113.0. It is a review flag, not proof that a coordinate lies outside California. A precise state or school-district determination requires the spatial-boundary join planned in Week 6.

Missing coordinates are the dominant geographic issue, especially in listings. Flag categories can overlap, so their individual counts should not be added together; `invalid_coordinates_flag` is the combined row-level indicator.

## Decisions and limitations

1. Invalid numeric, date, and coordinate records remain in the outputs with boolean flags. Week 6 metrics can apply the relevant flags transparently rather than relying on an undocumented deletion.
2. Optional missing values were not imputed because the handbook and metadata do not provide defensible replacement rules.
3. Original private source and enriched files remain unchanged, so every transformation is reversible.
4. Repeated listing identifiers were not deduplicated because the correct grain—record, listing, property, or transaction—depends on the metric. Week 6 summaries must state their counting unit.
5. The coordinate screen is rectangular and intentionally conservative. It does not replace a polygon-based geographic validation.
6. Cleaned CSVs do not preserve pandas data types by themselves. The script is the reproducible type specification, and downstream reads should parse the four date fields or reuse the cleaning functions.

## Independent saved-output validation

After writing, both CSVs were read back and checked independently:

- Exact expected row counts and 33 source months
- Zero non-Residential records
- Zero all-null columns
- Zero intentionally removed fields
- All 17 flag columns present with zero missing flag values
- Zero malformed saved date strings

File sizes are approximately 313.9 MB for listings and 283.0 MB for sold. Both remain excluded from Git.

## Reproducible artifacts

- `src/weeks4_5_clean.py` — complete transformation and validation workflow
- `notebooks/04_05_cleaning_preparation.ipynb` — aggregate analytical narrative and review tables
- `reports/weeks4_5_cleaning_report.md` — supervisor-facing summary
- `docs/project_log.md` — chronological project record

## Next phase

Week 6 will create the handbook's market features: close-to-original-list ratio, price per square foot, year/month variables, listing-to-contract days, and contract-to-close days. Those metrics should use the Weeks 4–5 flags to document which records are eligible for each calculation.
