"""Week 6 feature engineering for the sold Residential dataset.

This module is being built one approved metric at a time. The first two
metrics were defined with the analyst before coding:

    close_to_original_list_ratio = ClosePrice / OriginalListPrice
    close_price_per_sqft = ClosePrice / LivingArea

Each metric is calculated only when its numerator and denominator are present
and greater than zero. Otherwise, the result remains missing. Console output
is aggregate-only and never displays confidential MLS records.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

INPUT_FILE = PROCESSED_DIR / "analysis_ready_sold_residential.csv"
OUTPUT_FILE = PROCESSED_DIR / "market_metrics_sold_residential.csv"
DISTRICT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "DistrictArea2425"
    / "DistrictAreas2425.shp"
)
SEGMENT_OUTPUT_FILES = {
    "PropertySubType": PROCESSED_DIR / "week6_segment_property_subtype.csv",
    "CountyOrParish": PROCESSED_DIR / "week6_segment_county.csv",
    "MLSAreaMajor": PROCESSED_DIR / "week6_segment_mls_area.csv",
}
MIN_SEGMENT_RECORDS = 100

EXPECTED_ROWS = 495_334
EXPECTED_SOURCE_MONTHS = 33

RATIO_COLUMN = "close_to_original_list_ratio"
PPSF_COLUMN = "close_price_per_sqft"
CLOSE_YEAR_COLUMN = "close_year"
CLOSE_MONTH_COLUMN = "close_month"
LISTING_TO_CONTRACT_COLUMN = "listing_to_contract_days"
CONTRACT_TO_CLOSE_COLUMN = "contract_to_close_days"
DISTRICT_OUTPUT_COLUMNS = {
    "Elementary": (
        "elementary_district_name",
        "elementary_district_code",
    ),
    "High": (
        "high_district_name",
        "high_district_code",
    ),
    "Unified": (
        "unified_district_name",
        "unified_district_code",
    ),
}
SCHOOL_DISTRICT_COLUMNS = tuple(
    column
    for output_pair in DISTRICT_OUTPUT_COLUMNS.values()
    for column in output_pair
)

METRIC_SPECIFICATION = {
    "metric": RATIO_COLUMN,
    "formula": "ClosePrice / OriginalListPrice",
    "validity_rule": (
        "ClosePrice and OriginalListPrice must both be present and > 0"
    ),
    "invalid_treatment": "Leave the result missing",
    "interpretation": (
        "Below 1 = sold below original list; "
        "1 = sold at original list; "
        "above 1 = sold above original list"
    ),
    "primary_dataset": "sold",
}

PPSF_SPECIFICATION = {
    "metric": PPSF_COLUMN,
    "formula": "ClosePrice / LivingArea",
    "validity_rule": "ClosePrice and LivingArea must both be present and > 0",
    "invalid_treatment": "Leave the result missing",
    "interpretation": (
        "The transaction's close price per square foot of living area; "
        "higher values are descriptive and do not establish why the "
        "property or area commands a higher price"
    ),
    "primary_dataset": "sold",
}

DOM_SPECIFICATION = {
    "metric": "DaysOnMarket",
    "formula": "Use the existing DaysOnMarket field; no duplicate column",
    "validity_rule": "DaysOnMarket must be present and >= 0",
    "invalid_treatment": (
        "Preserve the record and existing invalid flag; exclude the value "
        "from metric summaries"
    ),
    "interpretation": "Time-to-sell indicator; zero is valid",
    "primary_dataset": "sold",
}

TIME_SPECIFICATION = {
    "metric": "Close year / month / year-month",
    "source": "CloseDate",
    "created_columns": [CLOSE_YEAR_COLUMN, CLOSE_MONTH_COLUMN],
    "reused_column": "year_month",
    "validity_rule": "CloseDate must parse as a valid date",
    "invalid_treatment": "Leave derived time fields missing",
    "interpretation": "Enables chronological monthly trend analysis",
    "primary_dataset": "sold",
}

LISTING_TO_CONTRACT_SPECIFICATION = {
    "metric": LISTING_TO_CONTRACT_COLUMN,
    "formula": "PurchaseContractDate - ListingContractDate",
    "validity_rule": (
        "Both dates must be present and PurchaseContractDate must be on or "
        "after ListingContractDate"
    ),
    "invalid_treatment": (
        "Preserve the record and existing negative timeline flag; leave the "
        "metric missing"
    ),
    "interpretation": "Time from listing to an accepted purchase offer",
    "primary_dataset": "sold",
}

CONTRACT_TO_CLOSE_SPECIFICATION = {
    "metric": CONTRACT_TO_CLOSE_COLUMN,
    "formula": "CloseDate - PurchaseContractDate",
    "validity_rule": (
        "Both dates must be present and CloseDate must be on or after "
        "PurchaseContractDate"
    ),
    "invalid_treatment": (
        "Preserve the record and existing purchase-after-close flag; leave "
        "the metric missing"
    ),
    "interpretation": (
        "Time for the full closing process after an accepted purchase offer"
    ),
    "primary_dataset": "sold",
}

SCHOOL_DISTRICT_SPECIFICATION = {
    "metric": "California school district enrichment",
    "source": "California School District Areas 2024-25",
    "method": "Point-in-polygon intersection using Latitude and Longitude",
    "validity_rule": "The existing invalid_coordinates_flag must be false",
    "invalid_treatment": "Preserve the record and leave district fields missing",
    "output_columns": SCHOOL_DISTRICT_COLUMNS,
    "primary_dataset": "sold",
}


def validate_input(frame: pd.DataFrame) -> None:
    """Confirm that the Weeks 4–5 sold output is the expected input."""

    if len(frame) != EXPECTED_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_ROWS:,} sold rows, found {len(frame):,}"
        )

    required_columns = {
        "ClosePrice",
        "OriginalListPrice",
        "LivingArea",
        "DaysOnMarket",
        "invalid_days_on_market_flag",
        "CloseDate",
        "ListingContractDate",
        "PurchaseContractDate",
        "negative_timeline_flag",
        "purchase_after_close_flag",
        "Latitude",
        "Longitude",
        "invalid_coordinates_flag",
        "year_month",
        "missing_required_date_flag",
        "PropertyType",
        "_source_month",
    }
    missing_columns = sorted(required_columns - set(frame.columns))
    if missing_columns:
        raise ValueError(
            f"Required columns are missing: {missing_columns}"
        )

    existing_week6_columns = {
        RATIO_COLUMN,
        PPSF_COLUMN,
        CLOSE_YEAR_COLUMN,
        CLOSE_MONTH_COLUMN,
        LISTING_TO_CONTRACT_COLUMN,
        CONTRACT_TO_CLOSE_COLUMN,
        *SCHOOL_DISTRICT_COLUMNS,
    } & set(frame.columns)
    if existing_week6_columns:
        raise ValueError(
            "Input already contains Week 6 columns: "
            f"{sorted(existing_week6_columns)}; use the clean Weeks 4–5 "
            "sold dataset as input"
        )

    non_residential = frame["PropertyType"].ne("Residential").sum()
    if non_residential:
        raise ValueError(
            f"Found {non_residential:,} non-Residential records"
        )

    source_months = frame["_source_month"].nunique(dropna=True)
    if source_months != EXPECTED_SOURCE_MONTHS:
        raise ValueError(
            f"Expected {EXPECTED_SOURCE_MONTHS} source months, "
            f"found {source_months}"
        )


def add_close_to_original_list_ratio(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Add the approved close-to-original-list ratio and audit results."""

    validate_input(frame)
    featured = frame.copy()

    close_price = pd.to_numeric(featured["ClosePrice"], errors="coerce")
    original_list_price = pd.to_numeric(
        featured["OriginalListPrice"],
        errors="coerce",
    )

    valid = (
        close_price.notna()
        & original_list_price.notna()
        & close_price.gt(0)
        & original_list_price.gt(0)
    )

    featured[RATIO_COLUMN] = float("nan")
    featured.loc[valid, RATIO_COLUMN] = (
        close_price.loc[valid] / original_list_price.loc[valid]
    )

    below_original = valid & close_price.lt(original_list_price)
    at_original = valid & close_price.eq(original_list_price)
    above_original = valid & close_price.gt(original_list_price)

    ratios = featured.loc[valid, RATIO_COLUMN]
    summary: dict[str, object] = {
        "total_records": len(featured),
        "eligible_records": int(valid.sum()),
        "ineligible_records": int((~valid).sum()),
        "missing_close_price": int(close_price.isna().sum()),
        "nonpositive_close_price": int(
            (close_price.notna() & close_price.le(0)).sum()
        ),
        "missing_original_list_price": int(
            original_list_price.isna().sum()
        ),
        "nonpositive_original_list_price": int(
            (
                original_list_price.notna()
                & original_list_price.le(0)
            ).sum()
        ),
        "sold_below_original_list": int(below_original.sum()),
        "sold_at_original_list": int(at_original.sum()),
        "sold_above_original_list": int(above_original.sum()),
        "ratio_mean": float(ratios.mean()),
        "ratio_median": float(ratios.median()),
        "ratio_percentile_01": float(ratios.quantile(0.01)),
        "ratio_percentile_25": float(ratios.quantile(0.25)),
        "ratio_percentile_75": float(ratios.quantile(0.75)),
        "ratio_percentile_99": float(ratios.quantile(0.99)),
        "ratio_minimum": float(ratios.min()),
        "ratio_maximum": float(ratios.max()),
    }

    if len(featured) != len(frame):
        raise ValueError("Feature engineering changed the row count")

    if featured.loc[~valid, RATIO_COLUMN].notna().any():
        raise ValueError("Ineligible records received ratio values")

    if featured.loc[valid, RATIO_COLUMN].isna().any():
        raise ValueError("Eligible records are missing ratio values")

    outcome_total = (
        summary["sold_below_original_list"]
        + summary["sold_at_original_list"]
        + summary["sold_above_original_list"]
    )
    if outcome_total != summary["eligible_records"]:
        raise ValueError(
            "Below/at/above outcome counts do not equal eligible records"
        )

    return featured, summary


