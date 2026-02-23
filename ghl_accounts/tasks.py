"""
Celery tasks for ghl_accounts. Used for periodic GHL token refresh.
"""
import logging

from celery import shared_task

from ghl_accounts.ghl_refresh import refresh_all_ghl_credentials

logger = logging.getLogger(__name__)


@shared_task(name="ghl_accounts.tasks.refresh_ghl_tokens_task")
def refresh_ghl_tokens_task():
    """
    Refresh GHL OAuth tokens for all stored credentials.
    Intended to run every 20 hours via Celery Beat so users don't need to re-auth.
    """
    try:
        count = refresh_all_ghl_credentials()
        logger.info("GHL token refresh task completed: %s credential(s) refreshed", count)
        return {"refreshed": count}
    except Exception as e:
        logger.exception("GHL token refresh task failed: %s", e)
        raise
