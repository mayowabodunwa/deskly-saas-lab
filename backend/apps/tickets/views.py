from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.organizations.models import Organization

from .models import Ticket
from .serializers import TicketSerializer


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def ticket_list(request, slug):
    """Resolve the tenant from the URL, then read or create within it."""
    organization = get_object_or_404(Organization, slug=slug)

    if request.method == "POST":
        serializer = TicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(organization=organization)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    tickets = Ticket.objects.for_org(organization)
    return Response(TicketSerializer(tickets, many=True).data)