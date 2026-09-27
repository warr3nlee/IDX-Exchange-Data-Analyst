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