"""
GHL (GoHighLevel) API client for contacts and calendar bookings.
Request/response shapes aligned with official GHL curl examples.
"""
import logging
from datetime import datetime
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)

GHL_API_BASE = "https://services.leadconnectorhq.com"


def _headers(
    access_token: str,
    location_id: Optional[str] = None,
    version: Optional[str] = None,
) -> dict:
    """Headers: Content-Type, Accept, Authorization. Optional Location-Id and Version (required by GHL)."""
    h = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    if location_id:
        h["Location-Id"] = location_id
    if version:
        h["Version"] = version
    return h


def _response_error_detail(resp: requests.Response) -> str:
    """Return status and body for debugging."""
    try:
        body = resp.text[:300] if resp.text else "(empty)"
    except Exception:
        body = "(unable to read)"
    return f"GHL {resp.status_code}: {body}"


def _log_response_error(prefix: str, resp: requests.Response) -> None:
    logger.warning("%s %s", prefix, _response_error_detail(resp))


def get_calendars(
    access_token: str,
    location_id: str,
    version: Optional[str] = None,
) -> Tuple[Optional[list], Optional[str]]:
    """
    Get all calendars in a location. Returns (list of calendar dicts, None) or (None, error_detail).
    GET /calendars/
    Use this to get calendar_id for the mapping form.
    """
    url = f"{GHL_API_BASE}/calendars/"
    headers = _headers(access_token, location_id, version)
    params = {"locationId": location_id}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        calendars = data.get("calendars") or data.get("calendar") or []
        if isinstance(calendars, dict):
            calendars = [calendars]
        return (calendars, None)
    except requests.HTTPError as e:
        _log_response_error("GHL get calendars", e.response)
        return (None, _response_error_detail(e.response))
    except requests.RequestException as e:
        logger.warning("GHL get calendars failed: %s", e)
        return (None, str(e))


def get_calendar_detail(
    access_token: str,
    location_id: str,
    calendar_id: str,
    version: Optional[str] = None,
) -> Tuple[Optional[dict], Optional[str]]:
    """
    Get one calendar by ID (may include services, assignees). Returns (calendar dict, None) or (None, error_detail).
    GET /calendars/{calendarId}
    Use this to get service_id and staff_id from the calendar detail.
    """
    url = f"{GHL_API_BASE}/calendars/{calendar_id}"
    headers = _headers(access_token, location_id, version)
    params = {"locationId": location_id}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        calendar = data.get("calendar") or data
        return (calendar if isinstance(calendar, dict) else None, None)
    except requests.HTTPError as e:
        _log_response_error("GHL get calendar detail", e.response)
        return (None, _response_error_detail(e.response))
    except requests.RequestException as e:
        logger.warning("GHL get calendar detail failed: %s", e)
        return (None, str(e))


def get_contact_id_by_email(
    access_token: str,
    location_id: str,
    email: str,
    version: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Search for a contact by email.
    Returns (contact_id, None) if found, (None, None) if not found, (None, error_detail) on API error.
    """
    url = f"{GHL_API_BASE}/contacts/search"
    headers = _headers(access_token, location_id, version)
    payload = {
        "locationId": location_id,
        "query": email,
        "pageLimit": 100,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        contacts = data.get("contacts") or data.get("contact") or []
        if isinstance(contacts, dict):
            contacts = [contacts]
        if contacts:
            first = contacts[0]
            return (first.get("id") or first.get("contactId"), None)
        return (None, None)
    except requests.HTTPError as e:
        _log_response_error("GHL contact search", e.response)
        return (None, _response_error_detail(e.response))
    except requests.RequestException as e:
        logger.warning("GHL contact search failed for email=%s: %s", email, e)
        return (None, str(e))


def create_contact(
    access_token: str,
    location_id: str,
    name: str,
    email: str,
    phone: str = "",
    version: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Create a contact. Returns (contact_id, None) on success, (None, error_detail) on API error.
    POST /contacts/
    """
    url = f"{GHL_API_BASE}/contacts/"
    headers = _headers(access_token, location_id, version)
    parts = (name or "").strip().split(None, 1)
    first_name = parts[0] if parts else ""
    last_name = parts[1] if len(parts) > 1 else ""
    payload = {
        "firstName": first_name,
        "lastName": last_name,
        "name": name or "",
        "email": email,
        "locationId": location_id,
        "phone": phone or "",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return (data.get("contact", {}).get("id") or data.get("id"), None)
    except requests.HTTPError as e:
        _log_response_error("GHL create contact", e.response)
        return (None, _response_error_detail(e.response))
    except requests.RequestException as e:
        logger.warning("GHL create contact failed for email=%s: %s", email, e)
        return (None, str(e))


def create_service_booking(
    access_token: str,
    location_id: str,
    service_id: str,
    staff_id: str,
    contact_id: str,
    start_time: datetime,
    end_time: datetime,
    timezone: str = "UTC",
    calendar_id: Optional[str] = None,
    version: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Create a calendar service booking. Returns (booking_id, None) on success, (None, error_detail) on failure.
    POST /calendars/services/bookings
    """
    url = f"{GHL_API_BASE}/calendars/services/bookings"
    # Create Service Booking API requires Version 2021-04-15 per GHL docs
    headers = _headers(access_token, location_id, "2021-04-15")
    # ISO with offset if timezone-aware, e.g. 2021-06-23T03:30:00+05:30
    start_str = start_time.isoformat()
    end_str = end_time.isoformat()
    payload = {
        "locationId": location_id,
        "contactId": contact_id,
        "startTime": start_str,
        "endTime": end_str,
        "timezone": timezone,
        "services": [
            {
                "id": service_id,
                "staffId": staff_id,
                "position": 0,
            }
        ],
        "title": "Service Appointment",
        "status": "confirmed",
    }
    if calendar_id:
        payload["serviceLocationId"] = calendar_id
    # Skip slot validation so imported appointments are accepted (per GHL Create Service Booking docs)
    params = {"overrideAvailability": "true"}
    try:
        resp = requests.post(url, json=payload, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # API returns 201 with bookingId (per GHL Create Service Booking docs)
        bid = data.get("bookingId") or data.get("booking", {}).get("id") or data.get("id")
        return (bid, None)
    except requests.HTTPError as e:
        _log_response_error("GHL create booking", e.response)
        return (None, _response_error_detail(e.response))
    except requests.RequestException as e:
        logger.warning("GHL create booking failed for contact=%s: %s", contact_id, e)
        return (None, str(e))
