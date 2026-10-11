# Weeks 2–3 Data Validation and Mortgage Enrichment — Final Report

**Reporting date:** October 10, 2026<br>
**Project:** IDX Exchange Data Analyst Internship<br>
**Status:** Weeks 2–3 complete; ready to begin Weeks 4–5

## Executive summary

The Weeks 2–3 handbook requirements are complete. The CRMLS listing and sold datasets now cover January 2024 through September 2026, the most recently completed calendar month. Both datasets were filtered to Residential records, structurally validated, profiled for missingness and numeric behavior, checked for preliminary date issues and repeated identifiers, and enriched with monthly average 30-year mortgage rates from FRED.

The final private analysis datasets contain 655,943 listing records and 495,334 sold records across 33 source months. The mortgage-rate joins preserved every row and produced zero missing rates. The analysis also established the central data-quality questions for Weeks 4–5: how to flag implausible numeric values, how to handle repeated listing identifiers, how to formalize date rules, and which sparse fields should be excluded from specific analyses without deleting them from the source data.

No raw MLS records, CSV files, credentials, or private handbook files are included in Git. All figures in this report are aggregate-level results.

## Handbook completion checklist

| Requirement | Evidence | Status |
|---|---|---|
| Combine all monthly listing and sold extracts through the latest completed month | `src/week1_aggregate.py`; 33 months from 202401–202609 | Complete |
| Filter to `PropertyType == "Residential"` and record before/after counts | Aggregation audit and property-type summaries | Complete |
| Validate dimensions, data types, missingness, and field roles | `src/weeks2_3_validate.py` and EDA notebook | Complete |
| Report fields above 90% missing and make retain/exclude recommendations | Missingness report with explicit recommendations | Complete |
| Analyze all nine specified numeric fields | Percentile tables, full-range checks, histograms, and boxplots | Complete |
| Investigate property categories, dates, price outcomes, and counties | Aggregate EDA sections and final report | Complete |
| Obtain FRED `MORTGAGE30US`, calculate monthly averages, and left-join | `src/weeks2_3_mortgage.py` and mortgage notebook | Complete |
| Validate mortgage joins with unchanged row counts and zero null rates | Independent post-write validation | Complete |
| Save enriched private CSV outputs | `data/processed/` outputs, excluded from Git | Complete |

## Final dataset coverage

| Dataset | Combined input rows | Residential rows | Columns before mortgage join | Source months | Non-Residential rows |
|---|---:|---:|---:|---:|---:|
| Listings | 1,031,314 | 655,943 | 75 | 33 | 0 |
| Sold | 736,548 | 495,334 | 86 | 33 | 0 |

Coverage is complete from January 2024 through September 2026. These are record counts, not yet counts of unique properties or transactions; repeated listing identifiers are discussed below.

## Residential filtering audit

Before filtering, Residential was the largest property type in both datasets but not the only one.

| Property type | Listings rows | Listings share | Sold rows | Sold share |
|---|---:|---:|---:|---:|
| Residential | 655,943 | 63.60% | 495,334 | 67.25% |
| ResidentialLease | 214,277 | 20.78% | 169,471 | 23.01% |
| Land | 66,848 | 6.48% | 23,310 | 3.16% |
| ResidentialIncome | 38,287 | 3.71% | 19,797 | 2.69% |
| ManufacturedInPark | 29,386 | 2.85% | 19,771 | 2.68% |
| CommercialSale | 14,153 | 1.37% | 4,557 | 0.62% |
| CommercialLease | 9,207 | 0.89% | 3,833 | 0.52% |
| BusinessOpportunity | 3,213 | 0.31% | 475 | 0.06% |

The handbook's Residential-only filter therefore materially changes the analytical population. ResidentialLease and the other property types are intentionally out of scope, not missing by accident.

## Structure and field roles

The processed datasets passed checks for expected row counts, complete month coverage, Residential-only scope, required columns, unique processed headers, and numeric conversion. Listings contain 75 columns; sold contains 86. The raw files exhibit schema evolution, but the aggregation logic harmonizes those schema groups while retaining source-month lineage.

Fields were reviewed against their analytical roles:

