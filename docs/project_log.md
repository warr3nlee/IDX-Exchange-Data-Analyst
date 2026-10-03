# IDX Internship Project Log

## 2026-09-26
- Set up WSL project structure and public GitHub repo.
- Added `.gitignore` to protect confidential MLS CSV files.
- Found that provided extraction scripts contain an internal IDX token endpoint, so they should remain private.
- Confirmed FTP data covers Jan 2024 through Apr 2026.
- Found some sold files use `_filled` suffix and contain extra `latfilled` / `lonfilled` columns.
- Confirmed those columns are not created by `crmls_sold.py`.
- Generated missing listing files for May–Aug 2026 using `crmls_listed.py`.
- Generated missing sold files for May–Aug 2026 using `crmls_sold.py`.
- Confirmed monthly coverage is complete from Jan 2024 through Aug 2026 for both listings and sold data.
- Noted that older `_filled` sold files have a schema difference that needs to be handled carefully during Week 1 aggregation.

## 2026-10-03
- Started Week 1 monthly dataset aggregation with a read-only preflight audit.
- Confirmed one listing file and one sold file exist for every month from January 2024 through August 2026.
- Identified three ordered listing schema groups and six ordered sold schema groups.
- Confirmed listing headers repeat 11 column names; the duplicate values agree in structurally complete records.
- Confirmed seven historical sold files contain populated `latfilled` and `lonfilled` columns that should be retained intentionally.
- Detected that `CRMLSListing202601.csv` appears truncated: it has an unusually low row count, its final record has fewer fields than the header, and the file lacks a final line terminator.
- Added `src/week1_aggregate.py` to validate coverage, schemas, record widths, duplicate-column agreement, and aggregate row counts before concatenation.
- The preflight stopped as designed, and no processed datasets were created.
- Regenerated the January 2026 listings extract, retained the truncated source privately for reference, and validated 25,933 structurally complete January records.
- Reran the preflight successfully after replacing the damaged January input.
- Combined 996,267 listing records and filtered them to 633,662 Residential records.
- Combined 714,370 sold records and filtered them to 480,486 Residential records.
- Saved the private outputs as `data/processed/combined_listings_residential.csv` and `data/processed/combined_sold_residential.csv`.
- Independently confirmed exact output counts, all 32 source months, zero non-Residential rows, zero malformed records, no duplicate headers, and preservation of the optional filled-coordinate fields.

### Weeks 2–3 first-half checkpoint
- Started the exploratory data analysis and validation phase with `src/weeks2_3_validate.py`.
- Reached the agreed halfway stopping point for Weeks 2–3: input, structural, missing-value, and selected numeric-distribution checks are complete. The deeper EDA, visualizations, date checks, and mortgage-rate enrichment remain for the next session.
- Kept the workflow read-only: the validation script loads and summarizes the Week 1 outputs but does not modify, clean, remove, or overwrite any MLS records.
- Kept the reporting confidentiality-safe: only aggregate counts, percentages, data types, and descriptive statistics are printed; no row-level MLS data is displayed.
- Validated the private inputs `data/processed/combined_listings_residential.csv` (293.1 MB) and `data/processed/combined_sold_residential.csv` (273.5 MB). These CSV files remain excluded from Git.
- Reconfirmed the listings dataset contains 633,662 rows, 75 columns, all 32 expected source months, and zero non-Residential rows.
- Reconfirmed the sold dataset contains 480,486 rows, 86 columns, all 32 expected source months, and zero non-Residential rows.
- Recorded listings data types: 39 string columns, 29 float columns, 4 integer columns, and 3 object columns.
- Recorded sold data types: 44 string columns, 29 float columns, 4 integer columns, and 9 object columns.
- Added enforced guards for the expected row counts, 32-month coverage, Residential-only scope, required numeric fields, and absence of duplicate processed-data columns.
- Listings missingness: 63 of 75 columns contain at least one missing value, and 13 columns are more than 90% missing.
- Sold missingness: 74 of 86 columns contain at least one missing value, and 15 columns are more than 90% missing.
- Eight fields are 100% missing in both datasets: `TaxAnnualAmount`, `AboveGradeFinishedArea`, `FireplacesTotal`, `TaxYear`, `ElementarySchoolDistrict`, `BusinessType`, `CoveredSpaces`, and `MiddleOrJuniorSchoolDistrict`.
- Additional listings fields above 90% missing are `BelowGradeFinishedArea` (99.41%), `CoBuyerAgentFirstName` (97.08%), `BuilderName` (95.39%), `LotSizeDimensions` (94.79%), and `BuildingAreaTotal` (91.24%).
- Additional sold fields above 90% missing are `WaterfrontYN` (99.94%), `BelowGradeFinishedArea` (99.39%), `BasementYN` (98.04%), `BuilderName` (95.13%), `LotSizeDimensions` (95.12%), `BuildingAreaTotal` (92.98%), and `CoBuyerAgentFirstName` (90.80%).
- Confirmed all non-missing values in the nine selected numeric fields converted successfully to numeric values in both datasets, with zero coercion failures.
- Selected central results: listings have median ListPrice $840,000, median LivingArea 1,670 square feet, and median DaysOnMarket 11; sold records have median ClosePrice $825,000, median LivingArea 1,647 square feet, and median DaysOnMarket 19.
- The numeric audit surfaced values requiring later validity rules and outlier review: negative DaysOnMarket values, zero prices and living areas, very large price/area/acreage values, unusually high bedroom and bathroom counts, and future YearBuilt values.
- Notable observed extremes include listings DaysOnMarket from -75 to 1,155 and sold DaysOnMarket from -288 to 12,430; listings ListPrice up to $400 million; sold ClosePrice up to $989.5 million; and LivingArea up to 17,021,321 square feet in both datasets.
- ClosePrice is 70.74% missing in the listings dataset, which is broadly consistent with listings that did not become closed sales. The sold dataset has only two missing ClosePrice values; those records should be investigated later without printing confidential row details.
- Decision: do not automatically delete sparse columns or extreme records. Sparse fields may represent legitimate optional features, and suspicious numeric values will be evaluated with explicit domain rules and outlier flags in later cleaning work.
- Decision: prefer medians and percentile-based summaries when describing these skewed fields; means are strongly influenced by the extreme values.
- Next-session resume point: save reusable missingness and numeric summary outputs, create confidentiality-safe distribution plots, review property-category values and filtering logic, and test date consistency.
- Later Weeks 2–3 work also includes obtaining the approved FRED mortgage-rate series, converting it to the project month key, merging it into the MLS analysis data, validating the join, and documenting the enriched outputs.
- Validation commands for this checkpoint: `.venv/bin/python -m py_compile src/weeks2_3_validate.py` followed by `.venv/bin/python src/weeks2_3_validate.py`.
