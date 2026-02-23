"""
CSV parsing for appointment import.
Supported columns: id, name, email, phone, service_name, staff_name, staff_id,
start_time, end_time, timezone, status.
service_id is not required in CSV: we resolve it from service_name via GHLService (synced catalog)
or ServiceCalendarMapping. staff_id can be in CSV or from mapping.
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
    "staff_name",
    "staff_id",
    "start_time",
    "end_time",
    "timezone",
    "status",
]

# Date format presets (client requirement: admin selects format)
DATE_FORMAT_PRESETS = {
    "DD/MM/YYYY": [
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %I:%M:%S %p",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ],
    "YYYY-MM-DD": [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ],
    "MM/DD/YYYY": [
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
    ],
    "ISO": [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ],
}

# Default: try common formats (order matters)
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


def parse_datetime(value: str, formats: Optional[List[str]] = None) -> Optional[datetime]:
    """Parse a datetime string using given formats or default list. Returns None if invalid."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    fmts = formats or DATETIME_FORMATS
    for fmt in fmts:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    logger.warning("Could not parse datetime: %r", value)
    return None


def normalize_headers(row: List[str]) -> List[str]:
    """Lowercase and strip header names for comparison."""
    return [h.strip().lower().replace(" ", "_") for h in row]


def _apply_column_mapping(record: dict, column_mapping: Optional[dict]) -> dict:
    """Map CSV columns to our field names. column_mapping: { our_name: csv_header_name }."""
    if not column_mapping:
        return record
    out = dict(record)
    for our_key, csv_key in column_mapping.items():
        csv_key_norm = (str(csv_key or "").strip().lower().replace(" ", "_"))
        if csv_key_norm:
            out[our_key] = record.get(csv_key_norm, record.get(our_key, ""))
    return out


def parse_csv_rows(
    file_content: bytes,
    encoding: str = "utf-8",
    skip_invalid: bool = True,
    date_format: Optional[str] = None,
    column_mapping: Optional[dict] = None,
) -> Iterator[dict]:
    """
    Yield one dict per data row. Keys are normalized (lowercase, underscores).
    date_format: one of DD/MM/YYYY, YYYY-MM-DD, MM/DD/YYYY, ISO to try those formats first.
    column_mapping: optional dict mapping our field names to CSV header names (e.g. {"name": "Patient Name"}).
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
    name_to_index = {name: i for i, name in enumerate(normalized)}
    formats = (DATE_FORMAT_PRESETS.get(date_format or "") or DATETIME_FORMATS) if date_format else None
    if formats is None:
        formats = DATETIME_FORMATS
    for row_num, row in enumerate(reader, start=2):
        if len(row) < len(header_row):
            row = row + [""] * (len(header_row) - len(row))
        record = {}
        for norm_name, idx in name_to_index.items():
            if idx < len(row):
                record[norm_name] = (row[idx] or "").strip()
            else:
                record[norm_name] = ""
        if column_mapping:
            record = _apply_column_mapping(record, column_mapping)
        start_raw = record.get("start_time", "")
        end_raw = record.get("end_time", "")
        start_dt = parse_datetime(start_raw, formats)
        end_dt = parse_datetime(end_raw, formats)
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
        record["_row_num"] = row_num
        yield record
