from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Organization


@api_view(["GET"])
@permission_classes([AllowAny])
def organization_detail(request, slug):
    """Resolve the tenant from the URL, then describe it."""
    organization = get_object_or_404(Organization, slug=slug)
    return Response(
        {
            "id": organization.id,
            "name": organization.name,
            "slug": organization.slug,
            "plan": organization.plan,
        }
    )