# Week 6 Feature Engineering and Market Metrics — Final Report

**Reporting date:** October 31, 2026<br>
**Project:** IDX Exchange Data Analyst Internship<br>
**Status:** Week 6 complete; ready to begin Week 7

## Executive summary

The Week 6 deliverable requirements are complete for the analysis-ready Residential sold dataset. Six market-metric groups were implemented and independently validated: close-to-original-list ratio, close price per square foot (PPSF), Days on Market, close-date time fields, listing-to-contract days, and contract-to-close days. California 2024–25 school-district boundaries were joined by property coordinates, and the market metrics were summarized by PropertySubType, CountyOrParish, and MLSAreaMajor.

The private Week 6 dataset preserves all 495,334 sold records covering January 2024 through September 2026. It contains 97 columns: 85 input columns, six engineered metric columns, and six school-district fields. Invalid or ineligible inputs remain preserved; metric values are left missing when their business rules are not satisfied.

The statewide median close-to-original-list ratio was 0.9944, median PPSF was $535.98, median Days on Market was 19 days, median listing-to-contract time was 25 days, and median contract-to-close time was 29 days. Segment comparisons show meaningful descriptive differences by housing form and geography, but they do not establish that property type or location caused those differences.

No private CSV, row-level MLS record, school-boundary file, credential, or confidential handbook is included in Git. All results in this report are aggregate-level findings.

## Handbook completion checklist

| Requirement | Implementation | Status |
|---|---|---|
| Price ratio and close-to-original-list ratio | One nonduplicated `close_to_original_list_ratio` field using `ClosePrice / OriginalListPrice` | Complete |
| Price per square foot | `close_price_per_sqft` using valid positive close price and living area | Complete |
| Days on Market | Existing `DaysOnMarket` validated; negative values excluded from summaries | Complete |
| Year, Month, and YrMo | Added `close_year` and `close_month`; validated and reused `year_month` | Complete |
| Listing-to-contract days | Nonnegative `PurchaseContractDate - ListingContractDate` | Complete |
| Contract-to-close days | Nonnegative `CloseDate - PurchaseContractDate` | Complete |
| School districts | Separate elementary, high-school, and unified district name/code fields | Complete |
| Sample populated output | Safe synthetic example in the notebook; no private MLS row displayed | Complete |
| Segmented summary | PropertySubType, CountyOrParish, and MLSAreaMajor summaries | Complete |
| Reproducible script | `src/week6_features.py` with calculations, audits, saving, and validation | Complete |

## Input, output, and scope

- Input: `data/processed/analysis_ready_sold_residential.csv`
- Output: `data/processed/market_metrics_sold_residential.csv`

| Measure | Value |
|---|---:|
| Residential sold records | 495,334 |
| Source months | 33 |
| Coverage | January 2024–September 2026 |
| Input columns | 85 |
| Engineered metric columns | 6 |
| School-district fields | 6 |
| Final columns | 97 |

Close-dependent metrics were applied to sold records because they represent completed transactions. The analysis-ready listings dataset remains unchanged.

## Metric definitions and eligibility

| Metric | Definition | Eligible | Share | Ineligible treatment |
|---|---|---:|---:|---|
| Close-to-original-list ratio | `ClosePrice / OriginalListPrice` | 494,426 | 99.82% | Leave missing for absent or nonpositive prices |
| Close price per square foot | `ClosePrice / LivingArea` | 494,880 | 99.91% | Leave missing for absent or nonpositive inputs |
| Days on Market | Existing `DaysOnMarket` | 495,278 | 99.99% | Exclude negative values; retain zero |
| Close-date time fields | Year/month from `CloseDate`; validated `year_month` | 495,334 | 100.00% | Leave missing if date is missing |
| Listing to contract | `PurchaseContractDate - ListingContractDate` | 494,820 | 99.90% | Leave missing for absent dates or negative chronology |
| Contract to close | `CloseDate - PurchaseContractDate` | 494,894 | 99.91% | Leave missing for absent dates or negative chronology |

The handbook lists “Price Ratio” and “Close to Original List Ratio” with the same formula. One field satisfies both definitions without creating a misleading duplicate. Every ineligibility rule preserves the underlying record.

## Overall market findings

### Close-to-original-list ratio

The median ratio was 0.9944. The typical eligible property closed at 99.44% of its original list price, approximately 0.56% below the original asking price.

| Outcome | Records | Share of eligible |
|---|---:|---:|
| Below original list | 254,515 | 51.48% |
| At original list | 57,304 | 11.59% |
| Above original list | 182,607 | 36.93% |

A median near 1.0 does not mean most properties were unchanged: only 11.59% closed exactly at original list price.

### PPSF and market time

Median PPSF was $535.98. This means the typical eligible property sold for approximately $536 per square foot of living area. PPSF does not establish affordability or explain why one area is more expensive.

Median Days on Market was 19 days; half of eligible sold records had 19 days or less and half had 19 days or more. Its 37.65-day mean indicates a long right tail. Zero-day records remain valid, while 56 negative values were excluded from the summary but preserved.

Median listing-to-contract time was 25 days. Half of eligible properties reached an accepted purchase contract within 25 days and half took 25 days or longer. Its 45.65-day mean also shows a long right tail.

Median contract-to-close time was 29 days. Half of eligible transactions closed within 29 days after an accepted contract and half took 29 days or longer. This period can reflect financing, appraisal, inspection, title, escrow, and actions by both parties.

