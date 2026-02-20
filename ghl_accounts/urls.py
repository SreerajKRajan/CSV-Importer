from django.urls import path

from ghl_accounts.views import (
    GHLMappingIdsView,
    ImportAppointmentsView,
    auth_connect,
    callback,
    tokens,
)

urlpatterns = [
    path("auth/connect/", auth_connect, name="oauth_connect"),
    path("auth/tokens/", tokens, name="oauth_tokens"),
    path("auth/callback/", callback, name="oauth_callback"),
    path("import-appointments/", ImportAppointmentsView.as_view(), name="import_appointments"),
    path("ghl-mapping-ids/", GHLMappingIdsView.as_view(), name="ghl_mapping_ids"),
]