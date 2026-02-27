# Production deploy (e.g. AWS)

## Before first deploy / after pull

1. **Environment variables** (in `.env` on the server; never commit `.env`):
   - `SECRET_KEY` – set a strong random value in production
   - `DEBUG=False`
   - `ALLOWED_HOSTS` – comma-separated (e.g. `csvapptimporter.automatedoctor.com,your-ec2-ip`)
   - `CSRF_TRUSTED_ORIGINS` – comma-separated HTTPS (and HTTP if needed) origins (e.g. `https://csvapptimporter.automatedoctor.com`)
   - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` – PostgreSQL (RDS)
   - `GHL_CLIENT_ID`, `GHL_CLIENT_SECRET`, `GHL_REDIRECTED_URI`, `BASE_URI`, `FRONTEND_URI`, `version_id` – GHL OAuth
   - `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` – Redis URL if using Celery

2. **Migrations**:
   ```bash
   python manage.py migrate
   ```

3. **Static files** (if serving with Django):
   ```bash
   python manage.py collectstatic --noinput
   ```

## GHL marketplace

- Redirect URL must be your **backend** callback, e.g. `https://your-domain.com/api/auth/callback/`
- In GHL Custom JS, set `PAST_APP_URL` to your **frontend** URL, e.g. `https://csvapptimporter.automatedoctor.com`
