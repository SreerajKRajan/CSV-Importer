"""
Import appointment logic: CSV rows → contact lookup/create → past vs future → save + optional GHL booking.
Supports dry-run (preview), date_format, column_mapping, override_availability, per-row results.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from django.utils import timezone as django_tz

from ghl_accounts.csv_parser import parse_csv_rows
from ghl_accounts.ghl_client import (
    create_contact,
    create_service_booking,
    get_contact_id_by_email,
)
from ghl_accounts.models import GHLAuthCredentials, GHLService, ImportedAppointment, ServiceCalendarMapping

logger = logging.getLogger(__name__)


def _friendly_booking_error(raw_error: Optional[str]) -> str:
    """Turn GHL API error text into a short, user-friendly message."""
    if not raw_error:
        return "Booking could not be created."
    err_lower = raw_error.lower()
    if "slot is no longer available" in err_lower or "no longer available" in err_lower:
        return (
            "This time slot is no longer available. "
            "Choose a different time, or enable “Override slot availability” to book anyway."
        )
    if "conflict" in err_lower or "already booked" in err_lower:
        return (
            "This slot is already taken. "
            "Choose a different time, or enable “Override slot availability” to book anyway."
        )
    if "internal server error" in err_lower or "500" in err_lower:
        if "slot" in err_lower or "available" in err_lower:
            return (
                "This time slot is not available. "
                "Try another time or enable “Override slot availability”."
            )
    # Keep first sentence or first 120 chars of raw message as fallback
    for sep in (". ", " — ", ": "):
        if sep in raw_error:
            return raw_error.split(sep)[0].strip() + "."
    return (raw_error[:120] + "...") if len(raw_error) > 120 else raw_error


def _resolve_service_and_staff(
    location_id: str,
    service_name: str,
    csv_service_id: Optional[str] = None,
    csv_staff_id: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Resolve (service_id, staff_id, calendar_id) for booking.
    service_id: from CSV if provided, else from GHLService (catalog) by service_name, else from ServiceCalendarMapping.
    staff_id: from CSV if provided, else from ServiceCalendarMapping.
    calendar_id: from ServiceCalendarMapping when used.
    Returns (service_id, staff_id, calendar_id) or (None, None, None) if not found.
    """
    service_id = (csv_service_id or "").strip() or None
    staff_id = (csv_staff_id or "").strip() or None
    calendar_id = None

    if service_id and staff_id:
        return (service_id, staff_id, None)

    mapping = ServiceCalendarMapping.objects.filter(
        location_id=location_id,
        service_name__iexact=service_name,
    ).first()

    if not service_id:
        # Prefer GHLService (synced catalog) then ServiceCalendarMapping
        catalog = GHLService.objects.filter(
            location_id=location_id,
            name__iexact=service_name,
        ).first()
        if catalog:
            service_id = catalog.service_id
        elif mapping:
            service_id = mapping.service_id
    if not staff_id and mapping:
        staff_id = mapping.staff_id
        calendar_id = mapping.calendar_id

    if service_id and staff_id:
        return (service_id, staff_id, calendar_id)
    return (None, None, None)


