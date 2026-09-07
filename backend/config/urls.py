"""Root URL configuration. Everything lives under /api/."""

from django.urls import include, path

urlpatterns = [
    path("api/", include("claims.urls")),
]
