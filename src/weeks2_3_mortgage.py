"""Weeks 2–3: enrich Residential MLS datasets with mortgage rates.

Fetch the public FRED MORTGAGE30US series, calculate monthly averages, merge
the rates onto both private MLS datasets, and validate the results. Console
output is aggregate-only and never displays confidential MLS records.
"""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

FRED_URL = (
    "https://fred.stlouisfed.org/graph/"
    "fredgraph.csv?id=MORTGAGE30US"
)

INPUT_FILES = {
    "listings": PROCESSED_DIR / "combined_listings_residential.csv",
    "sold": PROCESSED_DIR / "combined_sold_residential.csv",
}

OUTPUT_FILES = {
    "listings": (
        PROCESSED_DIR
        / "combined_listings_residential_with_mortgage_rates.csv"
    ),
    "sold": (
        PROCESSED_DIR
        / "combined_sold_residential_with_mortgage_rates.csv"
    ),
}

DATE_FIELDS = {
    "listings": "ListingContractDate",
    "sold": "CloseDate",
}

EXPECTED_ROWS = {
    "listings": 655_943,
    "sold": 495_334,
}

EXPECTED_MONTHS = set(
    pd.period_range(
        start="2024-01",
        end="2026-09",
        freq="M",
    )
)


def fetch_monthly_mortgage_rates() -> pd.DataFrame:
    """Fetch weekly FRED observations and return monthly average rates."""

    mortgage = pd.read_csv(
        FRED_URL,
        parse_dates=["observation_date"],
    )

    required_columns = {"observation_date", "MORTGAGE30US"}
    missing_columns = required_columns - set(mortgage.columns)
    if missing_columns:
        raise ValueError(
            "FRED response is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    mortgage = mortgage.rename(
        columns={
            "observation_date": "date",
            "MORTGAGE30US": "rate_30yr_fixed",
        }
    )
    mortgage["rate_30yr_fixed"] = pd.to_numeric(
        mortgage["rate_30yr_fixed"],
        errors="coerce",
    )
    mortgage = mortgage.dropna(
        subset=["date", "rate_30yr_fixed"]
    ).copy()
    mortgage["year_month"] = mortgage["date"].dt.to_period("M")

    mortgage_monthly = (
        mortgage.groupby("year_month", as_index=False)
        .agg(
            rate_30yr_fixed=("rate_30yr_fixed", "mean"),
            weekly_observations=("rate_30yr_fixed", "size"),
        )
        .sort_values("year_month")
        .reset_index(drop=True)
    )

    duplicated_months = mortgage_monthly["year_month"].duplicated().sum()
    if duplicated_months:
        raise ValueError(
            f"FRED monthly data contains {duplicated_months} duplicate months"
        )

    available_months = set(mortgage_monthly["year_month"])
    missing_months = sorted(EXPECTED_MONTHS - available_months)
    if missing_months:
        raise ValueError(
            "FRED monthly data does not cover required months: "
            + ", ".join(str(month) for month in missing_months)
        )

    required_rates = mortgage_monthly.loc[
        mortgage_monthly["year_month"].isin(EXPECTED_MONTHS),
        "rate_30yr_fixed",
    ]

    print("FRED MORTGAGE30US")
    print(
        f"Required monthly coverage: "
        f"{min(EXPECTED_MONTHS)} through {max(EXPECTED_MONTHS)}"
    )
    print(f"Required months covered: {len(required_rates)}")
    print(
        f"Rate range: {required_rates.min():.3f}% to "
        f"{required_rates.max():.3f}%"
    )

    return mortgage_monthly


def enrich_dataset(
    dataset: str,
    mortgage_monthly: pd.DataFrame,
) -> Path:
    """Merge monthly mortgage rates onto one private MLS dataset."""

    input_path = INPUT_FILES[dataset]
    output_path = OUTPUT_FILES[dataset]
    date_field = DATE_FIELDS[dataset]

    frame = pd.read_csv(input_path, low_memory=False)

    if len(frame) != EXPECTED_ROWS[dataset]:
        raise ValueError(
            f"{dataset}: expected {EXPECTED_ROWS[dataset]:,} rows, "
            f"but found {len(frame):,}"
        )

    if date_field not in frame.columns:
        raise ValueError(
            f"{dataset}: required date field {date_field!r} is missing"
        )

    parsed_dates = pd.to_datetime(
        frame[date_field],
        errors="coerce",
        format="mixed",
        utc=True,
    )
    invalid_dates = parsed_dates.isna().sum()
    if invalid_dates:
        raise ValueError(
            f"{dataset}: {invalid_dates:,} rows have missing or invalid "
            f"{date_field} values and cannot receive a monthly rate"
        )

    frame["year_month"] = (
        parsed_dates.dt.tz_localize(None).dt.to_period("M")
    )

    enriched = frame.merge(
        mortgage_monthly[["year_month", "rate_30yr_fixed"]],
        on="year_month",
        how="left",
        validate="many_to_one",
    )

    if len(enriched) != len(frame):
        raise ValueError(
            f"{dataset}: merge changed row count from {len(frame):,} "
            f"to {len(enriched):,}"
        )

    unmatched_rates = enriched["rate_30yr_fixed"].isna().sum()
    if unmatched_rates:
        missing_keys = sorted(
            str(month)
            for month in enriched.loc[
                enriched["rate_30yr_fixed"].isna(),
                "year_month",
            ].drop_duplicates()
        )
        raise ValueError(
            f"{dataset}: {unmatched_rates:,} rows have null mortgage rates; "
            f"unmatched months: {missing_keys}"
        )

    enriched.to_csv(output_path, index=False)

    print(f"\n{dataset.upper()} ENRICHMENT")
    print(f"Rows before merge: {len(frame):,}")
    print(f"Rows after merge: {len(enriched):,}")
    print(f"Null mortgage rates: {unmatched_rates:,}")
    print(f"Source months: {enriched['year_month'].nunique()}")
    print(f"Saved privately: {output_path.relative_to(PROJECT_ROOT)}")

    return output_path


def main() -> int:
    """Run the handbook mortgage-rate enrichment workflow."""

    missing_inputs = [
        path
        for path in INPUT_FILES.values()
        if not path.exists()
    ]
    if missing_inputs:
        raise FileNotFoundError(
            "Required Residential inputs are missing: "
            + ", ".join(str(path) for path in missing_inputs)
        )

    mortgage_monthly = fetch_monthly_mortgage_rates()

    for dataset in ("listings", "sold"):
        enrich_dataset(
            dataset=dataset,
            mortgage_monthly=mortgage_monthly,
        )

    print("\nWEEKS 2–3 MORTGAGE ENRICHMENT COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
