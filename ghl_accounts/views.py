import logging

import requests
from decouple import config
from django.http import JsonResponse
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ghl_accounts.ghl_client import get_calendar_detail, get_calendars
from ghl_accounts.models import GHLAuthCredentials
from ghl_accounts.serializers import ImportAppointmentsSerializer
from ghl_accounts.services import run_import

logger = logging.getLogger(__name__)


GHL_CLIENT_ID = config("GHL_CLIENT_ID")
GHL_CLIENT_SECRET = config("GHL_CLIENT_SECRET")
GHL_REDIRECTED_URI = config("GHL_REDIRECTED_URI")
TOKEN_URL = "https://services.leadconnectorhq.com/oauth/token"
SCOPE = config("SCOPE")
version_id = config("version_id")

def auth_connect(request):
    auth_url = ("https://marketplace.gohighlevel.com/oauth/chooselocation?response_type=code&"
                f"redirect_uri={GHL_REDIRECTED_URI}&"
                f"client_id={GHL_CLIENT_ID}&"
                f"scope={SCOPE}&"
                f"version_id={version_id}"
                )
    return redirect(auth_url)



def callback(request):
    
    code = request.GET.get('code')

    if not code:
        return JsonResponse({"error": "Authorization code not received from OAuth"}, status=400)
    

    return redirect(f'{config("BASE_URI")}/api/auth/tokens?code={code}')


def tokens(request):
    authorization_code = request.GET.get("code")

    if not authorization_code:
        return JsonResponse({"error": "Authorization code not found"}, status=400)

    data = {
        "grant_type": "authorization_code",
        "client_id": GHL_CLIENT_ID,
        "client_secret": GHL_CLIENT_SECRET,
        "redirect_uri": GHL_REDIRECTED_URI,
        "code": authorization_code,
    }

    response = requests.post(TOKEN_URL, data=data)

    try:
        response_data = response.json()
        if not response_data:
            return

        obj, created = GHLAuthCredentials.objects.update_or_create(
            location_id= response_data.get("locationId"),
            defaults={
                "access_token": response_data.get("access_token"),
                "refresh_token": response_data.get("refresh_token"),
                "expires_in": response_data.get("expires_in"),
                "scope": response_data.get("scope"),
                "user_type": response_data.get("userType"),
                "company_id": response_data.get("companyId"),
                "user_id":response_data.get("userId"),

            }
        )
        return JsonResponse({
            "message": "Authentication successful",
            "access_token": response_data.get('access_token'),
            "token_stored": True
        })
        
    except requests.exceptions.JSONDecodeError:
        return JsonResponse({
            "error": "Invalid JSON response from API",
            "status_code": response.status_code,
            "response_text": response.text[:500]
        }, status=500)


class ImportAppointmentsView(APIView):
    """POST /import-appointments: upload CSV to import appointments (past saved only, future also create GHL bookings)."""
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        serializer = ImportAppointmentsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file_obj = serializer.validated_data["file"]
        location_id = (serializer.validated_data.get("location_id") or "").strip()

        # If user didn't send location_id, use the one stored from GHL OAuth
        if not location_id:
            creds = GHLAuthCredentials.objects.first()
            if not creds or not creds.location_id:
                return Response(
                    {
                        "success": False,
                        "error": "No GHL location connected. Connect your GoHighLevel account first (OAuth), then try again.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            location_id = creds.location_id

        file_content = file_obj.read()

        result = run_import(
            file_content=file_content,
            location_id=location_id,
            version="2021-07-28",
        )

        if not result.get("success"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        # So the user knows which location was used (especially when we auto-picked it)
        result["location_id_used"] = location_id
        return Response(result, status=status.HTTP_200_OK)


class GHLMappingIdsView(APIView):
    """
    GET /api/ghl-mapping-ids/?location_id=...&calendar_id=... (optional)
    Returns calendars for the location (and optional calendar detail with services/staff)
    so you can copy Service id, Staff id, Calendar id into the Service calendar mapping form.
    """

    def get(self, request):
        location_id = request.query_params.get("location_id", "").strip()
        if not location_id:
            creds = GHLAuthCredentials.objects.first()
            if creds and creds.location_id:
                location_id = creds.location_id
            else:
                return Response(
                    {"error": "No GHL location connected. Connect GoHighLevel first, or pass ?location_id=..."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            creds = GHLAuthCredentials.objects.filter(location_id=location_id).first()
        if not creds:
            return Response(
                {"error": "No OAuth credentials found for this location_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        version = "2021-07-28"
        calendars, err = get_calendars(
            access_token=creds.access_token,
            location_id=location_id,
            version=version,
        )
        if err:
            return Response({"error": err, "calendars": None}, status=status.HTTP_400_BAD_REQUEST)
        result = {"location_id": location_id, "calendars": calendars or []}
        calendar_id = request.query_params.get("calendar_id", "").strip()
        if calendar_id:
            detail, detail_err = get_calendar_detail(
                access_token=creds.access_token,
                location_id=location_id,
                calendar_id=calendar_id,
                version=version,
            )
            result["calendar_detail"] = detail
            if detail_err:
                result["calendar_detail_error"] = detail_err
        elif calendars:
            first_id = (calendars[0].get("id") or calendars[0].get("calendarId")) if calendars else None
            if first_id:
                detail, _ = get_calendar_detail(
                    access_token=creds.access_token,
                    location_id=location_id,
                    calendar_id=first_id,
                    version=version,
                )
                result["first_calendar_detail"] = detail
        return Response(result, status=status.HTTP_200_OK)