# Testing the CSV Appointment Importer

Follow these steps to verify the full flow.

---

## 1. Prerequisites

- **OAuth done**: You must have completed the GHL OAuth flow at least once so that `GHLAuthCredentials` has a row with your `location_id` and `access_token`.
- **One service mapping**: Add at least one `ServiceCalendarMapping` for the location (so future appointments can create GHL bookings). Use Django admin: **Admin → GHL Accounts → Service calendar mappings → Add**.

---

## 2. Get your `location_id`

- **Option A – Django admin**: Go to `http://127.0.0.1:8000/admin/` → **GHL Accounts → GHL auth credentials** and copy the `location_id` from the row you use.
- **Option B – Shell**:
  ```bash
  python manage.py shell -c "from ghl_accounts.models import GHLAuthCredentials; print(GHLAuthCredentials.objects.values_list('location_id', flat=True))"
  ```

Use this value as `YOUR_LOCATION_ID` below.

---

## 3. Add a service mapping (for future appointments)

In **Admin → GHL Accounts → Service calendar mappings**, add a row:

- **Location id**: same as `YOUR_LOCATION_ID`
- **Service name**: exactly as in your CSV (e.g. `Haircut`) – matching is case-insensitive
- **Service id**, **Staff id**, **Calendar id**: real IDs from your GHL location (from GHL calendar/settings or API)

Without this, future rows are still saved in `ImportedAppointment` but no GHL booking is created (and you’ll see a message in the response `errors`).

---

## 4. Start the server

```bash
cd "C:\Users\user\Desktop\CSV Impoter\csv_appointment_importer"
python manage.py runserver
```

Keep the server running.

---

## 5. Call the import API

**Using curl (PowerShell):**

```powershell
cd "C:\Users\user\Desktop\CSV Impoter\csv_appointment_importer"
curl.exe -X POST -F "file=@sample_appointments.csv" -F "location_id=YOUR_LOCATION_ID" http://127.0.0.1:8000/api/import-appointments/
```

Replace `YOUR_LOCATION_ID` with the value from step 2.

**Using PowerShell `Invoke-RestMethod`:**

```powershell
$uri = "http://127.0.0.1:8000/api/import-appointments/"
$form = @{
    file = Get-Item -Path ".\sample_appointments.csv"
    location_id = "YOUR_LOCATION_ID"
}
Invoke-RestMethod -Uri $uri -Method Post -Form $form
```

Again, replace `YOUR_LOCATION_ID`.

---

## 6. Check that it worked

**A. API response**

You should get JSON like:

```json
{
  "success": true,
  "imported": 2,
  "past_count": 1,
  "future_count": 1,
  "created_bookings": 1,
  "errors": []
}
```

- `past_count`: rows with `start_time` in the past (saved only, no GHL booking).
- `future_count`: rows with `start_time` in the future (saved + booking created if mapping exists).
- `created_bookings`: number of GHL bookings actually created.
- `errors`: any skipped rows or missing mappings (e.g. “No service mapping for service_name=…”).

**B. Django admin**

- **Imported appointments**: You should see one row per CSV row with correct `email`, `service_name`, `start_time`, `end_time`, `is_past`, and `ghl_booking_id` (set for future rows when a mapping existed).

**C. GHL (optional)**

- **Contacts**: New contacts for the emails in the CSV (if they didn’t exist).
- **Calendar**: For future rows with a mapping, a new booking in the linked calendar.

---

## 7. Quick “past only” test (no mapping needed)

To test without creating any GHL bookings:

1. Use a CSV where **all** `start_time` values are in the past (e.g. `1/15/2025 10:00:00`).
2. Call the API as in step 5. You don’t need a `ServiceCalendarMapping`.
3. Expect `past_count = number of rows`, `future_count = 0`, `created_bookings = 0`, and the same number of rows in **Imported appointments** with `is_past = True` and `ghl_booking_id` empty.

---

## 8. If something fails

- **400 with "No OAuth credentials found"**: That `location_id` has no row in `GHLAuthCredentials`. Complete OAuth for that location or use a `location_id` that exists.
- **400 with validation errors**: Ensure the request has both `file` (CSV) and `location_id`, and the file has a `.csv` extension.
- **Rows in `errors`**: Check the message (e.g. missing mapping, invalid datetime). Fix the CSV or add the mapping and re-import.
- **GHL API errors**: If contact search, contact create, or booking create fail, check server logs and compare with your GHL API curl; we can then adjust the client to match.
