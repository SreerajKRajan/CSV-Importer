"""
GHL OAuth token refresh. Call this periodically (e.g. every 20 hours via Celery)
so access_token stays valid without requiring auth/connect again.
"""
import logging

import requests
from decouple import config

from ghl_accounts.models import GHLAuthCredentials

logger = logging.getLogger(__name__)

TOKEN_URL = "https://services.leadconnectorhq.com/oauth/token"


def refresh_ghl_credentials(creds: GHLAuthCredentials) -> bool:
    """
    Refresh access_token for one GHLAuthCredentials using refresh_token.
    Updates the creds in DB on success. Returns True if refreshed, False on failure.
    """
    if not creds.refresh_token:
        logger.warning("No refresh_token for location_id=%s", creds.location_id)
        return False
    data = {
        "grant_type": "refresh_token",
        "client_id": config("GHL_CLIENT_ID"),
        "client_secret": config("GHL_CLIENT_SECRET"),
        "refresh_token": creds.refresh_token,
    }
    try:
        resp = requests.post(TOKEN_URL, data=data, timeout=30)
        resp.raise_for_status()
        response_data = resp.json()
    except requests.RequestException as e:
        logger.warning("GHL token refresh failed for location_id=%s: %s", creds.location_id, e)
        if hasattr(e, "response") and e.response is not None:
            try:
                logger.warning("Response: %s", e.response.text[:300])
            except Exception:
                pass
        return False
    except Exception as e:
        logger.exception("GHL token refresh error for location_id=%s: %s", creds.location_id, e)
        return False

    access_token = response_data.get("access_token")
    refresh_token = response_data.get("refresh_token") or creds.refresh_token
    expires_in = response_data.get("expires_in")

    if not access_token:
        logger.warning("GHL refresh response missing access_token for location_id=%s", creds.location_id)
        return False

    creds.access_token = access_token
    creds.refresh_token = refresh_token
    if expires_in is not None:
        creds.expires_in = expires_in
    creds.save(update_fields=["access_token", "refresh_token", "expires_in"])
    logger.info("Refreshed GHL token for location_id=%s", creds.location_id)
    return True


def refresh_all_ghl_credentials() -> int:
    """
    Refresh tokens for all stored GHLAuthCredentials. Returns count of successfully refreshed.
    """
    creds_list = list(GHLAuthCredentials.objects.all())
    if not creds_list:
        logger.debug("No GHL credentials to refresh")
        return 0
    count = 0
    for creds in creds_list:
        if refresh_ghl_credentials(creds):
            count += 1
    return count
