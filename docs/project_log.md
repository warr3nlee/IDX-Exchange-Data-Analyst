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
