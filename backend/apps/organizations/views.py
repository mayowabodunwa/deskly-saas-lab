from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .access import get_membership_or_404
from .models import Organization


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def organization_detail(request, slug):
    """Describe an org, but only to its members."""
    organization = get_membership_or_404(request, slug).organization
    return Response(
        {
            "id": organization.id,
            "name": organization.name,
            "slug": organization.slug,
            "plan": organization.plan,
        }
    )