- Market measures: prices, living area, lot size, bedrooms, bathrooms, days on market, and year built.
- Dates: listing contract, purchase contract, and close dates.
- Geography: county and other location fields. Confidential row-level location values are never reported.
- Identifiers: listing keys and IDs used to assess repetition, not displayed as raw values.
- Metadata/operational fields: source month and fields needed for lineage or validation.

The Trestle metadata definitions were reviewed for the core fields. In particular, `ListingContractDate` represents the listing agreement date, `PurchaseContractDate` the accepted-offer date, and `CloseDate` the completed agreement date. Those definitions inform the preliminary chronological checks and the formal rules to be developed in Weeks 4–5.

## Missing-value findings and decisions

| Dataset | Columns with any missing values | Columns above 90% missing | Total columns |
|---|---:|---:|---:|
| Listings | 63 | 13 | 75 |
| Sold | 74 | 15 | 86 |

Eight fields are completely empty in both datasets: `TaxAnnualAmount`, `AboveGradeFinishedArea`, `FireplacesTotal`, `TaxYear`, `ElementarySchoolDistrict`, `BusinessType`, `CoveredSpaces`, and `MiddleOrJuniorSchoolDistrict`.

Other fields above 90% missing include `BelowGradeFinishedArea`, `BuilderName`, `LotSizeDimensions`, `BuildingAreaTotal`, and `CoBuyerAgentFirstName`. In sold data, `WaterfrontYN` and `BasementYN` are also especially sparse.

The working decision is:

- Preserve all source columns in the private master datasets.
- Exclude 100%-missing fields from current analyses because they provide no information.
- Treat fields above 90% missing as analysis-specific and exclude them by default unless a business question requires them.
- Retain core market fields despite partial missingness and report the valid denominator for every metric.
- Do not impute values until the Weeks 4–5 business rules identify a defensible method.

`ClosePrice` is missing for 71.54% of listing records, which is expected because the listing file contains records that may not be closed. Sold data is the authoritative source for completed-sale analysis.

## Numeric distributions and extreme values

All nine handbook-specified fields were analyzed in both datasets: `ClosePrice`, `ListPrice`, `OriginalListPrice`, `LivingArea`, `LotSizeAcres`, `BedroomsTotal`, `BathroomsTotalInteger`, `DaysOnMarket`, and `YearBuilt`. Every non-missing value in these fields converted successfully to numeric form.

| Measure | Listings | Sold |
|---|---:|---:|
| Median ListPrice | $840,000 | — |
| Median ClosePrice | $850,000 among non-missing listing values | $825,000 |
| Median LivingArea | 1,671 sq. ft. | 1,648 sq. ft. |
| Median DaysOnMarket | 11 days | 19 days |
| Mean DaysOnMarket | 20.48 days | 37.64 days |

The distributions are strongly skewed. Full-range validation identified negative days on market, zero prices or living areas, implausibly large price/area/acreage values, unusually high bedroom and bathroom counts, and future year-built values. The notebooks show both percentile summaries and capped visualizations so the central distribution is visible without hiding the full observed extremes.

These records are not automatically deleted. Weeks 4–5 will translate the observations into transparent flags and exclusion rules, preserving the original values for auditability. Medians and percentiles remain preferable to means for initial market descriptions.

## Property subtypes

Single-family residences dominate both Residential datasets, followed by condominiums and townhouses.

| Property subtype | Listings rows | Listings share | Sold rows | Sold share |
|---|---:|---:|---:|---:|
| SingleFamilyResidence | 478,767 | 72.99% | 371,242 | 74.95% |
| Condominium | 117,922 | 17.98% | 81,160 | 16.38% |
| Townhouse | 38,496 | 5.87% | 29,035 | 5.86% |

This composition matters because price, living area, and days-on-market comparisons may need to be segmented by subtype rather than interpreted as one uniform market.

## Repeated identifiers

Repeated identifiers exist but affect a small fraction of records:

| Dataset | Repeated `ListingKey` values | Records using repeated keys | Repeated `ListingId` values | Records using repeated IDs |
|---|---:|---:|---:|---:|
| Listings | 199 | 400 | 222 | 446 |
| Sold | 376 | 756 | 378 | 760 |

No row-level identifiers were printed. A repeated key is not automatically an error; it may reflect source updates, relisting behavior, or cross-month extraction semantics. Weeks 4–5 should determine whether final metrics use record-level observations, latest snapshots, or deduplicated transaction definitions.

