"""
Single source of truth for the derived money figures and the claim status.

    total_paid          = Σ payments.amount_in_claim_currency   (0 when none)
    outstanding_balance = approved_amount − total_paid          (NULL until approved)
    status              = reserved            when approved_amount is NULL
                          settled_outstanding when outstanding_balance > 0
                          settled_paid        otherwise (zero or below)

Everything is computed in SQL as queryset annotations, so the list filters
can use them in WHERE clauses and the totals row is produced by one grouped
aggregate over exactly the same filtered rows.
"""

from decimal import Decimal

from django.db import models
from django.db.models import (
    Case,
    CharField,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from .money import MONEY_FIELD_KWARGS

MONEY = DecimalField(**MONEY_FIELD_KWARGS)
ZERO = Value(Decimal("0.00"), output_field=MONEY)

# Status codes duplicated here (rather than imported from models) to avoid a
# circular import; `models.ClaimStatus` is the canonical enum with labels.
RESERVED = "reserved"
SETTLED_OUTSTANDING = "settled_outstanding"
SETTLED_PAID = "settled_paid"


class ClaimQuerySet(models.QuerySet):
    def with_financials(self):
        """Annotate total_paid, payments_count, outstanding_balance and status."""
        from .models import Payment  # local import: models.py imports this module

        payments = Payment.objects.filter(claim=OuterRef("pk")).order_by().values("claim")
        paid_subquery = payments.annotate(total=Sum("amount_in_claim_currency")).values("total")
        count_subquery = payments.annotate(total=Count("id")).values("total")

        return (
            self.annotate(
                total_paid=Coalesce(Subquery(paid_subquery, output_field=MONEY), ZERO),
                payments_count=Coalesce(
                    Subquery(count_subquery, output_field=IntegerField()),
                    Value(0, output_field=IntegerField()),
                ),
            )
            .annotate(
                # Plain subtraction propagates NULL: no approved amount → no balance.
                outstanding_balance=ExpressionWrapper(
                    F("approved_amount") - F("total_paid"), output_field=MONEY
                ),
            )
            .annotate(
                status=Case(
                    When(approved_amount__isnull=True, then=Value(RESERVED)),
                    When(outstanding_balance__gt=0, then=Value(SETTLED_OUTSTANDING)),
                    default=Value(SETTLED_PAID),
                    output_field=CharField(),
                ),
            )
        )


def totals_by_currency(claims):
    """
    Totals row(s) for a queryset already annotated by `with_financials()`.

    Returns a list of dicts, one per claim currency (sorted), plus a list of
    actual outflows grouped by *payment* currency. Aliases are prefixed `sum_`
    so they cannot shadow the row-level annotations they aggregate.
    """
    from .models import Payment

    by_claim_currency = list(
        claims.order_by()
        .values("currency")
        .annotate(
            claims=Count("id"),
            sum_estimated=Coalesce(Sum("estimated_loss_amount"), ZERO),
            sum_approved=Coalesce(Sum("approved_amount"), ZERO),
            sum_total_paid=Coalesce(Sum("total_paid"), ZERO),
            sum_paid_on_settled=Coalesce(
                Sum("total_paid", filter=Q(approved_amount__isnull=False)), ZERO
            ),
            sum_paid_on_reserved=Coalesce(
                Sum("total_paid", filter=Q(approved_amount__isnull=True)), ZERO
            ),
            sum_outstanding=Coalesce(Sum("outstanding_balance"), ZERO),
            sum_overpaid=Coalesce(
                Sum(
                    Case(
                        When(outstanding_balance__lt=0, then=-F("outstanding_balance")),
                        default=ZERO,
                        output_field=MONEY,
                    ),
                    output_field=MONEY,
                ),
                ZERO,
            ),
        )
        .order_by("currency")
    )

    by_payment_currency = list(
        Payment.objects.filter(claim__in=claims.values("pk"))
        .order_by()
        .values("currency")
        .annotate(amount=Coalesce(Sum("amount"), ZERO))
        .order_by("currency")
    )

    return by_claim_currency, by_payment_currency
