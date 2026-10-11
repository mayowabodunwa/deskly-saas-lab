from django.contrib.auth import authenticate, login
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    user = authenticate(
        request,
        username=request.data.get("username"),
        password=request.data.get("password"),
    )
    if user is None:
        return Response(
            {"detail": "Invalid username or password."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    login(request, user)
    return Response({"username": user.username})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    memberships = request.user.memberships.select_related("organization")
    return Response({
        "username": request.user.username,
        "memberships": [
            {"org": m.organization.slug, "role": m.role}
            for m in memberships
        ],
    })