All 495,334 sold records have valid close-date time fields spanning 33 months. `year_month` distinguishes the same calendar month across different years and supports chronological trend analysis.

## School-district enrichment

The California 2024–25 file contains overlapping elementary, high-school, and unified service areas. Separate name/code fields preserve each district type without duplicating property rows.

| District type | Unique matches | Same-type ambiguity |
|---|---:|---:|
| Elementary | 121,334 | 0 |
| High school | 118,883 | 0 |
| Unified | 370,946 | 0 |

Of 495,334 records, 490,422 had eligible coordinates. Only 142 eligible records did not match any district. The 4,912 invalid-coordinate records remain preserved with missing district fields, and 2,000 valid cross-type overlaps remain in separate columns.

The join is a geographic assignment. It does not establish school quality, guarantee attendance at a particular school, or demonstrate a causal effect on property prices.

## Segment methodology and coverage

Each segment table reports record count and share, valid denominators, and medians for price, PPSF, close-to-original-list ratio, Days on Market, listing-to-contract days, and contract-to-close days. Only groups with at least 100 sold records are displayed.

| Segment | Distinct values | Missing | Qualifying groups |
|---|---:|---:|---:|
| PropertySubType | 20 | 923 | 11 |
| CountyOrParish | 63 | 0 | 44 |
| MLSAreaMajor | 1,097 | 67,273 | 598 |

`PropertyType` is constant (`Residential`) in the analysis-ready population, so it cannot produce a meaningful within-dataset comparison. Office-level competitive intelligence was outside the three analyst-selected summaries and remains appropriate for the later competitive-analysis dashboard. The formal Week 6 deliverable requires at least one summary grouped by PropertyType or CountyOrParish; the county table satisfies that requirement.

### PropertySubType

Among single-family residences, condominiums, and townhouses, condominiums had the lowest median sale price at $625,000 but the highest median PPSF at $561.72. Smaller living areas may contribute, although location, amenities, and property mix may also matter. Condominiums took longest to sell, with a 25-day median.

Their median ratio of 0.9848 means the typical eligible condominium sold at 98.48% of original asking price, approximately 1.52% below it. PPSF is calculated per property and then summarized with the median.

### CountyOrParish

Among the five largest county groups, Orange had the highest median price at $1,185,000 and highest median PPSF at $674.99. San Bernardino had the lowest median price at $535,000, while Riverside had the lowest PPSF at $320.70 and longest median Days on Market at 30 days.

Compared with Orange, Riverside's median price was $585,000 (49.37%) lower and its median PPSF was $354.29 (52.49%) lower. Riverside's median selling time was twice Orange's 15 days. Riverside's ratio of 0.9854 indicates a typical discount of 1.46%; Orange's 0.9929 indicates approximately 0.71%.

Riverside has 12,535 more records than Orange in this dataset, but this describes dataset coverage—not total market size. Property prices also do not establish resident wealth.

### MLSAreaMajor

Among the five largest defined MLS areas, Corona had the highest median price at $757,500 and PPSF at $396.38. Victorville had the lowest median price at $439,900 and PPSF at $238.12. Riverside had the shortest median Days on Market at 20 days.

Compared with Victorville, Corona had 460 more records, a $317,600 higher median price, a $158.26 higher median PPSF, and a three-day shorter selling time. Corona's 0.9941 ratio indicates a typical 0.59% discount. Victorville's median ratio of 1.0000 does not mean every property sold at original asking price. Missing ratios remain missing rather than becoming zero.

`MLSAreaMajor` is granular and fragmented: 1,097 labels, 67,273 missing records, and 50,310 `Not Defined` records. Its largest defined area represents only 4.88% of the full dataset. County is therefore better for an initial statewide comparison; MLS area is better for local drill-downs.

## Limitations and Week 7 handoff

Week 6 preserves extreme values for systematic Week 7 review.

| Metric | Median | Maximum |
|---|---:|---:|
| Close-to-original-list ratio | 0.9944 | 9,118,000.00 |
| PPSF | $535.98 | $1,164,066.85 |
| Days on Market | 19 | 12,430 |
| Listing to contract | 25 | 14,657 |
| Contract to close | 29 | 36,629 |

These maxima may be entry errors, unusual records, or valid exceptions. They are not deleted automatically. Other limitations are:

1. Segment findings are descriptive, not causal.
2. Medians are unadjusted for size, age, condition, amenities, month, or property mix.
3. Records are the counting unit and are not asserted to be unique physical properties.
4. The 2024–25 district boundaries are applied across January 2024–September 2026.
5. MLSAreaMajor is less standardized and less complete than CountyOrParish.

## Reproducible artifacts

- `src/week6_features.py` — transformation and validation workflow.
- `notebooks/06_market_metrics.ipynb` — definitions, validations, charts, tables, and analyst interpretation.
- `reports/week6_market_metrics_report.md` — this supervisor-facing report.
- Four private outputs under `data/processed/`: the 97-column dataset and three segment summaries.
- `docs/project_log.md` — chronological decision record.

## Next phase

Week 7 will apply IQR and percentile diagnostics, add outlier flags, preserve a full flagged dataset, create a separate filtered analysis dataset, and compare record counts and medians before and after filtering. The handbook specifically requires ClosePrice, LivingArea, and DaysOnMarket; the extreme Week 6 ratio and PPSF values should also be reviewed.
