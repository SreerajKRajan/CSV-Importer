from rest_framework import serializers


class ImportAppointmentsSerializer(serializers.Serializer):
    """Request: CSV file. Optional: location_id, dry_run, override_availability, date_format, column_mapping."""

    file = serializers.FileField(
        help_text="CSV with columns: id, name, email, phone, service_name, staff_name, staff_id, start_time, end_time, timezone, status (service_id resolved from catalog by service_name)"
    )
    location_id = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Optional. GHL location ID; if not sent, we use the location from your connected GHL account.",
    )
    dry_run = serializers.BooleanField(
        required=False,
        default=False,
        help_text="If true, validate only (preview). No contacts or bookings created.",
    )
    override_availability = serializers.BooleanField(
        required=False,
        default=True,
        help_text="If true, allow booking even when slot is taken. If false, respect conflicts (mark as error).",
    )
    date_format = serializers.CharField(
        max_length=32,
        required=False,
        allow_blank=True,
        help_text="Optional. One of: DD/MM/YYYY, YYYY-MM-DD, MM/DD/YYYY, ISO.",
    )
    column_mapping = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text="Optional. Map our field names to CSV headers, e.g. {\"name\": \"Patient Name\", \"email\": \"Email\"}.",
    )

    def validate_file(self, value):
        if not value.name.lower().endswith(".csv"):
            raise serializers.ValidationError("File must be a CSV.")
        return value
