from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/", include("apps.core.urls")),
    path("api/orgs/", include("apps.organizations.urls")),
    path("api/", include("apps.accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path(settings.ADMIN_URL, admin.site.urls),
]
