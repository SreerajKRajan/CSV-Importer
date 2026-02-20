from django.contrib import admin

from ghl_accounts.models import GHLAuthCredentials, ImportedAppointment, ServiceCalendarMapping


@admin.register(GHLAuthCredentials)
class GHLAuthCredentialsAdmin(admin.ModelAdmin):
    list_display = ("location_id", "company_id", "user_id")
    list_filter = ("user_type",)


@admin.register(ServiceCalendarMapping)
class ServiceCalendarMappingAdmin(admin.ModelAdmin):
    list_display = ("location_id", "service_name", "service_id", "staff_id", "calendar_id")
    list_filter = ("location_id",)
    search_fields = ("service_name", "location_id")


@admin.register(ImportedAppointment)
class ImportedAppointmentAdmin(admin.ModelAdmin):
    list_display = ("email", "service_name", "start_time", "is_past", "ghl_booking_id", "created_at")
    list_filter = ("is_past",)
    search_fields = ("email", "name", "service_name")
    readonly_fields = ("created_at",)
