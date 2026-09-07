"""Small helpers to build claims and payments in tests without a factory library."""

from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from claims.models import Claim, Payment
from claims.money import ONE, to_claim_currency


def make_claim(
    *,
    currency="GHS",
    estimated="10000.00",
    approved=None,
    loss_date=date(2026, 3, 1),
    date_notified=None,
    policy="POL-1",
    insured="Test Insured",
    nature="motor",
):
    return Claim.objects.create(
        policy_number=policy,
        insured_name=insured,
        loss_date=loss_date,
        date_notified=date_notified or loss_date + timedelta(days=1),
        loss_nature=nature,
        currency=currency,
        estimated_loss_amount=Decimal(estimated),
        approved_amount=Decimal(approved) if approved is not None else None,
        approved_at=timezone.now() if approved is not None else None,
    )


def pay(claim, amount, *, currency=None, rate=None, payment_date=date(2026, 3, 10), reference=""):
    currency = currency or claim.currency
    rate = ONE if currency == claim.currency else Decimal(rate)
    amount = Decimal(amount)
    return Payment.objects.create(
        claim=claim,
        payment_date=payment_date,
        amount=amount,
        currency=currency,
        exchange_rate=rate,
        amount_in_claim_currency=to_claim_currency(amount, rate),
        reference=reference,
    )


def financials(claim):
    return Claim.objects.with_financials().get(pk=claim.pk)
