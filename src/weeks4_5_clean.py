"""Weeks 4–5: prepare analysis-ready Residential MLS datasets.

The handbook requires standardized dates and numeric fields, documented
missing-value treatment, date-consistency flags, and geographic quality
flags. Invalid records are flagged rather than silently deleted. Console
output is aggregate-only and never displays confidential MLS records.
"""

from pathlib import Path

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

INPUT_FILES = {
    "listings": (
        PROCESSED_DIR
        / "combined_listings_residential_with_mortgage_rates.csv"
    ),
    "sold": (
        PROCESSED_DIR
        / "combined_sold_residential_with_mortgage_rates.csv"
    ),
}

OUTPUT_FILES = {
    "listings": PROCESSED_DIR / "analysis_ready_listings_residential.csv",
    "sold": PROCESSED_DIR / "analysis_ready_sold_residential.csv",
}

EXPECTED_ROWS = {
    "listings": 655_943,
    "sold": 495_334,
}

EXPECTED_SOURCE_MONTHS = 33

DATE_FIELDS = [
    "CloseDate",
    "PurchaseContractDate",
    "ListingContractDate",
    "ContractStatusChangeDate",
]

NUMERIC_FIELDS = [
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "BuildingAreaTotal",
    "BelowGradeFinishedArea",
    "LotSizeAcres",
    "LotSizeArea",
    "LotSizeSquareFeet",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "DaysOnMarket",
    "YearBuilt",
    "ParkingTotal",
    "Stories",
    "MainLevelBedrooms",
    "GarageSpaces",
    "AssociationFee",
    "Latitude",
    "Longitude",
    "rate_30yr_fixed",
]

# These row-level contact and address fields are not needed for the handbook's
# later aggregate market analysis. They remain available in the private source
# datasets but are omitted from the analysis-ready outputs to reduce exposure.
ANALYSIS_UNUSED_COLUMNS = {
    "UnparsedAddress",
    "StreetNumberNumeric",
    "ListAgentEmail",
    "ListAgentFirstName",
    "ListAgentLastName",
    "ListAgentFullName",
    "CoListAgentFirstName",
    "CoListAgentLastName",
    "BuyerAgentMlsId",
    "BuyerAgentFirstName",
    "BuyerAgentLastName",
    "CoBuyerAgentFirstName",
}

FLAG_COLUMNS = [
    "date_parse_error_flag",
    "numeric_parse_error_flag",
    "missing_required_date_flag",
    "listing_after_close_flag",
    "purchase_after_close_flag",
    "negative_timeline_flag",
    "invalid_close_price_flag",
    "invalid_living_area_flag",
    "invalid_days_on_market_flag",
    "negative_bedrooms_flag",
    "negative_bathrooms_flag",
    "invalid_numeric_flag",
    "missing_coordinates_flag",
    "zero_coordinates_flag",
    "positive_longitude_flag",
    "implausible_coordinates_flag",
    "invalid_coordinates_flag",
]

# A deliberately broad rectangular screen. It identifies records for review;
# it is not a substitute for a precise California boundary spatial join.
CA_LATITUDE_RANGE = (32.0, 42.5)
CA_LONGITUDE_RANGE = (-125.0, -113.0)


