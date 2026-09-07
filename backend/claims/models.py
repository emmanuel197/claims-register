"""
Data model for the claims register.

A Claim is reserved in exactly one currency. Every claim-level figure
(estimated, approved, total paid, outstanding) is expressed in that currency.
A Payment records what was actually paid (amount + currency) and, when the
payment currency differs from the claim's, the exchange rate used and the
resulting amount in claim currency. The converted amount is stored, not
recomputed, so totals never drift as rates change.

Derived figures (total paid, outstanding balance, status) are not columns —
see `queries.py`.
"""

from django.db import models
from django.db.models import F, Q

from .money import MONEY_FIELD_KWARGS, RATE_FIELD_KWARGS
from .queries import ClaimQuerySet


class Currency(models.TextChoices):
    GHS = "GHS", "Ghana Cedi"
    USD = "USD", "US Dollar"
    EUR = "EUR", "Euro"
    GBP = "GBP", "British Pound"


class LossNature(models.TextChoices):
    FIRE = "fire", "Fire"
    THEFT = "theft", "Theft"
    FLOOD = "flood", "Flood"
    MOTOR = "motor", "Motor"
    LIABILITY = "liability", "Liability"
    MEDICAL = "medical", "Medical"
    MARINE = "marine", "Marine"
    OTHER = "other", "Other"


class ClaimStatus(models.TextChoices):
    """Derived, never stored. Definitions live in `queries.py`."""

    RESERVED = "reserved", "Reserved, not yet settled"
    SETTLED_OUTSTANDING = "settled_outstanding", "Settled, payment outstanding"
    SETTLED_PAID = "settled_paid", "Settled and paid"


class Claim(models.Model):
    policy_number = models.CharField(max_length=50, db_index=True)
    insured_name = models.CharField(max_length=120)
    loss_date = models.DateField(db_index=True)
    date_notified = models.DateField(db_index=True)
    loss_nature = models.CharField(max_length=20, choices=LossNature.choices)
    currency = models.CharField(max_length=3, choices=Currency.choices, db_index=True)
    estimated_loss_amount = models.DecimalField(**MONEY_FIELD_KWARGS)

    # Null until the claim is settled (an approved amount is agreed).
    approved_amount = models.DecimalField(**MONEY_FIELD_KWARGS, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ClaimQuerySet.as_manager()

    class Meta:
        ordering = ["-date_notified", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(estimated_loss_amount__gt=0),
                name="claim_estimated_loss_positive",
            ),
            models.CheckConstraint(
                condition=Q(approved_amount__isnull=True) | Q(approved_amount__gt=0),
                name="claim_approved_amount_positive_or_null",
            ),
            models.CheckConstraint(
                condition=Q(date_notified__gte=F("loss_date")),
                name="claim_notified_on_or_after_loss",
            ),
            models.CheckConstraint(
                condition=(Q(approved_amount__isnull=True) & Q(approved_at__isnull=True))
                | (Q(approved_amount__isnull=False) & Q(approved_at__isnull=False)),
                name="claim_approved_amount_and_at_together",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.claim_number} · {self.insured_name} · {self.policy_number}"

    @property
    def claim_number(self) -> str:
        """Human-friendly reference derived from the sequence PK (may have gaps)."""
        return f"CLM-{self.pk:05d}"


class Payment(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.PROTECT, related_name="payments")
    payment_date = models.DateField()

    # What actually left the bank.
    amount = models.DecimalField(**MONEY_FIELD_KWARGS)
    currency = models.CharField(max_length=3, choices=Currency.choices)

    # Claim currency per 1 unit of payment currency; exactly 1 when they match.
    exchange_rate = models.DecimalField(**RATE_FIELD_KWARGS)
    # amount × exchange_rate, rounded once (HALF_UP, 2 dp) at recording time.
    amount_in_claim_currency = models.DecimalField(**MONEY_FIELD_KWARGS)

    reference = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["payment_date", "id"]
        indexes = [models.Index(fields=["claim", "payment_date"])]
        constraints = [
            models.CheckConstraint(condition=~Q(amount=0), name="payment_amount_nonzero"),
            models.CheckConstraint(condition=Q(exchange_rate__gt=0), name="payment_rate_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.currency} {self.amount} on {self.payment_date} → claim {self.claim_id}"
