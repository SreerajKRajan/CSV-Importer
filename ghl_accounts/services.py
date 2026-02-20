"""
Import appointment logic: CSV rows → contact lookup/create → past vs future → save + optional GHL booking.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from django.utils import timezone as django_tz

from ghl_accounts.csv_parser import parse_csv_rows
from ghl_accounts.ghl_client import (
    create_contact,
    create_service_booking,
    get_contact_id_by_email,
)
from ghl_accounts.models import GHLAuthCredentials, ImportedAppointment, ServiceCalendarMapping

logger = logging.getLogger(__name__)


def run_import(
    file_content: bytes,
    location_id: str,
    version: str = "",
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

    for record in parse_csv_rows(file_content):
        name = record.get("name", "")
        email = (record.get("email") or "").strip()
        phone = record.get("phone", "")
        service_name = (record.get("service_name") or "").strip()
        start_dt = record["_start_dt"]
        end_dt = record["_end_dt"]
        tz_name = (record.get("timezone") or "UTC").strip() or "UTC"

        if not email:
            errors.append(f"Row skipped: missing email for name={name!r}")
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
            continue

        # Future: create GHL booking using service_id and staff_id from CSV, or from mapping
        csv_service_id = (record.get("service_id") or "").strip()
        csv_staff_id = (record.get("staff_id") or "").strip()
        if csv_service_id and csv_staff_id:
            service_id = csv_service_id
            staff_id = csv_staff_id
            calendar_id = None
        else:
            mapping = ServiceCalendarMapping.objects.filter(
                location_id=location_id,
                service_name__iexact=service_name,
            ).first()
            if not mapping:
                errors.append(
                    f"No service_id/staff_id in row and no mapping for service_name={service_name!r}; row saved without GHL booking."
                )
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
                continue
            service_id = mapping.service_id
            staff_id = mapping.staff_id
            calendar_id = mapping.calendar_id

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
        else:
            msg = f"Booking creation failed for email={email!r}, service={service_name!r}"
            if booking_error:
                msg = f"{msg} — {booking_error}"
            errors.append(msg)

    return {
        "success": True,
        "imported": imported,
        "past_count": past_count,
        "future_count": future_count,
        "created_bookings": created_bookings,
        "errors": errors,
    }
