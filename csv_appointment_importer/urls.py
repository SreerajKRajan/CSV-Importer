"""
URL configuration for csv_appointment_importer project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

from ghl_accounts.views import import_app_page

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("ghl_accounts.urls")),
    path("app/", import_app_page, name="import_app_page"),
    path("", RedirectView.as_view(url="/app/", permanent=False)),
]