def add_close_price_per_sqft(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Add close price per square foot using positive, non-missing inputs."""

    if PPSF_COLUMN in frame.columns:
        raise ValueError(f"Input already contains {PPSF_COLUMN}")

    featured = frame.copy()
    close_price = pd.to_numeric(featured["ClosePrice"], errors="coerce")
    living_area = pd.to_numeric(featured["LivingArea"], errors="coerce")

    valid = (
        close_price.notna()
        & living_area.notna()
        & close_price.gt(0)
        & living_area.gt(0)
    )

    featured[PPSF_COLUMN] = float("nan")
    featured.loc[valid, PPSF_COLUMN] = (
        close_price.loc[valid] / living_area.loc[valid]
    )

    values = featured.loc[valid, PPSF_COLUMN]
    summary: dict[str, object] = {
        "ppsf_eligible_records": int(valid.sum()),
        "ppsf_ineligible_records": int((~valid).sum()),
        "ppsf_missing_close_price": int(close_price.isna().sum()),
        "ppsf_nonpositive_close_price": int(
            (close_price.notna() & close_price.le(0)).sum()
        ),
        "ppsf_missing_living_area": int(living_area.isna().sum()),
        "ppsf_nonpositive_living_area": int(
            (living_area.notna() & living_area.le(0)).sum()
        ),
        "ppsf_mean": float(values.mean()),
        "ppsf_median": float(values.median()),
        "ppsf_percentile_01": float(values.quantile(0.01)),
        "ppsf_percentile_25": float(values.quantile(0.25)),
        "ppsf_percentile_75": float(values.quantile(0.75)),
        "ppsf_percentile_99": float(values.quantile(0.99)),
        "ppsf_minimum": float(values.min()),
        "ppsf_maximum": float(values.max()),
    }

    if len(featured) != len(frame):
        raise ValueError("PPSF feature engineering changed the row count")
    if featured.loc[~valid, PPSF_COLUMN].notna().any():
        raise ValueError("Ineligible records received PPSF values")
    if featured.loc[valid, PPSF_COLUMN].isna().any():
        raise ValueError("Eligible records are missing PPSF values")

    return featured, summary


def summarize_days_on_market(frame: pd.DataFrame) -> dict[str, object]:
    """Validate and summarize the existing nonnegative DaysOnMarket field."""

    raw_days = frame["DaysOnMarket"]
    days = pd.to_numeric(raw_days, errors="coerce")
    coercion_failures = int((raw_days.notna() & days.isna()).sum())
    if coercion_failures:
        raise ValueError(
            f"DaysOnMarket has {coercion_failures:,} numeric coercion failures"
        )

    negative = days.notna() & days.lt(0)
    existing_flag = (
        frame["invalid_days_on_market_flag"].fillna(False).astype(bool)
    )
    if not existing_flag.equals(negative):
        mismatch_count = int((existing_flag != negative).sum())
        raise ValueError(
            "Existing invalid_days_on_market_flag disagrees with the "
            f"DaysOnMarket rule for {mismatch_count:,} records"
        )

    valid = days.notna() & days.ge(0)
    values = days.loc[valid]
    return {
        "dom_eligible_records": int(valid.sum()),
        "dom_ineligible_records": int((~valid).sum()),
        "dom_missing_records": int(days.isna().sum()),
        "dom_negative_records": int(negative.sum()),
        "dom_zero_records": int(days.eq(0).sum()),
        "dom_mean": float(values.mean()),
        "dom_median": float(values.median()),
        "dom_percentile_01": float(values.quantile(0.01)),
        "dom_percentile_25": float(values.quantile(0.25)),
        "dom_percentile_75": float(values.quantile(0.75)),
        "dom_percentile_99": float(values.quantile(0.99)),
        "dom_minimum": float(values.min()),
        "dom_maximum": float(values.max()),
    }


def add_close_time_fields(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Derive close year and month and validate the existing year_month."""

    created = {CLOSE_YEAR_COLUMN, CLOSE_MONTH_COLUMN} & set(frame.columns)
    if created:
        raise ValueError(f"Input already contains time fields: {sorted(created)}")

    featured = frame.copy()
    raw_close_date = featured["CloseDate"]
    close_date = pd.to_datetime(raw_close_date, errors="coerce")
    nonblank = raw_close_date.notna() & raw_close_date.astype(str).str.strip().ne("")
    parse_error = nonblank & close_date.isna()
    if parse_error.any():
        raise ValueError(
            f"CloseDate has {int(parse_error.sum()):,} parse failures"
        )

    missing = close_date.isna()
    existing_missing_flag = (
        featured["missing_required_date_flag"].fillna(False).astype(bool)
    )
    if not existing_missing_flag.equals(missing):
        mismatch_count = int((existing_missing_flag != missing).sum())
        raise ValueError(
            "missing_required_date_flag disagrees with CloseDate for "
            f"{mismatch_count:,} records"
        )

    expected_year_month = close_date.dt.strftime("%Y-%m").astype("string")
    existing_year_month = featured["year_month"].astype("string")
    year_month_mismatch = ~(
        existing_year_month.eq(expected_year_month)
        | (existing_year_month.isna() & expected_year_month.isna())
    )
    if year_month_mismatch.any():
        raise ValueError(
            "Existing year_month disagrees with CloseDate for "
            f"{int(year_month_mismatch.sum()):,} records"
        )

    featured[CLOSE_YEAR_COLUMN] = close_date.dt.year.astype("Int64")
    featured[CLOSE_MONTH_COLUMN] = close_date.dt.month.astype("Int64")

    valid = close_date.notna()
    valid_year_month = expected_year_month.loc[valid]
    summary: dict[str, object] = {
        "time_eligible_records": int(valid.sum()),
        "time_ineligible_records": int((~valid).sum()),
        "time_missing_close_date": int(missing.sum()),
        "time_parse_errors": int(parse_error.sum()),
        "time_distinct_year_months": int(valid_year_month.nunique()),
        "time_first_year_month": str(valid_year_month.min()),
        "time_last_year_month": str(valid_year_month.max()),
    }

    return featured, summary


def add_listing_to_contract_days(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Add nonnegative days from listing to accepted purchase contract."""

    if LISTING_TO_CONTRACT_COLUMN in frame.columns:
        raise ValueError(
            f"Input already contains {LISTING_TO_CONTRACT_COLUMN}"
        )

    featured = frame.copy()
    raw_listing = featured["ListingContractDate"]
    raw_purchase = featured["PurchaseContractDate"]
    listing = pd.to_datetime(raw_listing, errors="coerce")
    purchase = pd.to_datetime(raw_purchase, errors="coerce")

    listing_nonblank = (
        raw_listing.notna() & raw_listing.astype(str).str.strip().ne("")
    )
    purchase_nonblank = (
        raw_purchase.notna() & raw_purchase.astype(str).str.strip().ne("")
    )
    listing_parse_error = listing_nonblank & listing.isna()
    purchase_parse_error = purchase_nonblank & purchase.isna()
    if listing_parse_error.any() or purchase_parse_error.any():
        raise ValueError(
            "Listing-to-contract inputs contain date parse failures"
        )

    both_present = listing.notna() & purchase.notna()
    negative = both_present & purchase.lt(listing)
    existing_flag = featured["negative_timeline_flag"].fillna(False).astype(bool)
    if not existing_flag.equals(negative):
        mismatch_count = int((existing_flag != negative).sum())
        raise ValueError(
            "negative_timeline_flag disagrees with listing-to-contract "
            f"chronology for {mismatch_count:,} records"
        )

    valid = both_present & ~negative
    day_difference = (purchase - listing).dt.days
    featured[LISTING_TO_CONTRACT_COLUMN] = pd.Series(
        pd.NA,
        index=featured.index,
        dtype="Int64",
    )
    featured.loc[valid, LISTING_TO_CONTRACT_COLUMN] = day_difference.loc[valid]

    values = featured.loc[valid, LISTING_TO_CONTRACT_COLUMN].astype("float64")
    summary: dict[str, object] = {
        "ltc_eligible_records": int(valid.sum()),
        "ltc_ineligible_records": int((~valid).sum()),
        "ltc_missing_listing_date": int(listing.isna().sum()),
        "ltc_missing_purchase_date": int(purchase.isna().sum()),
        "ltc_negative_records": int(negative.sum()),
        "ltc_zero_day_records": int(values.eq(0).sum()),
        "ltc_mean": float(values.mean()),
        "ltc_median": float(values.median()),
        "ltc_percentile_01": float(values.quantile(0.01)),
        "ltc_percentile_25": float(values.quantile(0.25)),
        "ltc_percentile_75": float(values.quantile(0.75)),
        "ltc_percentile_99": float(values.quantile(0.99)),
        "ltc_minimum": float(values.min()),
        "ltc_maximum": float(values.max()),
    }

    if featured.loc[~valid, LISTING_TO_CONTRACT_COLUMN].notna().any():
        raise ValueError("Ineligible records received listing-to-contract days")
    if featured.loc[valid, LISTING_TO_CONTRACT_COLUMN].isna().any():
        raise ValueError("Eligible records are missing listing-to-contract days")

    return featured, summary


def add_contract_to_close_days(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Add nonnegative days from accepted contract to completed closing."""

    if CONTRACT_TO_CLOSE_COLUMN in frame.columns:
        raise ValueError(f"Input already contains {CONTRACT_TO_CLOSE_COLUMN}")

    featured = frame.copy()
    raw_purchase = featured["PurchaseContractDate"]
    raw_close = featured["CloseDate"]
    purchase = pd.to_datetime(raw_purchase, errors="coerce")
    close = pd.to_datetime(raw_close, errors="coerce")

    purchase_nonblank = (
        raw_purchase.notna() & raw_purchase.astype(str).str.strip().ne("")
    )
    close_nonblank = raw_close.notna() & raw_close.astype(str).str.strip().ne("")
    purchase_parse_error = purchase_nonblank & purchase.isna()
    close_parse_error = close_nonblank & close.isna()
    if purchase_parse_error.any() or close_parse_error.any():
        raise ValueError("Contract-to-close inputs contain date parse failures")

    both_present = purchase.notna() & close.notna()
    negative = both_present & close.lt(purchase)
    existing_flag = (
        featured["purchase_after_close_flag"].fillna(False).astype(bool)
    )
    if not existing_flag.equals(negative):
        mismatch_count = int((existing_flag != negative).sum())
        raise ValueError(
            "purchase_after_close_flag disagrees with contract-to-close "
            f"chronology for {mismatch_count:,} records"
        )

    valid = both_present & ~negative
    day_difference = (close - purchase).dt.days
    featured[CONTRACT_TO_CLOSE_COLUMN] = pd.Series(
        pd.NA,
        index=featured.index,
        dtype="Int64",
    )
    featured.loc[valid, CONTRACT_TO_CLOSE_COLUMN] = day_difference.loc[valid]

    values = featured.loc[valid, CONTRACT_TO_CLOSE_COLUMN].astype("float64")
    summary: dict[str, object] = {
        "ctc_eligible_records": int(valid.sum()),
        "ctc_ineligible_records": int((~valid).sum()),
        "ctc_missing_purchase_date": int(purchase.isna().sum()),
        "ctc_missing_close_date": int(close.isna().sum()),
        "ctc_negative_records": int(negative.sum()),
        "ctc_zero_day_records": int(values.eq(0).sum()),
        "ctc_mean": float(values.mean()),
        "ctc_median": float(values.median()),
        "ctc_percentile_01": float(values.quantile(0.01)),
        "ctc_percentile_25": float(values.quantile(0.25)),
        "ctc_percentile_75": float(values.quantile(0.75)),
        "ctc_percentile_99": float(values.quantile(0.99)),
        "ctc_minimum": float(values.min()),
        "ctc_maximum": float(values.max()),
    }

    if featured.loc[~valid, CONTRACT_TO_CLOSE_COLUMN].notna().any():
        raise ValueError("Ineligible records received contract-to-close days")
    if featured.loc[valid, CONTRACT_TO_CLOSE_COLUMN].isna().any():
        raise ValueError("Eligible records are missing contract-to-close days")

    return featured, summary


def build_school_district_matches(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Build district assignments without changing the input frame."""

    if not DISTRICT_FILE.exists():
        raise FileNotFoundError(
            f"Required district shapefile does not exist: {DISTRICT_FILE}"
        )

    districts = gpd.read_file(DISTRICT_FILE)
    required_district_fields = {
        "CDCode",
        "DistrictNa",
        "DistrictTy",
        "geometry",
    }
    missing_district_fields = sorted(
        required_district_fields - set(districts.columns)
    )
    if missing_district_fields:
        raise ValueError(
            "District shapefile is missing fields: "
            f"{missing_district_fields}"
        )
    if districts.crs is None:
        raise ValueError("District shapefile has no coordinate reference system")

    invalid_geometry_before = int((~districts.geometry.is_valid).sum())
    districts = districts.copy()
    districts["geometry"] = districts.geometry.make_valid()
    invalid_geometry_after = int((~districts.geometry.is_valid).sum())
    if invalid_geometry_after:
        raise ValueError(
            f"District shapefile retains {invalid_geometry_after} invalid geometries"
        )

    assignments = pd.DataFrame(
        pd.NA,
        index=frame.index,
        columns=SCHOOL_DISTRICT_COLUMNS,
        dtype="string",
    )
    latitude = pd.to_numeric(frame["Latitude"], errors="coerce")
    longitude = pd.to_numeric(frame["Longitude"], errors="coerce")
    invalid_coordinates = (
        frame["invalid_coordinates_flag"].fillna(True).astype(bool)
    )
    coordinate_eligible = ~invalid_coordinates
    if (
        latitude.loc[coordinate_eligible].isna().any()
        or longitude.loc[coordinate_eligible].isna().any()
    ):
        raise ValueError("Coordinate-eligible records contain missing coordinates")

    eligible_index = frame.index[coordinate_eligible]
    points = gpd.GeoDataFrame(
        {"_row_id": eligible_index.to_numpy()},
        geometry=gpd.points_from_xy(
            longitude.loc[eligible_index],
            latitude.loc[eligible_index],
            crs="EPSG:4326",
        ),
        index=eligible_index,
        crs="EPSG:4326",
    ).to_crs(districts.crs)

    matched_by_type: dict[str, set[int]] = {}
    summary: dict[str, object] = {
        "school_district_rows": len(districts),
        "school_invalid_geometry_before": invalid_geometry_before,
        "school_invalid_geometry_after": invalid_geometry_after,
        "school_coordinate_eligible_records": int(coordinate_eligible.sum()),
        "school_invalid_coordinate_records": int(invalid_coordinates.sum()),
    }

    for district_type, (name_column, code_column) in (
        DISTRICT_OUTPUT_COLUMNS.items()
    ):
        district_subset = districts.loc[
            districts["DistrictTy"].eq(district_type),
            ["CDCode", "DistrictNa", "geometry"],
        ]
        joined = gpd.sjoin(
            points,
            district_subset,
            how="inner",
            predicate="intersects",
        )
        match_counts = joined.groupby("_row_id").size()
        unique_ids = set(match_counts.index[match_counts.eq(1)])
        ambiguous_ids = set(match_counts.index[match_counts.gt(1)])
        matched_by_type[district_type] = set(match_counts.index)

        unique_matches = joined.loc[
            joined["_row_id"].isin(unique_ids),
            ["_row_id", "DistrictNa", "CDCode"],
        ].set_index("_row_id")
        assignments.loc[unique_matches.index, name_column] = (
            unique_matches["DistrictNa"].astype("string").to_numpy()
        )
        assignments.loc[unique_matches.index, code_column] = (
            unique_matches["CDCode"].astype("string").to_numpy()
        )

        key = district_type.lower()
        summary[f"school_{key}_matched_records"] = len(unique_ids)
        summary[f"school_{key}_ambiguous_records"] = len(ambiguous_ids)
        summary[f"school_{key}_unmatched_eligible_records"] = (
            len(points) - len(match_counts)
        )
        summary[f"school_{key}_distinct_districts"] = int(
            unique_matches["CDCode"].nunique()
        )

    any_match = set().union(*matched_by_type.values())
    unified = matched_by_type["Unified"]
    elementary_or_high = (
        matched_by_type["Elementary"] | matched_by_type["High"]
    )
    summary["school_any_matched_records"] = len(any_match)
    summary["school_unmatched_eligible_records"] = len(points) - len(any_match)
    summary["school_cross_type_overlap_records"] = len(
        unified & elementary_or_high
    )

    return assignments, summary


def add_school_district_fields(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Add separate elementary, high, and unified district name/code fields."""

    existing = set(SCHOOL_DISTRICT_COLUMNS) & set(frame.columns)
    if existing:
        raise ValueError(
            f"Input already contains school district fields: {sorted(existing)}"
        )

    featured = frame.copy()
    assignments, summary = build_school_district_matches(featured)
    for column in SCHOOL_DISTRICT_COLUMNS:
        featured[column] = assignments[column]

    if len(featured) != len(frame):
        raise ValueError("School district enrichment changed the row count")

    return featured, summary


def build_segment_summary(
    frame: pd.DataFrame,
    segment_column: str,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Create a denominator-aware median summary for one segment field."""

    if segment_column not in frame.columns:
        raise ValueError(f"Missing segment field: {segment_column}")

    segment = frame[segment_column].astype("string").str.strip()
    segment = segment.mask(segment.eq(""))
    close_price = pd.to_numeric(frame["ClosePrice"], errors="coerce")
    days_on_market = pd.to_numeric(frame["DaysOnMarket"], errors="coerce")

    analysis = pd.DataFrame(
        {
            "segment": segment,
            "valid_close_price": close_price.where(close_price.gt(0)),
            "valid_ratio": pd.to_numeric(
                frame[RATIO_COLUMN],
                errors="coerce",
            ),
            "valid_ppsf": pd.to_numeric(
                frame[PPSF_COLUMN],
                errors="coerce",
            ),
            "valid_days_on_market": days_on_market.where(
                days_on_market.ge(0)
            ),
            "valid_listing_to_contract_days": pd.to_numeric(
                frame[LISTING_TO_CONTRACT_COLUMN],
                errors="coerce",
            ),
            "valid_contract_to_close_days": pd.to_numeric(
                frame[CONTRACT_TO_CLOSE_COLUMN],
                errors="coerce",
            ),
        }
    )
    nonmissing = analysis.loc[analysis["segment"].notna()].copy()
    grouped = (
        nonmissing.groupby("segment", sort=False)
        .agg(
            records=("segment", "size"),
            valid_close_price_records=("valid_close_price", "count"),
            median_close_price=("valid_close_price", "median"),
            valid_ratio_records=("valid_ratio", "count"),
            median_close_to_original_ratio=("valid_ratio", "median"),
            valid_ppsf_records=("valid_ppsf", "count"),
            median_close_price_per_sqft=("valid_ppsf", "median"),
            valid_days_on_market_records=(
                "valid_days_on_market",
                "count",
            ),
            median_days_on_market=("valid_days_on_market", "median"),
            valid_listing_to_contract_records=(
                "valid_listing_to_contract_days",
                "count",
            ),
            median_listing_to_contract_days=(
                "valid_listing_to_contract_days",
                "median",
            ),
            valid_contract_to_close_records=(
                "valid_contract_to_close_days",
                "count",
            ),
            median_contract_to_close_days=(
                "valid_contract_to_close_days",
                "median",
            ),
        )
        .reset_index()
    )
    grouped["share_of_all_records_percent"] = (
        grouped["records"] / len(frame) * 100
    )
    qualifying = (
        grouped.loc[grouped["records"].ge(MIN_SEGMENT_RECORDS)]
        .sort_values(["records", "segment"], ascending=[False, True])
        .reset_index(drop=True)
    )
    qualifying.insert(0, "segment_field", segment_column)

    slug = {
        "PropertySubType": "property_subtype",
        "CountyOrParish": "county",
        "MLSAreaMajor": "mls_area",
    }[segment_column]
    not_defined = segment.str.contains(
        "not defined",
        case=False,
        na=False,
    )
    metadata: dict[str, object] = {
        f"segment_{slug}_distinct_values": int(segment.nunique(dropna=True)),
        f"segment_{slug}_missing_records": int(segment.isna().sum()),
        f"segment_{slug}_not_defined_records": int(not_defined.sum()),
        f"segment_{slug}_qualifying_groups": len(qualifying),
        f"segment_{slug}_qualifying_records": int(qualifying["records"].sum()),
        f"segment_{slug}_below_threshold_groups": int(
            grouped["records"].lt(MIN_SEGMENT_RECORDS).sum()
        ),
    }
    return qualifying, metadata


def build_segment_summaries(
    frame: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], dict[str, object]]:
    """Build the three analyst-approved Week 6 segment tables."""

    tables: dict[str, pd.DataFrame] = {}
    metadata: dict[str, object] = {}
    for segment_column in SEGMENT_OUTPUT_FILES:
        table, table_metadata = build_segment_summary(frame, segment_column)
        tables[segment_column] = table
        metadata.update(table_metadata)
    return tables, metadata


def save_and_validate_segment_summaries(
    tables: dict[str, pd.DataFrame],
) -> None:
    """Save private segment tables and validate their structure after reload."""

    for segment_column, table in tables.items():
        output_path = SEGMENT_OUTPUT_FILES[segment_column]
        table.to_csv(output_path, index=False)
        saved = pd.read_csv(output_path, dtype={"segment": "string"})
        if len(saved) != len(table):
            raise ValueError(
                f"Saved {segment_column} summary row count changed"
            )
        if set(saved.columns) != set(table.columns):
            raise ValueError(
                f"Saved {segment_column} summary columns changed"
            )
        if saved["records"].lt(MIN_SEGMENT_RECORDS).any():
            raise ValueError(
                f"Saved {segment_column} summary contains low-volume groups"
            )
        if saved["segment"].isna().any():
            raise ValueError(
                f"Saved {segment_column} summary contains missing labels"
            )
        print(
            "Saved private segment table: "
            f"{output_path.relative_to(PROJECT_ROOT)}"
        )


def print_segment_summary(summary: dict[str, object]) -> None:
    """Print aggregate coverage for the three approved segment tables."""

    print(f"\nSEGMENTED SUMMARIES (minimum {MIN_SEGMENT_RECORDS} records)")
    for label, slug in (
        ("PropertySubType", "property_subtype"),
        ("CountyOrParish", "county"),
        ("MLSAreaMajor", "mls_area"),
    ):
        print(
            f"  {label}: "
            f"{summary[f'segment_{slug}_distinct_values']:,} distinct; "
            f"{summary[f'segment_{slug}_missing_records']:,} missing; "
            f"{summary[f'segment_{slug}_qualifying_groups']:,} groups meet "
            "the threshold"
        )
        if label == "MLSAreaMajor":
            print(
                "    Not Defined records: "
                f"{summary['segment_mls_area_not_defined_records']:,}"
            )


def print_summary(summary: dict[str, object]) -> None:
    """Print aggregate eligibility, outcomes, and distribution statistics."""

    total = int(summary["total_records"])
    eligible = int(summary["eligible_records"])

    print("CLOSE-TO-ORIGINAL-LIST RATIO")
    print(f"Formula: {METRIC_SPECIFICATION['formula']}")
    print(f"Total sold records: {total:,}")
    print(
        f"Eligible records: {eligible:,} "
        f"({eligible / total * 100:.2f}%)"
    )
    print(f"Ineligible records: {summary['ineligible_records']:,}")
    print("Ineligibility reasons (categories can overlap):")
    print(f"  Missing ClosePrice: {summary['missing_close_price']:,}")
    print(
        "  Nonpositive ClosePrice: "
        f"{summary['nonpositive_close_price']:,}"
    )
    print(
        "  Missing OriginalListPrice: "
        f"{summary['missing_original_list_price']:,}"
    )
    print(
        "  Nonpositive OriginalListPrice: "
        f"{summary['nonpositive_original_list_price']:,}"
    )

    print("Sale outcomes relative to original list price:")
    for label, key in (
        ("Below", "sold_below_original_list"),
        ("At", "sold_at_original_list"),
        ("Above", "sold_above_original_list"),
    ):
        count = int(summary[key])
        print(f"  {label}: {count:,} ({count / eligible * 100:.2f}%)")

    print("Ratio distribution:")
    print(f"  Mean: {summary['ratio_mean']:.4f}")
    print(f"  Median: {summary['ratio_median']:.4f}")
    print(
        f"  1st–99th percentile: "
        f"{summary['ratio_percentile_01']:.4f} to "
        f"{summary['ratio_percentile_99']:.4f}"
    )
    print(
        f"  Full range: {summary['ratio_minimum']:.4f} to "
        f"{summary['ratio_maximum']:.4f}"
    )

    ppsf_eligible = int(summary["ppsf_eligible_records"])
    print("\nCLOSE PRICE PER SQUARE FOOT")
    print(f"Formula: {PPSF_SPECIFICATION['formula']}")
    print(
        f"Eligible records: {ppsf_eligible:,} "
        f"({ppsf_eligible / total * 100:.2f}%)"
    )
    print(f"Ineligible records: {summary['ppsf_ineligible_records']:,}")
    print("Ineligibility reasons (categories can overlap):")
    print(f"  Missing ClosePrice: {summary['ppsf_missing_close_price']:,}")
    print(
        "  Nonpositive ClosePrice: "
        f"{summary['ppsf_nonpositive_close_price']:,}"
    )
    print(
        f"  Missing LivingArea: {summary['ppsf_missing_living_area']:,}"
    )
    print(
        "  Nonpositive LivingArea: "
        f"{summary['ppsf_nonpositive_living_area']:,}"
    )
    print("PPSF distribution:")
    print(f"  Mean: ${summary['ppsf_mean']:,.2f}")
    print(f"  Median: ${summary['ppsf_median']:,.2f}")
    print(
        "  1st–99th percentile: "
        f"${summary['ppsf_percentile_01']:,.2f} to "
        f"${summary['ppsf_percentile_99']:,.2f}"
    )
    print(
        f"  Full range: ${summary['ppsf_minimum']:,.2f} to "
        f"${summary['ppsf_maximum']:,.2f}"
    )

    dom_eligible = int(summary["dom_eligible_records"])
    print("\nDAYS ON MARKET")
    print(f"Method: {DOM_SPECIFICATION['formula']}")
    print(
        f"Eligible records: {dom_eligible:,} "
        f"({dom_eligible / total * 100:.2f}%)"
    )
    print(f"Ineligible records: {summary['dom_ineligible_records']:,}")
    print(f"  Missing DaysOnMarket: {summary['dom_missing_records']:,}")
    print(f"  Negative DaysOnMarket: {summary['dom_negative_records']:,}")
    print(f"Valid zero-day records: {summary['dom_zero_records']:,}")
    print("DaysOnMarket distribution for valid records:")
    print(f"  Mean: {summary['dom_mean']:,.2f} days")
    print(f"  Median: {summary['dom_median']:,.2f} days")
    print(
        "  1st–99th percentile: "
        f"{summary['dom_percentile_01']:,.2f} to "
        f"{summary['dom_percentile_99']:,.2f} days"
    )
    print(
        f"  Full range: {summary['dom_minimum']:,.2f} to "
        f"{summary['dom_maximum']:,.2f} days"
    )

    print("\nCLOSE-DATE TIME FIELDS")
    print("Created: close_year and close_month")
    print("Reused as YrMo: year_month")
    print(
        f"Eligible records: {summary['time_eligible_records']:,} "
        f"({summary['time_eligible_records'] / total * 100:.2f}%)"
    )
    print(f"Missing CloseDate: {summary['time_missing_close_date']:,}")
    print(f"CloseDate parse errors: {summary['time_parse_errors']:,}")
    print(
        f"Coverage: {summary['time_first_year_month']} through "
        f"{summary['time_last_year_month']} "
        f"({summary['time_distinct_year_months']:,} months)"
    )

    ltc_eligible = int(summary["ltc_eligible_records"])
    print("\nLISTING TO CONTRACT DAYS")
    print(f"Formula: {LISTING_TO_CONTRACT_SPECIFICATION['formula']}")
    print(
        f"Eligible records: {ltc_eligible:,} "
        f"({ltc_eligible / total * 100:.2f}%)"
    )
    print(f"Ineligible records: {summary['ltc_ineligible_records']:,}")
    print("Ineligibility reasons (categories can overlap):")
    print(
        "  Missing ListingContractDate: "
        f"{summary['ltc_missing_listing_date']:,}"
    )
    print(
        "  Missing PurchaseContractDate: "
        f"{summary['ltc_missing_purchase_date']:,}"
    )
    print(f"  Negative timeline: {summary['ltc_negative_records']:,}")
    print(f"Valid zero-day records: {summary['ltc_zero_day_records']:,}")
    print("Listing-to-contract distribution for valid records:")
    print(f"  Mean: {summary['ltc_mean']:,.2f} days")
    print(f"  Median: {summary['ltc_median']:,.2f} days")
    print(
        "  1st–99th percentile: "
        f"{summary['ltc_percentile_01']:,.2f} to "
        f"{summary['ltc_percentile_99']:,.2f} days"
    )
    print(
        f"  Full range: {summary['ltc_minimum']:,.2f} to "
        f"{summary['ltc_maximum']:,.2f} days"
    )

    ctc_eligible = int(summary["ctc_eligible_records"])
    print("\nCONTRACT TO CLOSE DAYS")
    print(f"Formula: {CONTRACT_TO_CLOSE_SPECIFICATION['formula']}")
    print(
        f"Eligible records: {ctc_eligible:,} "
        f"({ctc_eligible / total * 100:.2f}%)"
    )
    print(f"Ineligible records: {summary['ctc_ineligible_records']:,}")
    print("Ineligibility reasons (categories can overlap):")
    print(
        "  Missing PurchaseContractDate: "
        f"{summary['ctc_missing_purchase_date']:,}"
    )
    print(f"  Missing CloseDate: {summary['ctc_missing_close_date']:,}")
    print(f"  Negative timeline: {summary['ctc_negative_records']:,}")
    print(f"Valid zero-day records: {summary['ctc_zero_day_records']:,}")
    print("Contract-to-close distribution for valid records:")
    print(f"  Mean: {summary['ctc_mean']:,.2f} days")
    print(f"  Median: {summary['ctc_median']:,.2f} days")
    print(
        "  1st–99th percentile: "
        f"{summary['ctc_percentile_01']:,.2f} to "
        f"{summary['ctc_percentile_99']:,.2f} days"
    )
    print(
        f"  Full range: {summary['ctc_minimum']:,.2f} to "
        f"{summary['ctc_maximum']:,.2f} days"
    )

    print("\nSCHOOL DISTRICT ENRICHMENT")
    print(
        "Source polygons: "
        f"{summary['school_district_rows']:,}; repaired geometries: "
        f"{summary['school_invalid_geometry_before']:,}"
    )
    print(
        "Coordinate-eligible records: "
        f"{summary['school_coordinate_eligible_records']:,}"
    )
    print(
        "Invalid-coordinate records retained unmatched: "
        f"{summary['school_invalid_coordinate_records']:,}"
    )
    for label, key in (
        ("Elementary", "elementary"),
        ("High", "high"),
        ("Unified", "unified"),
    ):
        print(
            f"  {label}: {summary[f'school_{key}_matched_records']:,} "
            "unique matches; "
            f"{summary[f'school_{key}_ambiguous_records']:,} ambiguous"
        )
    print(
        "Coordinate-eligible records without any district match: "
        f"{summary['school_unmatched_eligible_records']:,}"
    )
    print(
        "Records with unified plus elementary/high matches preserved: "
        f"{summary['school_cross_type_overlap_records']:,}"
    )


def validate_saved_output(
    output_path: Path,
    expected_summary: dict[str, object],
) -> None:
    """Read back the saved metric and verify eligibility and calculation."""

    saved = pd.read_csv(
        output_path,
        usecols=[
            "ClosePrice",
            "OriginalListPrice",
            "LivingArea",
            "DaysOnMarket",
            "invalid_days_on_market_flag",
            "CloseDate",
            "year_month",
            "missing_required_date_flag",
            "ListingContractDate",
            "PurchaseContractDate",
            "negative_timeline_flag",
            "purchase_after_close_flag",
            LISTING_TO_CONTRACT_COLUMN,
            CONTRACT_TO_CLOSE_COLUMN,
            "Latitude",
            "Longitude",
            "invalid_coordinates_flag",
            *SCHOOL_DISTRICT_COLUMNS,
            CLOSE_YEAR_COLUMN,
            CLOSE_MONTH_COLUMN,
            RATIO_COLUMN,
            PPSF_COLUMN,
        ],
        dtype={column: "string" for column in SCHOOL_DISTRICT_COLUMNS},
        low_memory=False,
    )

    if len(saved) != EXPECTED_ROWS:
        raise ValueError(
            f"Saved output has {len(saved):,} rows, expected {EXPECTED_ROWS:,}"
        )

    close_price = pd.to_numeric(saved["ClosePrice"], errors="coerce")
    original_list_price = pd.to_numeric(
        saved["OriginalListPrice"],
        errors="coerce",
    )
    valid = (
        close_price.notna()
        & original_list_price.notna()
        & close_price.gt(0)
        & original_list_price.gt(0)
    )

    if int(valid.sum()) != expected_summary["eligible_records"]:
        raise ValueError("Saved output eligibility count changed")

    if saved.loc[~valid, RATIO_COLUMN].notna().any():
        raise ValueError("Saved output populated ineligible ratios")

    expected_ratio = (
        close_price.loc[valid] / original_list_price.loc[valid]
    )
    absolute_error = (
        saved.loc[valid, RATIO_COLUMN] - expected_ratio
    ).abs()
    relative_error = absolute_error / expected_ratio.abs().clip(lower=1)
    maximum_relative_error = relative_error.max()
    if maximum_relative_error > 1e-12:
        raise ValueError(
            "Saved ratio values differ from the formula; maximum relative "
            f"error is {maximum_relative_error}"
        )

    living_area = pd.to_numeric(saved["LivingArea"], errors="coerce")
    ppsf_valid = (
        close_price.notna()
        & living_area.notna()
        & close_price.gt(0)
        & living_area.gt(0)
    )

    if int(ppsf_valid.sum()) != expected_summary["ppsf_eligible_records"]:
        raise ValueError("Saved output PPSF eligibility count changed")

    if saved.loc[~ppsf_valid, PPSF_COLUMN].notna().any():
        raise ValueError("Saved output populated ineligible PPSF values")

    expected_ppsf = close_price.loc[ppsf_valid] / living_area.loc[ppsf_valid]
    ppsf_absolute_error = (
        saved.loc[ppsf_valid, PPSF_COLUMN] - expected_ppsf
    ).abs()
    ppsf_relative_error = (
        ppsf_absolute_error / expected_ppsf.abs().clip(lower=1)
    )
    maximum_ppsf_relative_error = ppsf_relative_error.max()
    if maximum_ppsf_relative_error > 1e-12:
        raise ValueError(
            "Saved PPSF values differ from the formula; maximum relative "
            f"error is {maximum_ppsf_relative_error}"
        )

    raw_days = saved["DaysOnMarket"]
    days = pd.to_numeric(raw_days, errors="coerce")
    if (raw_days.notna() & days.isna()).any():
        raise ValueError("Saved output DaysOnMarket has coercion failures")
    negative_days = days.notna() & days.lt(0)
    saved_dom_flag = (
        saved["invalid_days_on_market_flag"].fillna(False).astype(bool)
    )
    if not saved_dom_flag.equals(negative_days):
        raise ValueError("Saved DaysOnMarket values disagree with invalid flag")
    valid_days = days.notna() & days.ge(0)
    if int(valid_days.sum()) != expected_summary["dom_eligible_records"]:
        raise ValueError("Saved output DaysOnMarket eligibility count changed")

    raw_close_date = saved["CloseDate"]
    close_date = pd.to_datetime(raw_close_date, errors="coerce")
    nonblank_close_date = (
        raw_close_date.notna()
        & raw_close_date.astype(str).str.strip().ne("")
    )
    if (nonblank_close_date & close_date.isna()).any():
        raise ValueError("Saved output CloseDate has parse failures")
    expected_year = close_date.dt.year
    expected_month = close_date.dt.month
    saved_year = pd.to_numeric(saved[CLOSE_YEAR_COLUMN], errors="coerce")
    saved_month = pd.to_numeric(saved[CLOSE_MONTH_COLUMN], errors="coerce")
    year_matches = saved_year.eq(expected_year) | (
        saved_year.isna() & expected_year.isna()
    )
    month_matches = saved_month.eq(expected_month) | (
        saved_month.isna() & expected_month.isna()
    )
    if not year_matches.all():
        raise ValueError("Saved close_year disagrees with CloseDate")
    if not month_matches.all():
        raise ValueError("Saved close_month disagrees with CloseDate")
    expected_year_month = close_date.dt.strftime("%Y-%m").astype("string")
    saved_year_month = saved["year_month"].astype("string")
    year_month_mismatch = ~(
        saved_year_month.eq(expected_year_month)
        | (saved_year_month.isna() & expected_year_month.isna())
    )
    if year_month_mismatch.any():
        raise ValueError("Saved year_month disagrees with CloseDate")
    if int(close_date.notna().sum()) != expected_summary["time_eligible_records"]:
        raise ValueError("Saved output time-field eligibility count changed")

    listing = pd.to_datetime(saved["ListingContractDate"], errors="coerce")
    purchase = pd.to_datetime(saved["PurchaseContractDate"], errors="coerce")
    both_present = listing.notna() & purchase.notna()
    negative_timeline = both_present & purchase.lt(listing)
    valid_ltc = both_present & ~negative_timeline
    saved_negative_flag = (
        saved["negative_timeline_flag"].fillna(False).astype(bool)
    )
    if not saved_negative_flag.equals(negative_timeline):
        raise ValueError("Saved dates disagree with negative_timeline_flag")
    if int(valid_ltc.sum()) != expected_summary["ltc_eligible_records"]:
        raise ValueError("Saved listing-to-contract eligibility count changed")
    if saved.loc[~valid_ltc, LISTING_TO_CONTRACT_COLUMN].notna().any():
        raise ValueError("Saved output populated ineligible listing-to-contract days")
    expected_ltc = (purchase - listing).dt.days
    saved_ltc = pd.to_numeric(
        saved[LISTING_TO_CONTRACT_COLUMN],
        errors="coerce",
    )
    ltc_matches = saved_ltc.eq(expected_ltc) | (
        saved_ltc.isna() & expected_ltc.isna()
    )
    if not ltc_matches.loc[valid_ltc].all():
        raise ValueError("Saved listing-to-contract values differ from formula")

    valid_ctc = purchase.notna() & close_date.notna() & close_date.ge(purchase)
    negative_ctc = purchase.notna() & close_date.notna() & close_date.lt(purchase)
    saved_purchase_after_close = (
        saved["purchase_after_close_flag"].fillna(False).astype(bool)
    )
    if not saved_purchase_after_close.equals(negative_ctc):
        raise ValueError("Saved dates disagree with purchase_after_close_flag")
    if int(valid_ctc.sum()) != expected_summary["ctc_eligible_records"]:
        raise ValueError("Saved contract-to-close eligibility count changed")
    if saved.loc[~valid_ctc, CONTRACT_TO_CLOSE_COLUMN].notna().any():
        raise ValueError("Saved output populated ineligible contract-to-close days")
    expected_ctc = (close_date - purchase).dt.days
    saved_ctc = pd.to_numeric(saved[CONTRACT_TO_CLOSE_COLUMN], errors="coerce")
    ctc_matches = saved_ctc.eq(expected_ctc) | (
        saved_ctc.isna() & expected_ctc.isna()
    )
    if not ctc_matches.loc[valid_ctc].all():
        raise ValueError("Saved contract-to-close values differ from formula")

    expected_districts, district_summary = build_school_district_matches(saved)
    for column in SCHOOL_DISTRICT_COLUMNS:
        actual = saved[column].astype("string")
        expected = expected_districts[column].astype("string")
        matches = actual.eq(expected) | (actual.isna() & expected.isna())
        if not matches.all():
            raise ValueError(
                f"Saved {column} differs from the spatial match for "
                f"{int((~matches).sum()):,} records"
            )
    district_summary_keys = (
        "school_coordinate_eligible_records",
        "school_invalid_coordinate_records",
        "school_elementary_matched_records",
        "school_high_matched_records",
        "school_unified_matched_records",
        "school_unmatched_eligible_records",
        "school_cross_type_overlap_records",
    )
    for key in district_summary_keys:
        if district_summary[key] != expected_summary[key]:
            raise ValueError(f"Saved district summary changed for {key}")

    print("Saved-output validation passed.")


def process_sold_dataset() -> dict[str, object]:
    """Load, engineer, save, and validate the current Week 6 metrics."""

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Required input does not exist: {INPUT_FILE}")

    print(f"Input: {INPUT_FILE.relative_to(PROJECT_ROOT)}")
    frame = pd.read_csv(INPUT_FILE, low_memory=False)
    featured, summary = add_close_to_original_list_ratio(frame)
    featured, ppsf_summary = add_close_price_per_sqft(featured)
    summary.update(ppsf_summary)
    summary.update(summarize_days_on_market(featured))
    featured, time_summary = add_close_time_fields(featured)
    summary.update(time_summary)
    featured, ltc_summary = add_listing_to_contract_days(featured)
    summary.update(ltc_summary)
    featured, ctc_summary = add_contract_to_close_days(featured)
    summary.update(ctc_summary)
    featured, district_summary = add_school_district_fields(featured)
    summary.update(district_summary)
    segment_tables, segment_summary = build_segment_summaries(featured)
    summary.update(segment_summary)

    featured.to_csv(OUTPUT_FILE, index=False)
    print_summary(summary)
    print_segment_summary(summary)
    print(f"Saved privately: {OUTPUT_FILE.relative_to(PROJECT_ROOT)}")

    validate_saved_output(OUTPUT_FILE, summary)
    save_and_validate_segment_summaries(segment_tables)
    return summary


def main() -> int:
    """Run the currently approved Week 6 feature-engineering workflow."""

    process_sold_dataset()
    print("\nWEEK 6 FEATURE ENGINEERING WORKFLOW COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
