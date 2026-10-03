"""Weeks 2–3: validate and explore the combined MLS datasets.

This script reports aggregate data-quality information only. It does not
display confidential row-level MLS records.
"""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

INPUT_FILES = {
    "listings": PROCESSED_DIR / "combined_listings_residential.csv",
    "sold": PROCESSED_DIR / "combined_sold_residential.csv",
}

EXPECTED_ROWS = {
    "listings": 633_662,
    "sold": 480_486,
}

EXPECTED_SOURCE_MONTHS = 32

NUMERIC_FIELDS = {
    "listings": [
        "ClosePrice",
        "ListPrice",
        "OriginalListPrice",
        "LivingArea",
        "LotSizeAcres",
        "BedroomsTotal",
        "BathroomsTotalInteger",
        "DaysOnMarket",
        "YearBuilt",
    ],
    "sold": [
        "ClosePrice",
        "ListPrice",
        "OriginalListPrice",
        "LivingArea",
        "LotSizeAcres",
        "BedroomsTotal",
        "BathroomsTotalInteger",
        "DaysOnMarket",
        "YearBuilt",
    ],
}


def validate_inputs() -> None:
    """Confirm that both private Week 1 outputs are available."""

    missing_files = [
        path
        for path in INPUT_FILES.values()
        if not path.exists()
    ]

    if missing_files:
        missing_text = "\n".join(
            str(path)
            for path in missing_files
        )
        raise FileNotFoundError(
            "Required Week 1 outputs are missing:\n"
            f"{missing_text}"
        )

    print("INPUT FILES")

    for dataset, path in INPUT_FILES.items():
        size_mb = path.stat().st_size / (1024**2)

        print(
            f"{dataset}: "
            f"{path.relative_to(PROJECT_ROOT)} "
            f"({size_mb:.1f} MB)"
        )


def inspect_structure(
    dataset: str,
    path: Path,
) -> pd.DataFrame:
    """Load one dataset and report safe structural information."""

    print(f"\nLoading {dataset}...")

    frame = pd.read_csv(
        path,
        low_memory=False,
    )

    if len(frame) != EXPECTED_ROWS[dataset]:
        raise ValueError(
            f"{dataset}: expected {EXPECTED_ROWS[dataset]:,} rows, "
            f"but found {len(frame):,}"
        )

    duplicate_columns = frame.columns[
        frame.columns.duplicated()
    ].tolist()

    if duplicate_columns:
        raise ValueError(
            f"{dataset}: duplicate columns found: {duplicate_columns}"
        )

    source_months = frame["_source_month"].nunique()
    non_residential = (
        frame["PropertyType"] != "Residential"
    ).sum()

    if source_months != EXPECTED_SOURCE_MONTHS:
        raise ValueError(
            f"{dataset}: expected {EXPECTED_SOURCE_MONTHS} source months, "
            f"but found {source_months}"
        )

    if non_residential:
        raise ValueError(
            f"{dataset}: found {non_residential:,} non-Residential rows"
        )

    print(f"Rows: {len(frame):,}")
    print(f"Columns: {len(frame.columns):,}")
    print(f"Source months: {source_months}")
    print(f"Non-Residential rows: {non_residential:,}")

    print("Data types:")

    dtype_counts = (
        frame.dtypes
        .astype(str)
        .value_counts()
    )

    for dtype, count in dtype_counts.items():
        print(f"  {dtype}: {count} columns")

    return frame


def analyze_missing_values(
    frame: pd.DataFrame,
    dataset: str,
) -> pd.DataFrame:
    """Calculate and summarize missing values by column."""

    missing_count = frame.isna().sum()

    missing_percent = (
        missing_count
        / len(frame)
        * 100
    )

    report = pd.DataFrame(
        {
            "column": frame.columns,
            "missing_count": missing_count.values,
            "missing_percent": missing_percent.values,
        }
    ).sort_values(
        by="missing_percent",
        ascending=False,
    )

    columns_with_missing = (
        report["missing_count"] > 0
    ).sum()

    high_missing = report.loc[
        report["missing_percent"] > 90
    ]

    print(f"\n{dataset.upper()} MISSING VALUES")
    print(
        f"Columns with missing values: "
        f"{columns_with_missing} of {len(frame.columns)}"
    )
    print(
        f"Columns above 90% missing: "
        f"{len(high_missing)}"
    )

    print("Ten highest missing percentages:")

    for row in report.head(10).itertuples():
        print(
            f"  {row.column}: "
            f"{row.missing_count:,} missing "
            f"({row.missing_percent:.2f}%)"
        )

    if not high_missing.empty:
        print("Columns above 90% missing:")

        for row in high_missing.itertuples():
            print(
                f"  {row.column}: "
                f"{row.missing_percent:.2f}%"
            )

    return report


def analyze_numeric_distributions(
    frame: pd.DataFrame,
    dataset: str,
) -> pd.DataFrame:
    """Summarize important numeric fields without printing records."""

    summary_rows = []

    for column in NUMERIC_FIELDS[dataset]:
        if column not in frame.columns:
            raise ValueError(
                f"{dataset}: required numeric field "
                f"{column!r} is missing"
            )

        original_nonmissing = frame[column].notna().sum()

        numeric = pd.to_numeric(
            frame[column],
            errors="coerce",
        )

        valid = numeric.dropna()

        coercion_failures = (
            original_nonmissing
            - valid.count()
        )

        summary_rows.append(
            {
                "column": column,
                "valid_count": valid.count(),
                "missing_percent": numeric.isna().mean() * 100,
                "minimum": valid.min(),
                "percentile_25": valid.quantile(0.25),
                "median": valid.median(),
                "mean": valid.mean(),
                "percentile_75": valid.quantile(0.75),
                "percentile_99": valid.quantile(0.99),
                "maximum": valid.max(),
                "coercion_failures": coercion_failures,
            }
        )

    report = pd.DataFrame(summary_rows)

    print(f"\n{dataset.upper()} NUMERIC DISTRIBUTIONS")

    for row in report.itertuples():
        print(f"\n{row.column}")
        print(f"  Valid values: {row.valid_count:,}")
        print(f"  Missing: {row.missing_percent:.2f}%")
        print(f"  Minimum: {row.minimum:,.2f}")
        print(f"  25th percentile: {row.percentile_25:,.2f}")
        print(f"  Median: {row.median:,.2f}")
        print(f"  Mean: {row.mean:,.2f}")
        print(f"  75th percentile: {row.percentile_75:,.2f}")
        print(f"  99th percentile: {row.percentile_99:,.2f}")
        print(f"  Maximum: {row.maximum:,.2f}")
        print(f"  Coercion failures: {row.coercion_failures:,}")

    return report


def main() -> int:
    """Run the first-half Weeks 2–3 validation workflow."""

    validate_inputs()
    print("\nInput validation passed.")

    for dataset, path in INPUT_FILES.items():
        frame = inspect_structure(
            dataset=dataset,
            path=path,
        )

        missing_report = analyze_missing_values(
            frame=frame,
            dataset=dataset,
        )
        numeric_report = analyze_numeric_distributions(
            frame=frame,
            dataset=dataset,
        )

        del frame, missing_report, numeric_report

    print("\nWEEKS 2–3 FIRST-HALF VALIDATION COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