def run_preview(
    file_content: bytes,
    location_id: str,
    date_format: Optional[str] = None,
    column_mapping: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Dry-run: validate CSV and report what would succeed/fail. No GHL calls for contacts/bookings.
    Returns total_rows, would_succeed, would_fail, row_results (per-row success/error).
    """
    row_results: List[Dict[str, Any]] = []
    would_succeed = 0
    would_fail = 0
    try:
        rows = list(
            parse_csv_rows(
                file_content,
                date_format=date_format,
                column_mapping=column_mapping,
            )
        )
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total_rows": 0,
            "would_succeed": 0,
            "would_fail": 0,
            "row_results": [],
        }
    total_rows = len(rows)
    for record in rows:
        row_num = record.get("_row_num", 0)
        email = (record.get("email") or "").strip()
        service_name = (record.get("service_name") or "").strip()
        csv_service_id = (record.get("service_id") or "").strip()
        csv_staff_id = (record.get("staff_id") or "").strip()
        if not email:
            row_results.append({"row": row_num, "success": False, "error": "Missing email"})
            would_fail += 1
            continue
        service_id, staff_id, _ = _resolve_service_and_staff(
            location_id, service_name, csv_service_id, csv_staff_id
        )
        if not service_id or not staff_id:
            row_results.append(
                {
                    "row": row_num,
                    "success": False,
                    "error": f"Could not resolve service_id/staff_id for service_name={service_name!r}. "
                    "Sync services catalog (POST /api/sync-services-catalog/) or add a ServiceCalendarMapping.",
                }
            )
            would_fail += 1
            continue
        row_results.append({"row": row_num, "success": True, "error": None})
        would_succeed += 1
    return {
        "success": True,
        "total_rows": total_rows,
        "would_succeed": would_succeed,
        "would_fail": would_fail,
        "row_results": row_results,
    }


def run_import(
    file_content: bytes,
    location_id: str,
    version: str = "",
    dry_run: bool = False,
    override_availability: bool = True,
    date_format: Optional[str] = None,
    column_mapping: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Process CSV and create ImportedAppointment records; create GHL bookings for future appointments.
    Returns a summary dict: imported, past_count, future_count, created_bookings, errors.
    """
    creds = GHLAuthCredentials.objects.filter(location_id=location_id).first()
    if not creds:
        return {
            "success": False,
            "error": "No OAuth credentials found for this location_id.",
            "imported": 0,
            "past_count": 0,
            "future_count": 0,
            "created_bookings": 0,
            "errors": [],
        }

    access_token = creds.access_token
    now = django_tz.now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    imported = 0
    past_count = 0
    future_count = 0
    created_bookings = 0
    errors: List[str] = []
    row_results: List[Dict[str, Any]] = []

    if dry_run:
        return run_preview(file_content, location_id, date_format, column_mapping)

    for record in parse_csv_rows(
        file_content,
        date_format=date_format,
        column_mapping=column_mapping,
    ):
        name = record.get("name", "")
        email = (record.get("email") or "").strip()
        phone = record.get("phone", "")
        service_name = (record.get("service_name") or "").strip()
        start_dt = record["_start_dt"]
        end_dt = record["_end_dt"]
        tz_name = (record.get("timezone") or "UTC").strip() or "UTC"

        row_num = record.get("_row_num", 0)
        if not email:
            errors.append(f"Row {row_num}: missing email for name={name!r}")
            row_results.append({"row": row_num, "success": False, "error": "Missing email"})
            continue

        # Ensure we have timezone-aware datetimes for comparison
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)

        # Step 1: Get or create contact
        contact_id, search_error = get_contact_id_by_email(
            access_token=access_token,
            location_id=location_id,
            email=email,
            version=version or None,
        )
        if not contact_id:
            contact_id, create_error = create_contact(
                access_token=access_token,
                location_id=location_id,
                name=name,
                email=email,
                phone=phone,
                version=version or None,
            )
        if not contact_id:
            detail = search_error or create_error
            msg = f"Could not get or create contact for email={email!r}"
            if detail:
                msg = f"{msg} — {detail}"
            errors.append(msg)
            row_results.append({"row": row_num, "success": False, "error": msg})
            continue

        # Step 2: Past vs future
        if start_dt < now:
            ImportedAppointment.objects.create(
                name=name,
                email=email,
                phone=phone,
                service_name=service_name,
                start_time=start_dt,
                end_time=end_dt,
                is_past=True,
                ghl_booking_id=None,
            )
            imported += 1
            past_count += 1
            row_results.append({"row": row_num, "success": True, "ghl_booking_id": None, "is_past": True})
            continue

        # Future: resolve service_id (from catalog or mapping) and staff_id (from CSV or mapping)
        csv_service_id = (record.get("service_id") or "").strip()
        csv_staff_id = (record.get("staff_id") or "").strip()
        service_id, staff_id, calendar_id = _resolve_service_and_staff(
            location_id, service_name, csv_service_id, csv_staff_id
        )
        if not service_id or not staff_id:
            err_msg = (
                f"Could not resolve service_id/staff_id for service_name={service_name!r}. "
                "Sync services catalog (POST /api/sync-services-catalog/) or add a ServiceCalendarMapping."
            )
            errors.append(err_msg)
            ImportedAppointment.objects.create(
                name=name,
                email=email,
                phone=phone,
                service_name=service_name,
                start_time=start_dt,
                end_time=end_dt,
                is_past=False,
                ghl_booking_id=None,
            )
            imported += 1
            future_count += 1
            row_results.append({"row": row_num, "success": True, "ghl_booking_id": None, "error": err_msg})
            continue

        booking_id, booking_error = create_service_booking(
            access_token=access_token,
            location_id=location_id,
            service_id=service_id,
            staff_id=staff_id,
            contact_id=contact_id,
            start_time=start_dt,
            end_time=end_dt,
            timezone=tz_name,
            calendar_id=calendar_id,
            version=version or None,
            override_availability=override_availability,
        )

        ImportedAppointment.objects.create(
            name=name,
            email=email,
            phone=phone,
            service_name=service_name,
            start_time=start_dt,
            end_time=end_dt,
            is_past=False,
            ghl_booking_id=booking_id,
        )
        imported += 1
        future_count += 1
        if booking_id:
            created_bookings += 1
            row_results.append({"row": row_num, "success": True, "ghl_booking_id": booking_id, "is_past": False})
        else:
            friendly = _friendly_booking_error(booking_error)
            errors.append(friendly)
            row_results.append({"row": row_num, "success": False, "error": friendly})

    return {
        "success": True,
        "imported": imported,
        "past_count": past_count,
        "future_count": future_count,
        "created_bookings": created_bookings,
        "errors": errors,
        "row_results": row_results,
    }
