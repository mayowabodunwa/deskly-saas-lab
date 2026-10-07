from django.urls import path, include

from . import views
                                                                    
urlpatterns = [
    path("<slug:slug>/", views.organization_detail, name="organization-detail"),
    path("<slug:slug>/", include("apps.tickets.urls")),
]