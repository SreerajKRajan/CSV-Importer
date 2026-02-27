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


def get_services_catalog(
    access_token: str,
    location_id: str,
    version: Optional[str] = "2021-07-28",
) -> Tuple[Optional[list], Optional[str]]:
    """
    Get services catalog from GHL. Returns (list of service dicts with id/name, None) or (None, error_detail).
    GET /calendars/services/catalog
    Requires location_id (header + query). Token from GHLAuthCredentials.
    """
    url = f"{GHL_API_BASE}/calendars/services/catalog"
    headers = _headers(access_token, location_id, version)
    params = {"locationId": location_id}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        services = data.get("services") or data.get("service") or []
        if isinstance(services, dict):
            services = [services]
        if not isinstance(services, list):
            services = []
        # Normalize: ensure each item has id and name (GHL may use id/serviceId, name/title)
        out = []
        for s in services:
            if not isinstance(s, dict):
                continue
            sid = s.get("id") or s.get("serviceId")
            name = (s.get("name") or s.get("title") or "").strip()
            if sid and name is not None:
                out.append({"id": str(sid), "name": name})
        return (out, None)
    except requests.HTTPError as e:
        _log_response_error("GHL get services catalog", e.response)
        return (None, _response_error_detail(e.response))
    except requests.RequestException as e:
        logger.warning("GHL get services catalog failed: %s", e)
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


def get_contact(
    access_token: str,
    location_id: str,
    contact_id: str,
    version: Optional[str] = "2021-07-28",
) -> Tuple[Optional[dict], Optional[str]]:
    """
    Get a contact by ID. Returns (contact_dict, None) or (None, error_detail).
    GET /contacts/:contactId
    Contact dict may have email, phone, phones (list), etc.
    """
    url = f"{GHL_API_BASE}/contacts/{contact_id}"
    headers = _headers(access_token, location_id, version)
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        contact = data.get("contact") or data
        if isinstance(contact, dict):
            return (contact, None)
        return (None, "Unexpected contact response shape")
    except requests.HTTPError as e:
        _log_response_error("GHL get contact", e.response)
        return (None, _response_error_detail(e.response))
    except requests.RequestException as e:
        logger.warning("GHL get contact failed for contact_id=%s: %s", contact_id, e)
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


