# IDX Exchange Analysis Notebooks

This directory is the long-term analytical narrative for the internship project. Each notebook combines a business question, reproducible code, aggregate results, interpretation, decisions, and next steps.

Reusable processing logic belongs in `src/`. Private MLS data belongs in `data/` and must never be committed. Notebooks should call the reusable code and explain what the results mean.

## Handbook-aligned notebook roadmap

| Notebook | Handbook phase | Status |
|---|---|---|
| `00_pipeline_orientation.ipynb` | Week 0 – MLS Data Pipeline Orientation | Backfilled |
| `01_monthly_aggregation.ipynb` | Week 1 – Monthly Dataset Aggregation | Backfilled |
| `02_03_data_validation_eda.ipynb` | Weeks 2–3 – Dataset Structuring and Validation | Complete |
| `02_03_mortgage_enrichment.ipynb` | Weeks 2–3 – Mortgage Rate Enrichment | Complete |
| `04_05_cleaning_preparation.ipynb` | Weeks 4–5 – Data Cleaning and Preparation | Planned |
| `06_market_metrics.ipynb` | Week 6 – Feature Engineering and Market Metrics | Planned |
| `07_outlier_detection.ipynb` | Week 7 – Outlier Detection and Data Quality | Planned |
| `08_10_tableau_development.ipynb` | Weeks 8–10 – Tableau Dashboard Development | Planned |
| `11_12_final_findings.ipynb` | Weeks 11–12 – Final Report and Presentation | Planned |

Planned notebooks should be created when their phase begins. This keeps the repository useful and avoids empty placeholders.

## Standard notebook structure

Every analytical notebook should contain:

1. Objective and business question
2. Inputs, scope, and definitions
3. Reproducible validation or analysis code
4. Aggregate tables and visualizations
5. Findings in plain English
6. Decisions and assumptions
7. Questions for the supervisor
8. Next steps

## Confidentiality rules

- Never display raw MLS rows with `head()`, `sample()`, or unrestricted cell output.
- Never output addresses, names, coordinates, contact details, or listing identifiers.
- Display aggregate counts, percentages, statistics, and charts only.
- Do not place credentials, FTP details, or private endpoints in notebooks.
- Review every saved cell output before committing a notebook.
- Keep `data/raw/`, `data/processed/`, handbooks, and private extraction scripts out of Git.

## Working method

1. Activate the project environment from the repository root.
2. Install dependencies with `python -m pip install -r requirements.txt`.
3. Start Jupyter with `jupyter lab`, or open the notebook in VS Code and select the project `.venv` kernel.
4. Use **Restart Kernel and Run All Cells** before a milestone review.
5. Confirm that every output is aggregate-only.
6. Run `git diff --check` and review the notebook diff before committing.

## Supporting documentation

- `docs/project_log.md` is the chronological work record.
- `reports/` contains concise milestone summaries.
- `src/` contains reusable and testable analysis logic.
