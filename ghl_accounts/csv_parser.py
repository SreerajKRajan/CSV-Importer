"""
CSV parsing for appointment import.
Supported columns: id, name, email, phone, service_name, service_id, staff_name, staff_id,
start_time, end_time, timezone, status.
For GHL booking creation we use service_id and staff_id from the row when present;
otherwise we fall back to ServiceCalendarMapping by service_name.
"""
import csv
import io
import logging
from datetime import datetime
from typing import Any, Iterator, List, Optional

logger = logging.getLogger(__name__)

EXPECTED_HEADERS = [
    "id",
    "name",
    "email",
    "phone",
    "service_name",
    "service_id",
    "staff_name",
    "staff_id",
    "start_time",
    "end_time",
    "timezone",
    "status",
]

# Try these datetime formats (order matters)
DATETIME_FORMATS = [
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %I:%M:%S %p",
    "%m-%d-%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %I:%M:%S %p",
    "%m/%d/%Y %H:%M",
    "%Y-%m-%d %H:%M",
]


def parse_datetime(value: str) -> Optional[datetime]:
    """Parse a datetime string using common formats. Returns None if invalid."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    logger.warning("Could not parse datetime: %r", value)
    return None


def normalize_headers(row: List[str]) -> List[str]:
    """Lowercase and strip header names for comparison."""
    return [h.strip().lower().replace(" ", "_") for h in row]


def parse_csv_rows(
    file_content: bytes,
    encoding: str = "utf-8",
    skip_invalid: bool = True,
) -> Iterator[dict]:
    """
    Yield one dict per data row. Keys are normalized (lowercase, underscores).
    Skips rows where start_time or end_time fail to parse if skip_invalid=True;
    otherwise raises for invalid rows.
    """
    try:
        text = file_content.decode(encoding)
    except UnicodeDecodeError:
        text = file_content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    header_row = next(reader, None)
    if not header_row:
        return
    normalized = normalize_headers(header_row)
    # Map normalized name -> index
    name_to_index = {name: i for i, name in enumerate(normalized)}
    for row_num, row in enumerate(reader, start=2):
        if len(row) < len(header_row):
            row = row + [""] * (len(header_row) - len(row))
        record = {}
        for norm_name, idx in name_to_index.items():
            if idx < len(row):
                record[norm_name] = (row[idx] or "").strip()
            else:
                record[norm_name] = ""
        start_raw = record.get("start_time", "")
        end_raw = record.get("end_time", "")
        start_dt = parse_datetime(start_raw)
        end_dt = parse_datetime(end_raw)
        if start_dt is None or end_dt is None:
            if skip_invalid:
                logger.warning("Skipping row %s: invalid start_time or end_time", row_num)
                continue
            raise ValueError(
                f"Row {row_num}: invalid start_time or end_time "
                f"(start={start_raw!r}, end={end_raw!r})"
            )
        record["_start_dt"] = start_dt
        record["_end_dt"] = end_dt
        yield record