def update_contact(
    access_token: str,
    location_id: str,
    contact_id: str,
    name: str,
    email: str,
    phone: str = "",
    version: Optional[str] = "2021-07-28",
) -> Tuple[bool, Optional[str]]:
    """
    Update a GHL contact. Returns (True, None) on success, (False, error_detail) on failure.
    PUT /contacts/:contactId
    Use when contact already exists (e.g. found by email) to sync name/phone from CSV and avoid duplicate errors.
    """
    url = f"{GHL_API_BASE}/contacts/{contact_id}"
    headers = _headers(access_token, location_id, version)
    parts = (name or "").strip().split(None, 1)
    first_name = parts[0] if parts else ""
    last_name = parts[1] if len(parts) > 1 else ""
    payload = {
        "firstName": first_name,
        "lastName": last_name,
        "name": name or "",
        "email": email,
        "phone": phone or "",
    }
    try:
        resp = requests.put(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return (True, None)
    except requests.HTTPError as e:
        _log_response_error("GHL update contact", e.response)
        return (False, _response_error_detail(e.response))
    except requests.RequestException as e:
        logger.warning("GHL update contact failed for contact_id=%s: %s", contact_id, e)
        return (False, str(e))


def get_contact_notes(
    access_token: str,
    location_id: str,
    contact_id: str,
    version: Optional[str] = "2021-07-28",
) -> Tuple[Optional[list], Optional[str]]:
    """
    Get all notes for a GHL contact. Returns (list of note dicts with id/body, None) or (None, error_detail).
    GET /contacts/:contactId/notes
    """
    url = f"{GHL_API_BASE}/contacts/{contact_id}/notes"
    headers = _headers(access_token, location_id, version)
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        try:
            data = resp.json() or {}
        except Exception:
            data = {}
        notes = data.get("notes") or data.get("note") or data.get("data") or []
        if isinstance(notes, dict):
            notes = [notes]
        if not isinstance(notes, list):
            notes = []
        return (notes, None)
    except requests.HTTPError as e:
        _log_response_error("GHL get contact notes", e.response)
        return (None, _response_error_detail(e.response))
    except requests.RequestException as e:
        logger.warning("GHL get contact notes failed for contact=%s: %s", contact_id, e)
        return (None, str(e))


def update_contact_note(
    access_token: str,
    location_id: str,
    contact_id: str,
    note_id: str,
    body: str,
    version: Optional[str] = "2021-07-28",
) -> Tuple[bool, Optional[str]]:
    """
    Update a GHL contact note. Returns (True, None) on success, (False, error_detail) on failure.
    PUT /contacts/:contactId/notes/:id
    """
    if not (body or "").strip():
        return (True, None)
    url = f"{GHL_API_BASE}/contacts/{contact_id}/notes/{note_id}"
    headers = _headers(access_token, location_id, version)
    payload = {"body": (body or "").strip()}
    try:
        resp = requests.put(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return (True, None)
    except requests.HTTPError as e:
        _log_response_error("GHL update contact note", e.response)
        return (False, _response_error_detail(e.response))
    except requests.RequestException as e:
        logger.warning("GHL update contact note failed for contact=%s note=%s: %s", contact_id, note_id, e)
        return (False, str(e))


def create_contact_note(
    access_token: str,
    location_id: str,
    contact_id: str,
    body: str,
    user_id: Optional[str] = None,
    version: Optional[str] = "2021-07-28",
) -> Tuple[bool, Optional[str]]:
    """
    Create a note on a GHL contact. Returns (True, None) on success, (False, error_detail) on failure.
    POST /contacts/:contactId/notes
    """
    if not (body or "").strip():
        return (True, None)
    url = f"{GHL_API_BASE}/contacts/{contact_id}/notes"
    headers = _headers(access_token, location_id, version)
    payload = {"body": (body or "").strip()}
    if user_id:
        payload["userId"] = user_id
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return (True, None)
    except requests.HTTPError as e:
        _log_response_error("GHL create contact note", e.response)
        return (False, _response_error_detail(e.response))
    except requests.RequestException as e:
        logger.warning("GHL create contact note failed for contact=%s: %s", contact_id, e)
        return (False, str(e))


def create_or_update_contact_note(
    access_token: str,
    location_id: str,
    contact_id: str,
    body: str,
    user_id: Optional[str] = None,
    version: Optional[str] = "2021-07-28",
) -> Tuple[bool, Optional[str]]:
    """
    Create or update a note on a GHL contact (for future appointments). If contact has notes, update the first;
    otherwise create. Avoids duplicate notes on repeated imports. Returns (True, None) or (False, error_detail).
    """
    if not (body or "").strip():
        return (True, None)
    try:
        notes, err = get_contact_notes(access_token, location_id, contact_id, version)
        if err:
            logger.warning("GHL get contact notes failed, will try create: %s", err)
            return create_contact_note(access_token, location_id, contact_id, body, user_id, version)
        if notes and isinstance(notes, list) and len(notes) > 0:
            first = notes[0]
            if isinstance(first, dict):
                note_id = first.get("id") or first.get("noteId") or first.get("_id")
                if note_id and str(note_id).strip():
                    return update_contact_note(
                        access_token, location_id, contact_id, str(note_id), body, version
                    )
        return create_contact_note(access_token, location_id, contact_id, body, user_id, version)
    except Exception as e:
        logger.exception("create_or_update_contact_note failed: %s", e)
        return (False, str(e))


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
    override_availability: bool = True,
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
    # When False, respect slot conflicts (client requirement). When True, allow import (current behavior).
    params = {"overrideAvailability": "true" if override_availability else "false"}
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
