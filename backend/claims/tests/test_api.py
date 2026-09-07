from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from claims.models import Claim, Payment

from .factories import make_claim, pay

VALID_CLAIM = {
    "policy_number": "GH-MOT-99001",
    "insured_name": "Ama Serwaa",
    "loss_date": "2026-05-01",
    "date_notified": "2026-05-03",
    "loss_nature": "motor",
    "currency": "GHS",
    "estimated_loss_amount": "12500.00",
}


class HealthAndMetaTests(APITestCase):
    def test_health(self):
        r = self.client.get("/api/health/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})

    def test_meta_lists_options_and_rates(self):
        body = self.client.get("/api/meta/").json()
        self.assertEqual([c["value"] for c in body["currencies"]], ["GHS", "USD", "EUR", "GBP"])
        self.assertEqual(len(body["loss_natures"]), 8)
        self.assertEqual(len(body["statuses"]), 3)
        self.assertIn("USD", body["indicative_rates"]["in_ghs"])


class ClaimCreateTests(APITestCase):
    def test_register_claim_returns_reserved_status_and_string_money(self):
        r = self.client.post("/api/claims/", VALID_CLAIM, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.content)
        body = r.json()
        self.assertEqual(body["status"], "reserved")
        self.assertEqual(body["status_label"], "Reserved, not yet settled")
        self.assertEqual(body["estimated_loss_amount"], "12500.00")
        self.assertEqual(body["total_paid"], "0.00")
        self.assertIsNone(body["outstanding_balance"])
        self.assertEqual(body["claim_number"], f"CLM-{body['id']:05d}")

    def test_register_with_approved_amount_settles_immediately(self):
        r = self.client.post("/api/claims/", {**VALID_CLAIM, "approved_amount": "12000.00"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["status"], "settled_outstanding")
        self.assertIsNotNone(r.json()["approved_at"])

    def test_validation_errors_are_field_keyed(self):
        future = (timezone.localdate() + timedelta(days=1)).isoformat()
        cases = {
            "loss_date": {**VALID_CLAIM, "loss_date": future, "date_notified": future},
            "date_notified": {**VALID_CLAIM, "date_notified": "2026-04-30"},
            "estimated_loss_amount": {**VALID_CLAIM, "estimated_loss_amount": "0.00"},
            "approved_amount": {**VALID_CLAIM, "approved_amount": "0"},
            "currency": {**VALID_CLAIM, "currency": "NGN"},
            "loss_nature": {**VALID_CLAIM, "loss_nature": "asteroid"},
        }
        for field, payload in cases.items():
            r = self.client.post("/api/claims/", payload, format="json")
            self.assertEqual(r.status_code, 400, field)
            self.assertIn(field, r.json(), field)


class ClaimApprovalTests(APITestCase):
    def test_patch_sets_approved_amount_and_stamps_approved_at(self):
        claim = make_claim()
        r = self.client.patch(f"/api/claims/{claim.pk}/", {"approved_amount": "9000.00"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertEqual(body["approved_amount"], "9000.00")
        self.assertEqual(body["status"], "settled_outstanding")
        first_approved_at = body["approved_at"]
        self.assertIsNotNone(first_approved_at)

        r = self.client.patch(f"/api/claims/{claim.pk}/", {"approved_amount": "9500.00"}, format="json")
        self.assertEqual(r.json()["approved_at"], first_approved_at)  # unchanged on later edits

    def test_cannot_unset_approval(self):
        claim = make_claim(approved="100.00")
        r = self.client.patch(f"/api/claims/{claim.pk}/", {"approved_amount": None}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("approved_amount", r.json())

    def test_currency_locked_once_paid(self):
        claim = make_claim(currency="GHS")
        pay(claim, "10.00")
        r = self.client.patch(f"/api/claims/{claim.pk}/", {"currency": "USD"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("currency", r.json())

    def test_unknown_claim_404(self):
        self.assertEqual(self.client.get("/api/claims/999999/").status_code, 404)
        self.assertEqual(self.client.post("/api/claims/999999/payments/", {}, format="json").status_code, 404)

    def test_delete_not_allowed(self):
        claim = make_claim()
        self.assertEqual(self.client.delete(f"/api/claims/{claim.pk}/").status_code, 405)


class PaymentTests(APITestCase):
    def setUp(self):
        self.claim = make_claim(currency="GHS", approved="91200.00", loss_date=date(2026, 4, 22))
        self.url = f"/api/claims/{self.claim.pk}/payments/"

    def test_same_currency_payment_defaults_rate_to_one(self):
        r = self.client.post(self.url, {"payment_date": "2026-05-01", "amount": "20000.00", "currency": "GHS"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        body = r.json()
        self.assertEqual(body["payment"]["exchange_rate"], "1.00000000")
        self.assertEqual(body["payment"]["amount_in_claim_currency"], "20000.00")
        self.assertEqual(body["claim"]["total_paid"], "20000.00")
        self.assertEqual(body["claim"]["outstanding_balance"], "71200.00")
        self.assertEqual(body["claim"]["status"], "settled_outstanding")

    def test_same_currency_with_non_one_rate_rejected(self):
        r = self.client.post(
            self.url,
            {"payment_date": "2026-05-01", "amount": "1.00", "currency": "GHS", "exchange_rate": "15.2"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("exchange_rate", r.json())

    def test_cross_currency_requires_rate(self):
        r = self.client.post(self.url, {"payment_date": "2026-05-01", "amount": "2500.00", "currency": "USD"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("exchange_rate", r.json())

    def test_cross_currency_converts_and_stores(self):
        r = self.client.post(
            self.url,
            {"payment_date": "2026-05-15", "amount": "2500.00", "currency": "USD", "exchange_rate": "15.20"},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        body = r.json()
        self.assertEqual(body["payment"]["amount"], "2500.00")
        self.assertEqual(body["payment"]["currency"], "USD")
        self.assertEqual(body["payment"]["amount_in_claim_currency"], "38000.00")
        self.assertEqual(body["claim"]["outstanding_balance"], "53200.00")
        self.assertEqual(Payment.objects.get().amount_in_claim_currency, Decimal("38000.00"))

    def test_rate_must_be_positive(self):
        r = self.client.post(
            self.url,
            {"payment_date": "2026-05-15", "amount": "1.00", "currency": "USD", "exchange_rate": "-1"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_zero_amount_rejected_but_negative_allowed(self):
        r = self.client.post(self.url, {"payment_date": "2026-05-01", "amount": "0", "currency": "GHS"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.post(self.url, {"payment_date": "2026-05-01", "amount": "-50.00", "currency": "GHS"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["claim"]["total_paid"], "-50.00")

    def test_payment_before_loss_date_rejected(self):
        r = self.client.post(self.url, {"payment_date": "2026-04-21", "amount": "1.00", "currency": "GHS"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("payment_date", r.json())

    def test_future_payment_date_rejected(self):
        future = (timezone.localdate() + timedelta(days=1)).isoformat()
        r = self.client.post(self.url, {"payment_date": future, "amount": "1.00", "currency": "GHS"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_overpayment_flips_to_settled_paid(self):
        r = self.client.post(self.url, {"payment_date": "2026-05-01", "amount": "91200.01", "currency": "GHS"}, format="json")
        self.assertEqual(r.json()["claim"]["status"], "settled_paid")
        self.assertEqual(r.json()["claim"]["outstanding_balance"], "-0.01")

    def test_detail_includes_payments(self):
        pay(self.claim, "100.00", payment_date=date(2026, 5, 1))
        body = self.client.get(f"/api/claims/{self.claim.pk}/").json()
        self.assertEqual(len(body["payments"]), 1)
        self.assertEqual(body["payments_count"], 1)


class ClaimListTests(APITestCase):
    def setUp(self):
        a = make_claim(policy="A", currency="GHS", loss_date=date(2026, 1, 10), date_notified=date(2026, 2, 1))
        pay(a, "100.00", payment_date=date(2026, 2, 2))
        b = make_claim(policy="B", currency="GHS", approved="500.00", loss_date=date(2026, 3, 10), date_notified=date(2026, 3, 11))
        pay(b, "200.00", payment_date=date(2026, 3, 12))
        c = make_claim(policy="C", currency="USD", approved="300.00", loss_date=date(2026, 5, 10), date_notified=date(2026, 5, 11))
        pay(c, "300.00", payment_date=date(2026, 5, 12))

    def get(self, **params):
        r = self.client.get("/api/claims/", params)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_list_shape_and_totals(self):
        body = self.get()
        self.assertEqual(body["count"], 3)
        self.assertEqual(len(body["results"]), 3)
        totals = {t["currency"]: t for t in body["totals"]["by_claim_currency"]}
        self.assertEqual(totals["GHS"]["total_paid"], "300.00")
        self.assertEqual(totals["GHS"]["paid_on_reserved"], "100.00")
        self.assertEqual(totals["GHS"]["outstanding_balance"], "300.00")
        self.assertEqual(totals["USD"]["outstanding_balance"], "0.00")
        self.assertEqual(body["totals"]["paid_by_payment_currency"], [
            {"currency": "GHS", "amount": "300.00"},
            {"currency": "USD", "amount": "300.00"},
        ])

    def test_status_filter(self):
        self.assertEqual([r["policy_number"] for r in self.get(status="reserved")["results"]], ["A"])
        self.assertEqual([r["policy_number"] for r in self.get(status="settled_outstanding")["results"]], ["B"])
        self.assertEqual([r["policy_number"] for r in self.get(status="settled_paid")["results"]], ["C"])

    def test_currency_filter_shrinks_totals_too(self):
        body = self.get(currency="USD")
        self.assertEqual(body["count"], 1)
        self.assertEqual([t["currency"] for t in body["totals"]["by_claim_currency"]], ["USD"])

    def test_date_range_defaults_to_loss_date_and_is_inclusive(self):
        body = self.get(date_from="2026-03-10", date_to="2026-05-10")
        self.assertEqual(sorted(r["policy_number"] for r in body["results"]), ["B", "C"])

    def test_date_range_on_date_notified(self):
        body = self.get(date_field="date_notified", date_from="2026-01-01", date_to="2026-02-28")
        self.assertEqual([r["policy_number"] for r in body["results"]], ["A"])

    def test_filters_compose(self):
        body = self.get(currency="GHS", status="settled_outstanding", date_from="2026-01-01", date_to="2026-12-31")
        self.assertEqual([r["policy_number"] for r in body["results"]], ["B"])
        self.assertEqual(body["totals"]["by_claim_currency"][0]["claims"], 1)

    def test_search(self):
        self.assertEqual(self.get(search="b")["count"], 1)

    def test_ordering_by_annotation(self):
        body = self.get(ordering="outstanding_balance")
        balances = [r["outstanding_balance"] for r in body["results"]]
        # NULLs sort first in ascending order on Postgres? No — NULLS LAST is the default for ASC.
        self.assertEqual(balances[:2], ["0.00", "300.00"])

    def test_empty_result_has_no_totals(self):
        body = self.get(currency="GBP")
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["totals"]["by_claim_currency"], [])

    def test_invalid_filter_value_is_400(self):
        r = self.client.get("/api/claims/", {"status": "nonsense"})
        self.assertEqual(r.status_code, 400)
