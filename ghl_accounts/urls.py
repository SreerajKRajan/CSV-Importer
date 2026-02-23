from django.urls import path

from ghl_accounts.views import (
    CSVDetectHeadersView,
    GHLMappingIdsView,
    ImportAppointmentsView,
    PastAppointmentsListView,
    SyncServicesCatalogView,
    auth_connect,
    callback,
    csrf_token_view,
    tokens,
)

urlpatterns = [
    path("csrf/", csrf_token_view, name="csrf_token"),
    path("auth/connect/", auth_connect, name="oauth_connect"),
    path("auth/tokens/", tokens, name="oauth_tokens"),
    path("auth/callback/", callback, name="oauth_callback"),
    path("import-appointments/", ImportAppointmentsView.as_view(), name="import_appointments"),
    path("import-appointments/detect-headers/", CSVDetectHeadersView.as_view(), name="import_detect_headers"),
    path("ghl-mapping-ids/", GHLMappingIdsView.as_view(), name="ghl_mapping_ids"),
    path("sync-services-catalog/", SyncServicesCatalogView.as_view(), name="sync_services_catalog"),
    path("past-appointments/", PastAppointmentsListView.as_view(), name="past_appointments"),
]