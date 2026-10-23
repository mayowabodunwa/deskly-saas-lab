from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
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


@api_view(["GET"])
@permission_classes([AllowAny])
def csrf(request):
    """Give the browser a CSRF token cookie before its first write."""
    get_token(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """End the session: Deskly throws away its note."""
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)