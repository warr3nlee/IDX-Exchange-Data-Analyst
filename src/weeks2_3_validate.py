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
    "listings": 655_943,
    "sold": 495_334,
}

EXPECTED_SOURCE_MONTHS = 33

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

FIELD_GROUPS = {
    "identifiers": [
        "ListingKey",
        "ListingKeyNumeric",
        "ListingId",
    ],
    "dates": [
        "ListingContractDate",
        "PurchaseContractDate",
        "CloseDate",
        "ContractStatusChangeDate",
    ],
    "prices": [
        "ListPrice",
        "OriginalListPrice",
        "ClosePrice",
        "AssociationFee",
    ],
    "property_characteristics": [
        "PropertyType",
        "PropertySubType",
        "LivingArea",
        "LotSizeAcres",
        "BedroomsTotal",
        "BathroomsTotalInteger",
        "YearBuilt",
        "DaysOnMarket",
        "NewConstructionYN",
    ],
    "geography": [
        "CountyOrParish",
        "City",
        "PostalCode",
        "MLSAreaMajor",
        "Latitude",
        "Longitude",
    ],
    "market_participants": [
        "ListOfficeName",
        "BuyerOfficeName",
        "ListAgentFullName",
        "ListAgentFirstName",
        "ListAgentLastName",
        "BuyerAgentFirstName",
        "BuyerAgentLastName",
    ],
}

CORE_ANALYSIS_FIELDS = set().union(
    FIELD_GROUPS["dates"],
    FIELD_GROUPS["prices"],
    FIELD_GROUPS["property_characteristics"],
    FIELD_GROUPS["geography"],
)


def missing_value_recommendation(
    column: str,
    missing_percent: float,
) -> str:
    """Recommend analytical treatment without altering source data."""

    if missing_percent == 100:
        return "exclude_current_analysis_all_missing"
    if missing_percent > 90:
        return "review_sparse_exclude_by_default"
    if column in CORE_ANALYSIS_FIELDS:
        return "retain_core_field"
    return "retain_or_review_for_use_case"



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
    report["recommendation"] = [
        missing_value_recommendation(
            column=row.column,
            missing_percent=row.missing_percent,
        )
        for row in report.itertuples()
    ]

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


def analyze_field_roles(
    frame: pd.DataFrame,
    dataset: str,
) -> pd.DataFrame:
    """Separate core analytical fields from identifiers and metadata."""

    assigned_fields: set[str] = set()
    rows = []

    for role, fields in FIELD_GROUPS.items():
        present = [column for column in fields if column in frame.columns]
        missing = [column for column in fields if column not in frame.columns]
        assigned_fields.update(present)
        rows.append(
            {
                "field_role": role,
                "present_count": len(present),
                "missing_count": len(missing),
                "present_fields": ", ".join(present),
                "missing_fields": ", ".join(missing),
            }
        )

    other_metadata = [
        column
        for column in frame.columns
        if column not in assigned_fields
    ]
    rows.append(
        {
            "field_role": "other_metadata",
            "present_count": len(other_metadata),
            "missing_count": 0,
            "present_fields": ", ".join(other_metadata),
            "missing_fields": "",
        }
    )

    report = pd.DataFrame(rows)
    print(f"\n{dataset.upper()} FIELD ROLES")
    for row in report.itertuples():
        print(
            f"  {row.field_role}: {row.present_count} present, "
            f"{row.missing_count} expected fields absent"
        )

    return report


def analyze_filtered_categories(
    frame: pd.DataFrame,
    dataset: str,
) -> pd.DataFrame:
    """Summarize filtered property types and subtypes without row data."""

    rows = []
    for column in ("PropertyType", "PropertySubType"):
        if column not in frame.columns:
            continue

        values = frame[column].fillna("<missing>").astype(str)
        counts = values.value_counts(dropna=False)
        for value, count in counts.items():
            rows.append(
                {
                    "column": column,
                    "category": value,
                    "record_count": int(count),
                    "share_percent": count / len(frame) * 100,
                }
            )

    report = pd.DataFrame(rows)
    print(f"\n{dataset.upper()} FILTERED PROPERTY CATEGORIES")
    for row in report.itertuples():
        print(
            f"  {row.column} / {row.category}: "
            f"{row.record_count:,} ({row.share_percent:.2f}%)"
        )

    return report


