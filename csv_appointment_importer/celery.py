"""
Celery app for csv_appointment_importer. Loaded when Django starts.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "csv_appointment_importer.settings")

app = Celery("csv_appointment_importer")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Run GHL token refresh every 20 hours (so token stays valid before 24h expiry)
app.conf.beat_schedule = {
    "refresh-ghl-tokens-every-20-hours": {
        "task": "ghl_accounts.tasks.refresh_ghl_tokens_task",
        "schedule": 20 * 60 * 60,  # 20 hours in seconds
    },
}
