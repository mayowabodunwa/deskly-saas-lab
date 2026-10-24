from django.urls import path
from .throttles import LoginRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    path("auth/login/", views.login_view, name="login"),
    path("me/", views.me, name="me"),
    path("auth/csrf/", views.csrf, name="csrf"),
    path("auth/logout/", views.logout_view, name="logout"),  
    path("auth/token/", TokenObtainPairView.as_view(throttle_classes=[LoginRateThrottle]), name="token"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"), 
]