"""
Serializers: all request validation lives here (dates, amounts, currency rules).
Database CHECK constraints back up the rules that can be expressed per row.
"""

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import Claim, ClaimStatus, Payment
from .money import MONEY_FIELD_KWARGS, ONE, RATE_FIELD_KWARGS, to_claim_currency


def _today():
    return timezone.localdate()


def _not_in_future(value, label):
    if value > _today():
        raise serializers.ValidationError(f"{label} cannot be in the future.")
    return value


# --- Claims -----------------------------------------------------------------


class ClaimWriteSerializer(serializers.ModelSerializer):
    """Create / update a claim's own fields. Approval is handled here too so the
    registration form can optionally settle a claim in one step."""

    approved_amount = serializers.DecimalField(
        **MONEY_FIELD_KWARGS, required=False, allow_null=True, min_value=Decimal("0.01")
    )

    class Meta:
        model = Claim
        fields = [
            "policy_number",
            "insured_name",
            "loss_date",
            "date_notified",
            "loss_nature",
            "currency",
            "estimated_loss_amount",
            "approved_amount",
        ]
        extra_kwargs = {
            "estimated_loss_amount": {"min_value": Decimal("0.01")},
        }

    def validate_loss_date(self, value):
        return _not_in_future(value, "Loss date")

    def validate_date_notified(self, value):
        return _not_in_future(value, "Date notified")

    def validate(self, attrs):
        instance = self.instance
        loss_date = attrs.get("loss_date", getattr(instance, "loss_date", None))
        date_notified = attrs.get("date_notified", getattr(instance, "date_notified", None))
        if loss_date and date_notified and date_notified < loss_date:
            raise serializers.ValidationError(
                {"date_notified": "Date notified cannot be before the loss date."}
            )

        if instance is not None:
            if "approved_amount" in attrs and attrs["approved_amount"] is None and instance.approved_amount is not None:
                raise serializers.ValidationError(
                    {"approved_amount": "An approved amount cannot be removed once set."}
                )
            if "currency" in attrs and attrs["currency"] != instance.currency and instance.payments.exists():
                raise serializers.ValidationError(
                    {"currency": "Currency cannot change once payments have been recorded."}
                )
            if "loss_date" in attrs and attrs["loss_date"] != instance.loss_date:
                earliest = instance.payments.order_by("payment_date").values_list("payment_date", flat=True).first()
                if earliest and attrs["loss_date"] > earliest:
                    raise serializers.ValidationError(
                        {"loss_date": "Loss date cannot be after an existing payment date."}
                    )
        return attrs

    def _stamp_approval(self, validated_data, instance=None):
        approved = validated_data.get("approved_amount")
        previously_approved = instance is not None and instance.approved_amount is not None
        if approved is not None and not previously_approved:
            validated_data["approved_at"] = timezone.now()
        return validated_data

    def create(self, validated_data):
        return super().create(self._stamp_approval(validated_data))

    def update(self, instance, validated_data):
        return super().update(instance, self._stamp_approval(validated_data, instance))


class ClaimReadSerializer(serializers.ModelSerializer):
    """Claim plus the derived figures. Expects a queryset from `with_financials()`."""

    claim_number = serializers.CharField(read_only=True)
    loss_nature_label = serializers.CharField(source="get_loss_nature_display", read_only=True)
    total_paid = serializers.DecimalField(**MONEY_FIELD_KWARGS, read_only=True)
    outstanding_balance = serializers.DecimalField(**MONEY_FIELD_KWARGS, read_only=True, allow_null=True)
    payments_count = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = Claim
        fields = [
            "id",
            "claim_number",
            "policy_number",
            "insured_name",
            "loss_date",
            "date_notified",
            "loss_nature",
            "loss_nature_label",
            "currency",
            "estimated_loss_amount",
            "approved_amount",
            "approved_at",
            "total_paid",
            "outstanding_balance",
            "payments_count",
            "status",
            "status_label",
            "created_at",
            "updated_at",
        ]

    def get_status_label(self, obj) -> str:
        return ClaimStatus(obj.status).label


# --- Payments ---------------------------------------------------------------


class PaymentReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "claim",
            "payment_date",
            "amount",
            "currency",
            "exchange_rate",
            "amount_in_claim_currency",
            "reference",
            "created_at",
        ]


class PaymentWriteSerializer(serializers.ModelSerializer):
    """Record a payment against `context["claim"]`.

    Rules (ADR-02): same currency → rate is 1 (a supplied rate ≠ 1 is rejected);
    different currency → rate required and > 0. The converted amount is
    computed here, once, and stored.
    """

    exchange_rate = serializers.DecimalField(**RATE_FIELD_KWARGS, required=False, allow_null=True)

    class Meta:
        model = Payment
        fields = ["payment_date", "amount", "currency", "exchange_rate", "reference"]

    def validate_amount(self, value):
        if value == 0:
            raise serializers.ValidationError("Amount cannot be zero. Use a negative amount to reverse a payment.")
        return value

    def validate_payment_date(self, value):
        _not_in_future(value, "Payment date")
        claim = self.context["claim"]
        if value < claim.loss_date:
            raise serializers.ValidationError(f"Payment date cannot be before the loss date ({claim.loss_date}).")
        return value

    def validate(self, attrs):
        claim = self.context["claim"]
        rate = attrs.get("exchange_rate")

        if attrs["currency"] == claim.currency:
            if rate is not None and rate != ONE:
                raise serializers.ValidationError(
                    {"exchange_rate": f"Payment is already in {claim.currency}; the exchange rate must be 1 or omitted."}
                )
            attrs["exchange_rate"] = ONE
        else:
            if rate is None:
                raise serializers.ValidationError(
                    {"exchange_rate": f"An exchange rate is required to convert {attrs['currency']} into {claim.currency}."}
                )
            if rate <= 0:
                raise serializers.ValidationError({"exchange_rate": "Exchange rate must be greater than zero."})

        attrs["amount_in_claim_currency"] = to_claim_currency(attrs["amount"], attrs["exchange_rate"])
        return attrs

    def create(self, validated_data):
        validated_data["claim"] = self.context["claim"]
        return super().create(validated_data)


# --- Totals -----------------------------------------------------------------


class CurrencyTotalsSerializer(serializers.Serializer):
    """One footer row. Maps the `sum_*` aggregate aliases onto readable names."""

    currency = serializers.CharField()
    claims = serializers.IntegerField()
    estimated_loss_amount = serializers.DecimalField(**MONEY_FIELD_KWARGS, source="sum_estimated")
    approved_amount = serializers.DecimalField(**MONEY_FIELD_KWARGS, source="sum_approved")
    total_paid = serializers.DecimalField(**MONEY_FIELD_KWARGS, source="sum_total_paid")
    paid_on_settled = serializers.DecimalField(**MONEY_FIELD_KWARGS, source="sum_paid_on_settled")
    paid_on_reserved = serializers.DecimalField(**MONEY_FIELD_KWARGS, source="sum_paid_on_reserved")
    outstanding_balance = serializers.DecimalField(**MONEY_FIELD_KWARGS, source="sum_outstanding")
    overpaid = serializers.DecimalField(**MONEY_FIELD_KWARGS, source="sum_overpaid")


class PaymentCurrencyTotalsSerializer(serializers.Serializer):
    currency = serializers.CharField()
    amount = serializers.DecimalField(**MONEY_FIELD_KWARGS)