def validate_input(dataset: str, frame: pd.DataFrame) -> None:
    """Enforce the expected enriched-dataset structure."""

    if len(frame) != EXPECTED_ROWS[dataset]:
        raise ValueError(
            f"{dataset}: expected {EXPECTED_ROWS[dataset]:,} rows, "
            f"but found {len(frame):,}"
        )

    duplicate_columns = frame.columns[frame.columns.duplicated()].tolist()
    if duplicate_columns:
        raise ValueError(
            f"{dataset}: duplicate columns found: {duplicate_columns}"
        )

    required_columns = {
        "PropertyType",
        "_source_month",
        "rate_30yr_fixed",
        "Latitude",
        "Longitude",
        "ClosePrice",
        "LivingArea",
        "DaysOnMarket",
        "BedroomsTotal",
        "BathroomsTotalInteger",
        *DATE_FIELDS,
    }
    missing_columns = sorted(required_columns - set(frame.columns))
    if missing_columns:
        raise ValueError(
            f"{dataset}: required columns are missing: {missing_columns}"
        )

    non_residential = frame["PropertyType"].ne("Residential").sum()
    if non_residential:
        raise ValueError(
            f"{dataset}: found {non_residential:,} non-Residential rows"
        )

    source_months = frame["_source_month"].nunique(dropna=True)
    if source_months != EXPECTED_SOURCE_MONTHS:
        raise ValueError(
            f"{dataset}: expected {EXPECTED_SOURCE_MONTHS} source months, "
            f"but found {source_months}"
        )

    missing_rates = frame["rate_30yr_fixed"].isna().sum()
    if missing_rates:
        raise ValueError(
            f"{dataset}: found {missing_rates:,} missing mortgage rates"
        )