## Preliminary date consistency

The Weeks 2–3 checks identify candidate chronology violations; they are not yet final invalid-record labels.

| Check | Listings | Sold |
|---|---:|---:|
| Listing date after purchase-contract date | 320 of 325,710 (0.10%) | 316 of 495,136 (0.06%) |
| Purchase-contract date after close date | 264 of 210,168 (0.13%) | 243 of 495,137 (0.05%) |
| Listing date after close date | 88 of 210,199 (0.04%) | 75 of 495,333 (0.02%) |

The rates are low but nonzero. Weeks 4–5 will formalize date parsing, acceptable exceptions, and reusable flag columns based on the metadata definitions and supervisor guidance.

## Sold-market questions

Among sold records with valid positive current list prices:

| Sale outcome | Records | Share |
|---|---:|---:|
| Above current list price | 196,249 | 39.62% |
| At current list price | 86,408 | 17.44% |
| Below current list price | 212,674 | 42.94% |

This is a record-level comparison with the current `ListPrice`, not necessarily the original asking price. Later market metrics should state explicitly whether they compare `ClosePrice` with `ListPrice` or `OriginalListPrice`.

For counties with at least 100 sold records, the highest observed median close prices were San Mateo ($1.70M), Santa Clara ($1.59M), San Francisco ($1.20M), Santa Cruz ($1.1885M), Orange ($1.185M), Marin ($1.17M), Alameda ($1.13M), Monterey ($910K), Los Angeles ($905K), and San Diego ($900K). These are unadjusted descriptive medians, not causal comparisons; property mix and time period differ by county.

## Mortgage-rate enrichment

The public FRED series `MORTGAGE30US` was downloaded and converted from weekly observations to calendar-month averages. Listings were joined by the month of `ListingContractDate`; sold records were joined by the month of `CloseDate`. Both joins were many-to-one left joins so the original MLS population was preserved.

| Validation | Listings | Sold |
|---|---:|---:|
| Rows before join | 655,943 | 495,334 |
| Rows after join | 655,943 | 495,334 |
| Months represented | 33 | 33 |
| Missing mortgage rates | 0 | 0 |
| Maximum distinct monthly rates per month key | 1 | 1 |
| Enriched columns | 77 | 88 |

The 33 required monthly averages ranged from 6.048% to 7.060%. The enriched private files were saved as:

- `data/processed/combined_listings_residential_with_mortgage_rates.csv`
- `data/processed/combined_sold_residential_with_mortgage_rates.csv`

These files are ignored by Git. The join establishes a descriptive macroeconomic feature; it does not by itself demonstrate that mortgage rates caused changes in prices or market activity.

## Decisions entering Weeks 4–5

1. Keep original values and create explicit quality flags rather than silently overwriting suspicious data.
2. Define valid ranges and exception handling for prices, area, acreage, bedrooms, bathrooms, days on market, and year built.
3. Formalize date-order rules using the Trestle definitions and preserve the denominator used for each violation rate.
4. Decide the correct analytical grain for repeated listing identifiers before calculating inventory or transaction counts.
5. Use sold records for closed-sale metrics and listings for supply/asking-price questions unless a metric explicitly needs both.
6. Confirm with the supervisor whether public Tableau work may use only aggregates or requires an additional de-identification/export policy.

## Reproducible project artifacts

- `src/week1_aggregate.py` — coverage, schema, duplicate-header, property-type, and aggregation validation.
- `src/weeks2_3_validate.py` — structural validation, missingness, numeric summaries, categories, identifiers, dates, and market questions.
- `src/weeks2_3_mortgage.py` — FRED monthly-rate preparation, joins, validation, and private outputs.
- `notebooks/01_monthly_aggregation.ipynb` — Week 1 analytical narrative.
- `notebooks/02_03_data_validation_eda.ipynb` — Weeks 2–3 validation, charts, findings, and decisions.
- `notebooks/02_03_mortgage_enrichment.ipynb` — mortgage methodology and independent validation.
- `docs/project_log.md` — chronological work record.

## Next phase

Weeks 4–5 should begin with a written cleaning specification, followed by reusable flag columns, quantified impacts of each rule, and a comparison of raw versus analysis-ready populations. No deletion or deduplication rule should be applied until its business meaning and effect on the data are documented.
