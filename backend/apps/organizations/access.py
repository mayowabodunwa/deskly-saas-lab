from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from .models import Membership

WRITE_ROLES = {Membership.Role.OWNER, Membership.Role.AGENT}

def require_write_role(membership):
    """Stop viewers from changing anything. Raises 403."""
    if membership.role not in WRITE_ROLES:
        raise PermissionDenied("Viewers can read tickets but not change them.")

def get_membership_or_404(request, slug):
    """Return the user's membership in this org, or 404 if they have none."""
    return get_object_or_404(
        Membership.objects.select_related("organization"),
        organization__slug=slug,        
        user=request.user,
    )