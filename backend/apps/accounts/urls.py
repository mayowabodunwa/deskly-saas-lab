from django.urls import path

from . import views

urlpatterns = [
    path("auth/login/", views.login_view, name="login"),
    path("me/", views.me, name="me"),
    path("auth/csrf/", views.csrf, name="csrf"),
    path("auth/logout/", views.logout_view, name="logout"),  
]