from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from claims.models import Claim
from claims.money import to_claim_currency

from .factories import financials, make_claim, pay


class ToClaimCurrencyTests(TestCase):
    def test_same_currency_is_identity(self):
        self.assertEqual(to_claim_currency(Decimal("1234.56"), Decimal("1")), Decimal("1234.56"))

    def test_rounds_half_up_at_the_boundary(self):
        # 1.005 -> 1.01 (bankers rounding would give 1.00)
        self.assertEqual(to_claim_currency(Decimal("1.005"), Decimal("1")), Decimal("1.01"))
        self.assertEqual(to_claim_currency(Decimal("2.675"), Decimal("1")), Decimal("2.68"))

    def test_eight_decimal_rate(self):
        self.assertEqual(
            to_claim_currency(Decimal("2500.00"), Decimal("15.19876543")), Decimal("37996.91")
        )

    def test_negative_amounts_round_symmetrically(self):
        self.assertEqual(to_claim_currency(Decimal("-2500.00"), Decimal("15.20")), Decimal("-38000.00"))
        self.assertEqual(to_claim_currency(Decimal("-1.005"), Decimal("1")), Decimal("-1.01"))


class StatusDerivationTests(TestCase):
    def test_no_approval_is_reserved_with_null_balance(self):
        c = financials(make_claim())
        self.assertEqual(c.status, "reserved")
        self.assertEqual(c.total_paid, Decimal("0.00"))
        self.assertIsNone(c.outstanding_balance)

    def test_interim_payment_keeps_claim_reserved(self):
        claim = make_claim()
        pay(claim, "1000.00")
        c = financials(claim)
        self.assertEqual(c.status, "reserved")
        self.assertEqual(c.total_paid, Decimal("1000.00"))
        self.assertIsNone(c.outstanding_balance)

    def test_approved_with_balance_above_zero_is_settled_outstanding(self):
        claim = make_claim(approved="5000.00")
        pay(claim, "4999.99")
        c = financials(claim)
        self.assertEqual(c.status, "settled_outstanding")
        self.assertEqual(c.outstanding_balance, Decimal("0.01"))

    def test_exactly_zero_balance_is_settled_paid(self):
        claim = make_claim(approved="5000.00")
        pay(claim, "2000.00")
        pay(claim, "3000.00")
        c = financials(claim)
        self.assertEqual(c.status, "settled_paid")
        self.assertEqual(c.outstanding_balance, Decimal("0.00"))

    def test_negative_balance_is_settled_paid(self):
        claim = make_claim(approved="5000.00")
        pay(claim, "5300.00")
        c = financials(claim)
        self.assertEqual(c.status, "settled_paid")
        self.assertEqual(c.outstanding_balance, Decimal("-300.00"))

    def test_approved_with_no_payments_is_settled_outstanding(self):
        c = financials(make_claim(approved="5000.00"))
        self.assertEqual(c.status, "settled_outstanding")
        self.assertEqual(c.outstanding_balance, Decimal("5000.00"))

    def test_cross_currency_payment_counts_in_claim_currency(self):
        claim = make_claim(currency="GHS", approved="91200.00")
        p = pay(claim, "2500.00", currency="USD", rate="15.20")
        self.assertEqual(p.amount_in_claim_currency, Decimal("38000.00"))
        c = financials(claim)
        self.assertEqual(c.total_paid, Decimal("38000.00"))
        self.assertEqual(c.outstanding_balance, Decimal("53200.00"))

    def test_reversal_at_original_rate_nets_to_zero(self):
        claim = make_claim(currency="GHS", approved="1000.00")
        pay(claim, "33.33", currency="USD", rate="15.20")
        pay(claim, "-33.33", currency="USD", rate="15.20")
        self.assertEqual(financials(claim).total_paid, Decimal("0.00"))

    def test_status_is_filterable_in_sql(self):
        make_claim(policy="A")
        make_claim(policy="B", approved="10.00")
        paid = make_claim(policy="C", approved="10.00")
        pay(paid, "10.00")
        qs = Claim.objects.with_financials()
        self.assertEqual(set(qs.filter(status="reserved").values_list("policy_number", flat=True)), {"A"})
        self.assertEqual(set(qs.filter(status="settled_outstanding").values_list("policy_number", flat=True)), {"B"})
        self.assertEqual(set(qs.filter(status="settled_paid").values_list("policy_number", flat=True)), {"C"})


class DatabaseConstraintTests(TestCase):
    def test_estimated_loss_must_be_positive(self):
        with self.assertRaises(IntegrityError):
            make_claim(estimated="0.00")

    def test_approved_amount_zero_rejected(self):
        with self.assertRaises(IntegrityError):
            make_claim(approved="0.00")

    def test_notified_before_loss_rejected(self):
        from datetime import date

        with self.assertRaises(IntegrityError):
            make_claim(loss_date=date(2026, 3, 5), date_notified=date(2026, 3, 4))

    def test_zero_payment_rejected(self):
        claim = make_claim()
        with self.assertRaises(IntegrityError):
            pay(claim, "0.00")