def convert_date_fields(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Convert handbook date fields and flag nonblank parse failures."""

    parse_failures: dict[str, int] = {}
    any_parse_error = pd.Series(False, index=frame.index)

    for column in DATE_FIELDS:
        original = frame[column]
        nonblank = (
            original.notna()
            & original.astype("string").str.strip().ne("")
        )
        parsed = pd.to_datetime(
            original,
            errors="coerce",
            format="mixed",
            utc=True,
        )
        parse_error = nonblank & parsed.isna()
        parse_failures[column] = int(parse_error.sum())
        any_parse_error |= parse_error

        frame[column] = (
            parsed.dt.tz_localize(None).dt.normalize()
        )

    frame["date_parse_error_flag"] = any_parse_error.astype(bool)
    return frame, parse_failures


def convert_numeric_fields(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Convert analytical measures and flag nonblank coercion failures."""

    coercion_failures: dict[str, int] = {}
    any_parse_error = pd.Series(False, index=frame.index)

    for column in NUMERIC_FIELDS:
        if column not in frame.columns:
            continue

        original = frame[column]
        nonblank = (
            original.notna()
            & original.astype("string").str.strip().ne("")
        )
        converted = pd.to_numeric(original, errors="coerce")
        parse_error = nonblank & converted.isna()
        coercion_failures[column] = int(parse_error.sum())
        any_parse_error |= parse_error
        frame[column] = converted

    frame["numeric_parse_error_flag"] = any_parse_error.astype(bool)
    return frame, coercion_failures


def add_date_consistency_flags(
    frame: pd.DataFrame,
    dataset: str,
) -> pd.DataFrame:
    """Create the handbook date-order flags with explicit meanings."""

    listing = frame["ListingContractDate"]
    purchase = frame["PurchaseContractDate"]
    close = frame["CloseDate"]

    frame["listing_after_close_flag"] = (
        listing.notna() & close.notna() & listing.gt(close)
    )
    frame["purchase_after_close_flag"] = (
        purchase.notna() & close.notna() & purchase.gt(close)
    )
    frame["negative_timeline_flag"] = (
        listing.notna() & purchase.notna() & purchase.lt(listing)
    )

    required_date = (
        "ListingContractDate" if dataset == "listings" else "CloseDate"
    )
    frame["missing_required_date_flag"] = frame[required_date].isna()

    return frame


def add_numeric_validity_flags(frame: pd.DataFrame) -> pd.DataFrame:
    """Flag the invalid numeric conditions specified by the handbook."""

    frame["invalid_close_price_flag"] = (
        frame["ClosePrice"].notna() & frame["ClosePrice"].le(0)
    )
    frame["invalid_living_area_flag"] = (
        frame["LivingArea"].notna() & frame["LivingArea"].le(0)
    )
    frame["invalid_days_on_market_flag"] = (
        frame["DaysOnMarket"].notna() & frame["DaysOnMarket"].lt(0)
    )
    frame["negative_bedrooms_flag"] = (
        frame["BedroomsTotal"].notna()
        & frame["BedroomsTotal"].lt(0)
    )
    frame["negative_bathrooms_flag"] = (
        frame["BathroomsTotalInteger"].notna()
        & frame["BathroomsTotalInteger"].lt(0)
    )

    numeric_flags = [
        "invalid_close_price_flag",
        "invalid_living_area_flag",
        "invalid_days_on_market_flag",
        "negative_bedrooms_flag",
        "negative_bathrooms_flag",
    ]
    frame["invalid_numeric_flag"] = frame[numeric_flags].any(axis=1)

    return frame


def add_geographic_quality_flags(frame: pd.DataFrame) -> pd.DataFrame:
    """Create aggregate-safe coordinate quality flags."""

    latitude = frame["Latitude"]
    longitude = frame["Longitude"]

    frame["missing_coordinates_flag"] = (
        latitude.isna() | longitude.isna()
    )
    frame["zero_coordinates_flag"] = (
        latitude.eq(0) | longitude.eq(0)
    )
    frame["positive_longitude_flag"] = longitude.gt(0)

    coordinates_present = latitude.notna() & longitude.notna()
    outside_bounding_box = (
        latitude.lt(CA_LATITUDE_RANGE[0])
        | latitude.gt(CA_LATITUDE_RANGE[1])
        | longitude.lt(CA_LONGITUDE_RANGE[0])
        | longitude.gt(CA_LONGITUDE_RANGE[1])
    )
    frame["implausible_coordinates_flag"] = (
        coordinates_present & outside_bounding_box
    )

    geographic_flags = [
        "missing_coordinates_flag",
        "zero_coordinates_flag",
        "positive_longitude_flag",
        "implausible_coordinates_flag",
    ]
    frame["invalid_coordinates_flag"] = frame[geographic_flags].any(
        axis=1
    )

    return frame


def remove_unusable_columns(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Drop all-null and unnecessary sensitive columns from the output."""

    all_null_columns = sorted(
        column
        for column in frame.columns
        if frame[column].isna().all()
    )
    unused_columns = sorted(
        ANALYSIS_UNUSED_COLUMNS.intersection(frame.columns)
    )
    columns_to_remove = sorted(set(all_null_columns + unused_columns))

    return (
        frame.drop(columns=columns_to_remove),
        all_null_columns,
        unused_columns,
    )


def validate_cleaned_frame(
    dataset: str,
    frame: pd.DataFrame,
    input_rows: int,
) -> None:
    """Confirm row preservation, types, flags, and confidentiality choices."""

    if len(frame) != input_rows:
        raise ValueError(
            f"{dataset}: cleaning changed rows from {input_rows:,} "
            f"to {len(frame):,}"
        )

    remaining_unused = ANALYSIS_UNUSED_COLUMNS.intersection(frame.columns)
    if remaining_unused:
        raise ValueError(
            f"{dataset}: unnecessary columns remain: "
            f"{sorted(remaining_unused)}"
        )

    all_null_columns = [
        column for column in frame.columns if frame[column].isna().all()
    ]
    if all_null_columns:
        raise ValueError(
            f"{dataset}: all-null columns remain: {all_null_columns}"
        )

    invalid_date_types = [
        column
        for column in DATE_FIELDS
        if not is_datetime64_any_dtype(frame[column])
    ]
    if invalid_date_types:
        raise TypeError(
            f"{dataset}: date fields are not datetime: "
            f"{invalid_date_types}"
        )

    invalid_numeric_types = [
        column
        for column in NUMERIC_FIELDS
        if column in frame.columns and not is_numeric_dtype(frame[column])
    ]
    if invalid_numeric_types:
        raise TypeError(
            f"{dataset}: fields are not numeric: {invalid_numeric_types}"
        )

    invalid_flag_types = [
        column
        for column in FLAG_COLUMNS
        if column not in frame.columns or frame[column].dtype != bool
    ]
    if invalid_flag_types:
        raise TypeError(
            f"{dataset}: flags are missing or not boolean: "
            f"{invalid_flag_types}"
        )


def clean_dataset(
    dataset: str,
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Apply and document every Weeks 4–5 transformation."""

    validate_input(dataset, frame)

    input_rows = len(frame)
    input_columns = len(frame.columns)

    frame = frame.copy()
    frame, date_parse_failures = convert_date_fields(frame)
    frame, numeric_coercion_failures = convert_numeric_fields(frame)
    frame = add_date_consistency_flags(frame, dataset)
    frame = add_numeric_validity_flags(frame)
    frame = add_geographic_quality_flags(frame)
    frame, all_null_columns, unused_columns = remove_unusable_columns(frame)

    validate_cleaned_frame(dataset, frame, input_rows)

    summary: dict[str, object] = {
        "dataset": dataset,
        "input_rows": input_rows,
        "output_rows": len(frame),
        "input_columns": input_columns,
        "output_columns": len(frame.columns),
        "all_null_columns_removed": all_null_columns,
        "unused_columns_removed": unused_columns,
        "date_parse_failures": date_parse_failures,
        "numeric_coercion_failures": numeric_coercion_failures,
        "flag_counts": {
            column: int(frame[column].sum())
            for column in FLAG_COLUMNS
        },
        "date_dtypes": {
            column: str(frame[column].dtype)
            for column in DATE_FIELDS
        },
        "numeric_dtypes": {
            column: str(frame[column].dtype)
            for column in NUMERIC_FIELDS
            if column in frame.columns
        },
    }

    return frame, summary


def print_summary(summary: dict[str, object]) -> None:
    """Print the handbook-required aggregate cleaning evidence."""

    dataset = str(summary["dataset"])
    print(f"\n{dataset.upper()} CLEANING SUMMARY")
    print(
        f"Rows: {summary['input_rows']:,} before, "
        f"{summary['output_rows']:,} after"
    )
    print(
        f"Columns: {summary['input_columns']} before, "
        f"{summary['output_columns']} after"
    )

    print("All-null columns removed:")
    for column in summary["all_null_columns_removed"]:
        print(f"  {column}")

    print("Unused row-level columns removed:")
    for column in summary["unused_columns_removed"]:
        print(f"  {column}")

    print("Date parse failures:")
    for column, count in summary["date_parse_failures"].items():
        print(f"  {column}: {count:,}")

    numeric_parse_failures = sum(
        summary["numeric_coercion_failures"].values()
    )
    print(f"Numeric coercion failures: {numeric_parse_failures:,}")

    print("Date data types:")
    for column, dtype in summary["date_dtypes"].items():
        print(f"  {column}: {dtype}")

    print("Quality flag counts:")
    for column, count in summary["flag_counts"].items():
        print(f"  {column}: {count:,}")


def process_dataset(dataset: str) -> dict[str, object]:
    """Load, clean, save, and summarize one private dataset."""

    input_path = INPUT_FILES[dataset]
    output_path = OUTPUT_FILES[dataset]

    if not input_path.exists():
        raise FileNotFoundError(
            f"{dataset}: required input does not exist: {input_path}"
        )

    print(f"\nLoading {dataset}: {input_path.relative_to(PROJECT_ROOT)}")
    frame = pd.read_csv(input_path, low_memory=False)
    cleaned, summary = clean_dataset(dataset, frame)

    cleaned.to_csv(
        output_path,
        index=False,
        date_format="%Y-%m-%d",
    )
    print_summary(summary)
    print(f"Saved privately: {output_path.relative_to(PROJECT_ROOT)}")

    return summary


def main() -> int:
    """Run the complete handbook Weeks 4–5 cleaning workflow."""

    for dataset in ("listings", "sold"):
        process_dataset(dataset)

    print("\nWEEKS 4–5 CLEANING AND PREPARATION COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
