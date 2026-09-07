"""
API views.

    GET  /api/health/
    GET  /api/meta/                      form options + indicative FX rates
    GET  /api/claims/                    list with filters + totals row(s)
    POST /api/claims/
    GET  /api/claims/{id}/               claim + payments
    PATCH /api/claims/{id}/              edit header fields / set approved amount
    GET  /api/claims/{id}/payments/
    POST /api/claims/{id}/payments/      returns the payment and the refreshed claim
"""

from datetime import date
from decimal import Decimal

from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .filters import ClaimFilter
from .models import Claim, ClaimStatus, Currency, LossNature, Payment
from .queries import totals_by_currency
from .serializers import (
    ClaimReadSerializer,
    ClaimWriteSerializer,
    CurrencyTotalsSerializer,
    PaymentCurrencyTotalsSerializer,
    PaymentReadSerializer,
    PaymentWriteSerializer,
)

# Illustrative rates for pre-filling the payment form; the user confirms or
# edits the rate before it is saved. Expressed as "1 unit of the key currency
# in GHS", from which any pair can be derived.
INDICATIVE_RATES_AS_OF = date(2026, 9, 1)
INDICATIVE_RATES_IN_GHS = {
    "GHS": Decimal("1"),
    "USD": Decimal("15.20"),
    "EUR": Decimal("16.45"),
    "GBP": Decimal("19.30"),
}


class HealthView(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class MetaView(APIView):
    """Everything the frontend forms need to render selects and rate hints."""

    def get(self, request):
        return Response(
            {
                "currencies": [{"value": c.value, "label": c.label} for c in Currency],
                "loss_natures": [{"value": n.value, "label": n.label} for n in LossNature],
                "statuses": [{"value": s.value, "label": s.label} for s in ClaimStatus],
                "indicative_rates": {
                    "as_of": INDICATIVE_RATES_AS_OF,
                    "base": "GHS",
                    "in_ghs": {k: str(v) for k, v in INDICATIVE_RATES_IN_GHS.items()},
                },
            }
        )


class NullsLastOrderingFilter(OrderingFilter):
    """Keep claims without a balance (Reserved) at the bottom whichever way you sort."""

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if not ordering:
            return queryset
        expressions = []
        for term in ordering:
            desc = term.startswith("-")
            field = F(term.lstrip("-"))
            expressions.append(field.desc(nulls_last=True) if desc else field.asc(nulls_last=True))
        return queryset.order_by(*expressions)


class ClaimViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Claims. No delete: a register keeps its history (payments are PROTECTed)."""

    queryset = Claim.objects.with_financials()
    filter_backends = [DjangoFilterBackend, NullsLastOrderingFilter]
    filterset_class = ClaimFilter
    ordering_fields = ["loss_date", "date_notified", "estimated_loss_amount", "outstanding_balance", "id"]
    ordering = ["-date_notified", "-id"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action in {"create", "partial_update", "update"}:
            return ClaimWriteSerializer
        return ClaimReadSerializer

    def _read(self, pk):
        return ClaimReadSerializer(Claim.objects.with_financials().get(pk=pk)).data

    def list(self, request, *args, **kwargs):
        claims = self.filter_queryset(self.get_queryset())
        by_claim_currency, by_payment_currency = totals_by_currency(claims)
        return Response(
            {
                "count": claims.count(),
                "results": ClaimReadSerializer(claims, many=True).data,
                "totals": {
                    "by_claim_currency": CurrencyTotalsSerializer(by_claim_currency, many=True).data,
                    "paid_by_payment_currency": PaymentCurrencyTotalsSerializer(by_payment_currency, many=True).data,
                },
            }
        )

    def create(self, request, *args, **kwargs):
        serializer = ClaimWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        return Response(self._read(claim.pk), status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        claim = self.get_object()
        data = ClaimReadSerializer(claim).data
        data["payments"] = PaymentReadSerializer(claim.payments.all(), many=True).data
        return Response(data)

    def partial_update(self, request, *args, **kwargs):
        claim = self.get_object()
        serializer = ClaimWriteSerializer(claim, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self._read(claim.pk))


class PaymentListCreateView(APIView):
    def get(self, request, claim_id):
        claim = get_object_or_404(Claim, pk=claim_id)
        return Response(PaymentReadSerializer(claim.payments.all(), many=True).data)

    def post(self, request, claim_id):
        claim = get_object_or_404(Claim, pk=claim_id)
        serializer = PaymentWriteSerializer(data=request.data, context={"claim": claim})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        refreshed = Claim.objects.with_financials().get(pk=claim.pk)
        return Response(
            {"payment": PaymentReadSerializer(payment).data, "claim": ClaimReadSerializer(refreshed).data},
            status=status.HTTP_201_CREATED,
        )
