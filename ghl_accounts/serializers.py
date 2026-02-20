from rest_framework import serializers


class ImportAppointmentsSerializer(serializers.Serializer):
    """Request: CSV file. location_id is optional; if omitted, we use the one from GHL OAuth (GHLAuthCredentials)."""

    file = serializers.FileField(
        help_text="CSV with columns: id, name, email, phone, service_name, service_id, staff_name, staff_id, start_time, end_time, timezone, status"
    )
    location_id = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Optional. GHL location ID; if not sent, we use the location from your connected GHL account.",
    )

    def validate_file(self, value):
        if not value.name.lower().endswith(".csv"):
            raise serializers.ValidationError("File must be a CSV.")
        return value
