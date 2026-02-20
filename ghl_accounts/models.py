from django.db import models


class GHLAuthCredentials(models.Model):
    user_id = models.CharField(max_length=255, null=True, blank=True)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_in = models.IntegerField()
    scope = models.TextField(null=True, blank=True)
    user_type = models.CharField(max_length=50, null=True, blank=True)
    company_id = models.CharField(max_length=255, null=True, blank=True)
    location_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.user_id} - {self.company_id} - {self.location_id}"


class ServiceCalendarMapping(models.Model):
    """Maps human-readable service_name to GHL calendar/service/staff IDs per location."""
    location_id = models.CharField(max_length=255, db_index=True)
    service_name = models.CharField(max_length=255)
    service_id = models.CharField(max_length=255)
    staff_id = models.CharField(max_length=255)
    calendar_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["location_id", "service_name"],
                name="unique_location_service",
            )
        ]
        ordering = ["location_id", "service_name"]

    def __str__(self):
        return f"{self.location_id} | {self.service_name}"


class ImportedAppointment(models.Model):
    """One row from an imported CSV; may or may not have a GHL booking."""
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    service_name = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_past = models.BooleanField(default=False)
    ghl_booking_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} | {self.service_name} | {self.start_time}"