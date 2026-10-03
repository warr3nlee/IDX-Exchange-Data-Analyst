"""Week 1: validate and aggregate monthly MLS files.

The script audits source coverage and structure before concatenating monthly
listing and sold files, filtering them to Residential records, and writing
private processed datasets. Console output is limited to safe metadata and
aggregate counts; confidential row-level values are never printed.
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_FILENAMES = {
    "listings": "combined_listings_residential.csv",
    "sold": "combined_sold_residential.csv",
}

START_MONTH = "202401"
END_MONTH = "202608"

LISTING_PATTERN = re.compile(r"CRMLSListing(?P<month>\d{6})\.csv")
SOLD_PATTERN = re.compile(
    r"CRMLSSold(?P<month>\d{6})(?P<filled>_filled)?\.csv"
)


@dataclass
class CsvAudit:
    """Metadata collected from one source CSV."""

    path: Path
    dataset: str
    month: str
    is_filled: bool
    header: tuple[str, ...] = ()
    row_count: int = 0
    residential_count: int = 0
    width_errors: list[tuple[int, int, int, int]] = field(default_factory=list)
    duplicate_columns: dict[str, tuple[int, ...]] = field(default_factory=dict)
    duplicate_mismatches: Counter[str] = field(default_factory=Counter)
    ends_with_newline: bool = True
    parse_error: str | None = None
    latfilled_nonblank: int = 0
    lonfilled_nonblank: int = 0
    latitude_rescued: int = 0
    longitude_rescued: int = 0

    @property
    def schema_id(self) -> str:
        """Return a short, stable identifier for the ordered header."""

        encoded_header = "\x1f".join(self.header).encode("utf-8")
        return hashlib.sha256(encoded_header).hexdigest()[:10]


def month_range(start: str, end: str) -> list[str]:
    """Return inclusive YYYYMM values from start through end."""

    year = int(start[:4])
    month = int(start[4:])
    end_year = int(end[:4])
    end_month = int(end[4:])
    months: list[str] = []

    while (year, month) <= (end_year, end_month):
        months.append(f"{year}{month:02d}")
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    return months


def classify_source(path: Path) -> tuple[str, str, bool] | None:
    """Classify an expected raw filename without opening the file."""

    listing_match = LISTING_PATTERN.fullmatch(path.name)
    if listing_match:
        return "listings", listing_match.group("month"), False

    sold_match = SOLD_PATTERN.fullmatch(path.name)
    if sold_match:
        return (
            "sold",
            sold_match.group("month"),
            bool(sold_match.group("filled")),
        )

    return None


def inspect_csv(
    path: Path,
    dataset: str,
    month: str,
    is_filled: bool,
) -> CsvAudit:
    """Scan one CSV and collect structural metadata and aggregate counts."""

    audit = CsvAudit(
        path=path,
        dataset=dataset,
        month=month,
        is_filled=is_filled,
    )

    if path.stat().st_size:
        with path.open("rb") as binary_file:
            binary_file.seek(-1, 2)
            audit.ends_with_newline = binary_file.read(1) in (b"\n", b"\r")

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.reader(csv_file, strict=True)
            try:
                audit.header = tuple(next(reader))
            except StopIteration:
                audit.parse_error = "file is empty"
                return audit

            column_positions: dict[str, list[int]] = defaultdict(list)
            for index, column in enumerate(audit.header):
                column_positions[column].append(index)

            audit.duplicate_columns = {
                column: tuple(indexes)
                for column, indexes in column_positions.items()
                if len(indexes) > 1
            }
            property_positions = column_positions.get("PropertyType", [])

            filled_columns = {
                "latfilled",
                "lonfilled",
                "Latitude",
                "Longitude",
            }
            can_audit_filled_coordinates = filled_columns.issubset(
                column_positions
            )

            for record_number, row in enumerate(reader, start=2):
                audit.row_count += 1

                if len(row) != len(audit.header):
                    audit.width_errors.append(
                        (
                            record_number,
                            reader.line_num,
                            len(audit.header),
                            len(row),
                        )
                    )

                if property_positions and property_positions[0] < len(row):
                    if row[property_positions[0]].strip() == "Residential":
                        audit.residential_count += 1

                for column, indexes in audit.duplicate_columns.items():
                    if max(indexes) < len(row):
                        first_value = row[indexes[0]]
                        if any(row[index] != first_value for index in indexes[1:]):
                            audit.duplicate_mismatches[column] += 1

                if can_audit_filled_coordinates:
                    filled_indexes = {
                        column: column_positions[column][0]
                        for column in filled_columns
                    }
                    if max(filled_indexes.values()) < len(row):
                        latfilled = row[filled_indexes["latfilled"]].strip()
                        lonfilled = row[filled_indexes["lonfilled"]].strip()
                        latitude = row[filled_indexes["Latitude"]].strip()
                        longitude = row[filled_indexes["Longitude"]].strip()

                        audit.latfilled_nonblank += bool(latfilled)
                        audit.lonfilled_nonblank += bool(lonfilled)
                        audit.latitude_rescued += bool(latfilled) and not latitude
                        audit.longitude_rescued += (
                            bool(lonfilled) and not longitude
                        )

    except (csv.Error, UnicodeError, OSError) as error:
        audit.parse_error = f"{type(error).__name__}: {error}"

    return audit


def load_month(audit: CsvAudit) -> pd.DataFrame:
    """Load one validated monthly CSV into a pandas DataFrame."""

    frame = pd.read_csv(audit.path, low_memory=False)

    # Preserve where every record came from.
    frame["_source_month"] = audit.month
    frame["_source_file"] = audit.path.name

    if audit.dataset == "listings":
        duplicate_copies = [
            f"{column}.1"
            for column in audit.duplicate_columns
        ]

        missing_copies = [
            column
            for column in duplicate_copies
            if column not in frame.columns
        ]

        if missing_copies:
            raise ValueError(
                f"{audit.path.name}: pandas did not create the expected "
                f"duplicate columns: {missing_copies}"
            )

        frame = frame.drop(columns=duplicate_copies)

    return frame


def combine_months(
    audits: list[CsvAudit],
    dataset: str,
) -> pd.DataFrame:
    """Load and concatenate all validated months for one dataset."""

    selected_audits = sorted(
        (
            audit
            for audit in audits
            if audit.dataset == dataset
        ),
        key=lambda audit: audit.month,
    )

    if not selected_audits:
        raise ValueError(f"No source files found for {dataset}")

    monthly_frames = []

    for audit in selected_audits:
        frame = load_month(audit)
        monthly_frames.append(frame)

    combined = pd.concat(
        monthly_frames,
        ignore_index=True,
        sort=False,
    )

    expected_rows = sum(
        audit.row_count
        for audit in selected_audits
    )

    if len(combined) != expected_rows:
        raise ValueError(
            f"{dataset}: expected {expected_rows:,} combined rows, "
            f"but pandas produced {len(combined):,}"
        )

    return combined


def filter_residential(
    frame: pd.DataFrame,
    dataset: str,
    expected_rows: int,
) -> pd.DataFrame:
    """Keep Residential records and validate the filtered row count."""

    if "PropertyType" not in frame.columns:
        raise ValueError(
            f"{dataset}: PropertyType column is missing"
        )

    residential = frame.loc[
        frame["PropertyType"] == "Residential"
    ].copy()

    if len(residential) != expected_rows:
        raise ValueError(
            f"{dataset}: expected {expected_rows:,} Residential rows, "
            f"but pandas produced {len(residential):,}"
        )

    return residential


def save_processed(
    frame: pd.DataFrame,
    dataset: str,
) -> Path:
    """Save one Residential dataset under data/processed."""

    if dataset not in OUTPUT_FILENAMES:
        raise ValueError(f"Unknown dataset: {dataset}")

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        PROCESSED_DIR
        / OUTPUT_FILENAMES[dataset]
    )

    frame.to_csv(
        output_path,
        index=False,
    )

    return output_path


def discover_and_inspect() -> tuple[list[CsvAudit], list[str]]:
    """Find all raw CSVs and audit files with recognized names."""

    audits: list[CsvAudit] = []
    unrecognized_files: list[str] = []

    for path in sorted(RAW_DIR.glob("*.csv")):
        classification = classify_source(path)
        if classification is None:
            unrecognized_files.append(path.name)
            continue

        dataset, month, is_filled = classification
        audits.append(inspect_csv(path, dataset, month, is_filled))

    return audits, unrecognized_files


def coverage_issues(
    audits: list[CsvAudit],
    unrecognized_files: list[str],
) -> list[str]:
    """Validate one source file per expected month for both datasets."""

    expected = set(month_range(START_MONTH, END_MONTH))
    issues: list[str] = []

    if unrecognized_files:
        issues.append(
            "Unrecognized CSV filenames: " + ", ".join(unrecognized_files)
        )

    for dataset in ("listings", "sold"):
        dataset_months = [
            audit.month for audit in audits if audit.dataset == dataset
        ]
        actual = set(dataset_months)
        missing = sorted(expected - actual)
        out_of_range = sorted(actual - expected)
        duplicates = sorted(
            month
            for month, count in Counter(dataset_months).items()
            if count > 1
        )

        if missing:
            issues.append(f"{dataset}: missing months: {', '.join(missing)}")
        if out_of_range:
            issues.append(
                f"{dataset}: out-of-range months: {', '.join(out_of_range)}"
            )
        if duplicates:
            issues.append(
                f"{dataset}: duplicate months: {', '.join(duplicates)}"
            )

    return issues


def structural_issues(audits: list[CsvAudit]) -> tuple[list[str], list[str]]:
    """Return blocking errors and non-blocking warnings from file audits."""

    errors: list[str] = []
    warnings: list[str] = []

    for audit in audits:
        if audit.parse_error:
            errors.append(f"{audit.path.name}: {audit.parse_error}")
            continue

        if "PropertyType" not in audit.header:
            errors.append(f"{audit.path.name}: PropertyType column is missing")

        for record, physical_line, expected, actual in audit.width_errors:
            errors.append(
                f"{audit.path.name}: record {record} (physical line "
                f"{physical_line}) has {actual} fields; expected {expected}"
            )

        for column, mismatch_count in audit.duplicate_mismatches.items():
            errors.append(
                f"{audit.path.name}: duplicated column {column!r} disagrees "
                f"in {mismatch_count:,} record(s)"
            )

        if not audit.ends_with_newline:
            warnings.append(
                f"{audit.path.name}: file does not end with a line terminator"
            )

        has_latfilled = "latfilled" in audit.header
        has_lonfilled = "lonfilled" in audit.header
        if has_latfilled != has_lonfilled:
            errors.append(
                f"{audit.path.name}: latfilled/lonfilled must appear together"
            )
        if audit.is_filled and not (has_latfilled and has_lonfilled):
            errors.append(
                f"{audit.path.name}: _filled filename lacks filled coordinates"
            )
        if not audit.is_filled and (has_latfilled or has_lonfilled):
            warnings.append(
                f"{audit.path.name}: filled coordinates exist without "
                "the _filled filename suffix"
            )

    return errors, warnings


def print_source_counts(audits: list[CsvAudit], dataset: str) -> None:
    """Print safe monthly counts for one dataset."""

    selected = sorted(
        (audit for audit in audits if audit.dataset == dataset),
        key=lambda audit: audit.month,
    )
    print(f"\n{dataset.upper()} SOURCE COUNTS")
    print("month   rows      residential  columns  source")
    for audit in selected:
        print(
            f"{audit.month}  {audit.row_count:>8,}  "
            f"{audit.residential_count:>11,}  "
            f"{len(audit.header):>7}  {audit.path.name}"
        )

    print(
        f"TOTAL   {sum(audit.row_count for audit in selected):>8,}  "
        f"{sum(audit.residential_count for audit in selected):>11,}"
    )


def print_schema_summary(audits: list[CsvAudit], dataset: str) -> None:
    """Describe exact ordered-header groups and their differences."""

    selected = [audit for audit in audits if audit.dataset == dataset]
    groups: dict[tuple[str, ...], list[CsvAudit]] = defaultdict(list)
    for audit in selected:
        groups[audit.header].append(audit)

    ordered_groups = sorted(
        groups.items(),
        key=lambda item: min(audit.month for audit in item[1]),
    )

    print(f"\n{dataset.upper()} SCHEMA GROUPS: {len(ordered_groups)}")
    previous_header: tuple[str, ...] | None = None

    for number, (header, group_audits) in enumerate(ordered_groups, start=1):
        months = ",".join(audit.month for audit in group_audits)
        fingerprint = group_audits[0].schema_id
        duplicate_names = sorted(group_audits[0].duplicate_columns)

        print(
            f"group {number}: columns={len(header)}, "
            f"schema={fingerprint}, months={months}"
        )
        print(
            "  duplicate column names: "
            + (", ".join(duplicate_names) if duplicate_names else "none")
        )

        if previous_header is not None:
            previous_set = set(previous_header)
            current_set = set(header)
            added = [column for column in header if column not in previous_set]
            removed = [
                column for column in previous_header if column not in current_set
            ]
            print("  added vs prior group: " + (", ".join(added) or "none"))
            print(
                "  removed vs prior group: " + (", ".join(removed) or "none")
            )

        previous_header = header


def print_filled_coordinate_summary(audits: list[CsvAudit]) -> None:
    """Document the optional filled-coordinate columns without exposing values."""

    filled_audits = [
        audit for audit in audits if "latfilled" in audit.header
    ]
    if not filled_audits:
        return

    print("\nFILLED SOLD COORDINATE SUMMARY")
    print(
        "month   rows      latfilled  lonfilled  latitude rescued  "
        "longitude rescued"
    )
    for audit in sorted(filled_audits, key=lambda item: item.month):
        print(
            f"{audit.month}  {audit.row_count:>8,}  "
            f"{audit.latfilled_nonblank:>9,}  "
            f"{audit.lonfilled_nonblank:>9,}  "
            f"{audit.latitude_rescued:>16,}  "
            f"{audit.longitude_rescued:>17,}"
        )


def main() -> int:
    """Run the Week 1 preflight audit."""

    print("Week 1 MLS aggregation preflight")
    print(f"Expected coverage: {START_MONTH} through {END_MONTH}")

    audits, unrecognized_files = discover_and_inspect()
    errors = coverage_issues(audits, unrecognized_files)
    structural_errors, warnings = structural_issues(audits)
    errors.extend(structural_errors)

    print_source_counts(audits, "listings")
    print_source_counts(audits, "sold")
    print_schema_summary(audits, "listings")
    print_schema_summary(audits, "sold")
    print_filled_coordinate_summary(audits)

    if warnings:
        print("\nWARNINGS")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("\nPREFLIGHT FAILED")
        for error in errors:
            print(f"- {error}")
        print(
            "\nNo datasets were concatenated or written. Resolve the errors "
            "and rerun this script."
        )
        return 1

    print("\nPREFLIGHT PASSED")
    print("The source files are ready for the aggregation stage.")

    print("\nAGGREGATION")

    for dataset in ("listings", "sold"):
        dataset_audits = [
            audit
            for audit in audits
            if audit.dataset == dataset
        ]

        expected_residential = sum(
            audit.residential_count
            for audit in dataset_audits
        )

        combined = combine_months(
            audits=audits,
            dataset=dataset,
        )

        residential = filter_residential(
            frame=combined,
            dataset=dataset,
            expected_rows=expected_residential,
        )

        output_path = save_processed(
            frame=residential,
            dataset=dataset,
        )

        print(
            f"{dataset}: "
            f"{len(combined):,} combined rows → "
            f"{len(residential):,} Residential rows"
        )
        print(
            "  saved to "
            f"{output_path.relative_to(PROJECT_ROOT)}"
        )

        # Release each large dataset before loading the next one.
        del combined
        del residential

    print("\nWEEK 1 AGGREGATION COMPLETED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
