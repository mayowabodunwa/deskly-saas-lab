from apps.organizations.access import get_membership_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Ticket
from .serializers import TicketSerializer


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def ticket_list(request, slug):
    """Read or create tickets, but only in an org you belong to."""
    organization = get_membership_or_404(request, slug).organization

    if request.method == "POST":
        serializer = TicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(organization=organization)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    tickets = Ticket.objects.for_org(organization)
    return Response(TicketSerializer(tickets, many=True).data)