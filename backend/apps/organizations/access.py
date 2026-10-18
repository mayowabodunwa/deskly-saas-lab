from django.shortcuts import get_object_or_404
from .models import Membership

def get_membership_or_404(request, slug):
    """Return the user's membership in this org, or 404 if they have none."""
    return get_object_or_404(
        Membership.objects.select_related("organization"),
        organization__slug=slug,        
        user=request.user,
    )