def analyze_identifier_repetition(
    frame: pd.DataFrame,
    dataset: str,
) -> pd.DataFrame:
    """Count repeated identifiers without displaying identifier values."""

    rows = []
    for column in FIELD_GROUPS["identifiers"]:
        if column not in frame.columns:
            continue

        valid = (
            frame[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
            .dropna()
        )
        repeated_mask = valid.duplicated(keep=False)
        rows.append(
            {
                "identifier": column,
                "nonmissing_records": len(valid),
                "unique_identifiers": valid.nunique(),
                "repeated_identifier_values": (
                    valid.loc[repeated_mask].nunique()
                ),
                "records_using_repeated_identifiers": repeated_mask.sum(),
            }
        )

    report = pd.DataFrame(rows)
    print(f"\n{dataset.upper()} IDENTIFIER REPETITION")
    for row in report.itertuples():
        print(
            f"  {row.identifier}: {row.unique_identifiers:,} unique; "
            f"{row.repeated_identifier_values:,} repeated values across "
            f"{row.records_using_repeated_identifiers:,} records"
        )

    return report


def analyze_date_consistency(
    frame: pd.DataFrame,
    dataset: str,
) -> pd.DataFrame:
    """Report aggregate date parsing and ordering issues for later flags."""

    parsed_dates = {}
    for column in FIELD_GROUPS["dates"]:
        if column not in frame.columns:
            continue
        parsed_dates[column] = pd.to_datetime(
            frame[column],
            errors="coerce",
            format="mixed",
            utc=True,
        )

    checks = [
        (
            "listing_after_purchase",
            "ListingContractDate",
            "PurchaseContractDate",
        ),
        (
            "purchase_after_close",
            "PurchaseContractDate",
            "CloseDate",
        ),
        (
            "listing_after_close",
            "ListingContractDate",
            "CloseDate",
        ),
    ]

    rows = []
    for check, earlier_field, later_field in checks:
        if earlier_field not in parsed_dates or later_field not in parsed_dates:
            continue

        eligible = (
            parsed_dates[earlier_field].notna()
            & parsed_dates[later_field].notna()
        )
        violations = (
            parsed_dates[earlier_field]
            > parsed_dates[later_field]
        ) & eligible
        eligible_count = int(eligible.sum())
        violation_count = int(violations.sum())
        rows.append(
            {
                "check": check,
                "eligible_records": eligible_count,
                "violation_count": violation_count,
                "violation_percent": (
                    violation_count / eligible_count * 100
                    if eligible_count
                    else 0.0
                ),
            }
        )

    report = pd.DataFrame(rows)
    print(f"\n{dataset.upper()} PRELIMINARY DATE CONSISTENCY")
    for row in report.itertuples():
        print(
            f"  {row.check}: {row.violation_count:,} of "
            f"{row.eligible_records:,} eligible records "
            f"({row.violation_percent:.2f}%)"
        )

    return report


def analyze_sold_market_questions(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Answer handbook pricing and county questions for sold records."""

    close_price = pd.to_numeric(frame["ClosePrice"], errors="coerce")
    list_price = pd.to_numeric(frame["ListPrice"], errors="coerce")
    valid_price = (
        close_price.notna()
        & list_price.notna()
        & close_price.gt(0)
        & list_price.gt(0)
    )

    comparison_masks = {
        "sold_above_list": valid_price & close_price.gt(list_price),
        "sold_at_list": valid_price & close_price.eq(list_price),
        "sold_below_list": valid_price & close_price.lt(list_price),
    }
    valid_count = int(valid_price.sum())
    price_report = pd.DataFrame(
        [
            {
                "outcome": outcome,
                "record_count": int(mask.sum()),
                "share_percent": (
                    mask.sum() / valid_count * 100
                    if valid_count
                    else 0.0
                ),
            }
            for outcome, mask in comparison_masks.items()
        ]
    )

    counties = frame["CountyOrParish"].astype("string").str.strip()
    county_source = pd.DataFrame(
        {
            "county": counties,
            "close_price": close_price,
        }
    )
    county_source = county_source.loc[
        county_source["county"].notna()
        & county_source["county"].ne("")
        & county_source["close_price"].gt(0)
    ]
    county_report = (
        county_source.groupby("county", as_index=False)
        .agg(
            transaction_count=("close_price", "size"),
            median_close_price=("close_price", "median"),
            mean_close_price=("close_price", "mean"),
        )
        .loc[lambda data: data["transaction_count"] >= 100]
        .sort_values(
            ["median_close_price", "transaction_count"],
            ascending=[False, False],
        )
        .head(10)
        .reset_index(drop=True)
    )

    print("\nSOLD PRICE OUTCOMES VS CURRENT LIST PRICE")
    for row in price_report.itertuples():
        print(
            f"  {row.outcome}: {row.record_count:,} "
            f"({row.share_percent:.2f}%)"
        )

    print("\nTOP COUNTIES BY MEDIAN CLOSE PRICE (100+ RECORDS)")
    for row in county_report.itertuples():
        print(
            f"  {row.county}: median ${row.median_close_price:,.0f}; "
            f"{row.transaction_count:,} records"
        )

    return price_report, county_report


def main() -> int:
    """Run the Weeks 2–3 dataset validation and EDA workflow."""

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
        analyze_field_roles(
            frame=frame,
            dataset=dataset,
        )
        analyze_filtered_categories(
            frame=frame,
            dataset=dataset,
        )
        analyze_identifier_repetition(
            frame=frame,
            dataset=dataset,
        )
        analyze_date_consistency(
            frame=frame,
            dataset=dataset,
        )

        if dataset == "sold":
            analyze_sold_market_questions(frame)


        del frame, missing_report, numeric_report

    print("\nWEEKS 2–3 DATASET VALIDATION AND EDA COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
