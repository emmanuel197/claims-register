from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import ClaimViewSet, HealthView, MetaView, PaymentListCreateView

router = SimpleRouter()
router.register("claims", ClaimViewSet, basename="claim")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("meta/", MetaView.as_view(), name="meta"),
    path("claims/<int:claim_id>/payments/", PaymentListCreateView.as_view(), name="claim-payments"),
    *router.urls,
]
