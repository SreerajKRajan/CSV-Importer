# GHL token refresh (Celery)

GHL access tokens expire every 24 hours. To avoid asking users to go through **auth/connect** again, we refresh tokens automatically every **20 hours** using Celery.

## What runs

- **Task:** `ghl_accounts.tasks.refresh_ghl_tokens_task`
- **Schedule:** Every 20 hours (defined in `csv_appointment_importer/celery.py`)
- **Action:** For each row in `GHLAuthCredentials`, calls GHL `POST /oauth/token` with `grant_type=refresh_token` and updates `access_token`, `refresh_token`, and `expires_in` in the DB.

## Prerequisites

- **Redis** running (used as Celery broker). Default: `redis://localhost:6379/0`.
  - Override with env: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`.

## Run in development

1. **Start Redis** (if not already running):
   ```bash
   redis-server
   ```

2. **Start Celery worker** (runs the refresh task when Beat triggers it). Use **one terminal**:
   ```bash
   cd csv_appointment_importer
   celery -A csv_appointment_importer worker -l info
   ```

3. **Start Celery Beat** (triggers the task every 20 hours). Use a **second terminal**:
   ```bash
   cd csv_appointment_importer
   celery -A csv_appointment_importer beat -l info
   ```

**Windows:** The `worker --beat` combined option is not supported. Always run the worker and beat in two separate terminals as above.

## Production

- Run **worker** and **beat** as separate processes (e.g. systemd, supervisor, or your host’s process manager).
- Ensure Redis is available and `CELERY_BROKER_URL` is set correctly.
- After the first **auth/connect**, tokens will be refreshed every 20 hours without user action.

## Manual refresh (optional)

You can trigger a refresh once from the Django shell:

```python
from ghl_accounts.ghl_refresh import refresh_all_ghl_credentials
refresh_all_ghl_credentials()
```

Or send the task to Celery:

```python
from ghl_accounts.tasks import refresh_ghl_tokens_task
refresh_ghl_tokens_task.delay()
```
