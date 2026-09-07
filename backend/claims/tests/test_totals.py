"""The totals row must always equal the sum of the rows it sits under."""

from decimal import Decimal

from django.test import TestCase

from claims.models import Claim
from claims.queries import totals_by_currency

from .factories import make_claim, pay


def build_fixture():
    # GHS: reserved-with-interim, settled-outstanding (cross-currency), exactly zero, overpaid
    r = make_claim(policy="G1", currency="GHS", estimated="1000.00")
    pay(r, "100.00")
    so = make_claim(policy="G2", currency="GHS", estimated="5000.00", approved="4500.00")
    pay(so, "100.00", currency="USD", rate="15.20")  # 1520.00
    z = make_claim(policy="G3", currency="GHS", estimated="300.00", approved="250.00")
    pay(z, "250.00")
    over = make_claim(policy="G4", currency="GHS", estimated="900.00", approved="800.00")
    pay(over, "1000.00")
    # USD: one reserved with no payments, one settled outstanding paid in EUR
    make_claim(policy="U1", currency="USD", estimated="2000.00")
    u2 = make_claim(policy="U2", currency="USD", estimated="9000.00", approved="9000.00")
    pay(u2, "1000.00", currency="EUR", rate="1.08")  # 1080.00


class TotalsIdentityTests(TestCase):
    def setUp(self):
        build_fixture()
        self.claims = Claim.objects.with_financials()
        self.rows, self.outflows = totals_by_currency(self.claims)
        self.by_ccy = {r["currency"]: r for r in self.rows}

    def test_one_row_per_currency(self):
        self.assertEqual([r["currency"] for r in self.rows], ["GHS", "USD"])
        self.assertEqual(self.by_ccy["GHS"]["claims"], 4)
        self.assertEqual(self.by_ccy["USD"]["claims"], 2)

    def test_ghs_figures(self):
        g = self.by_ccy["GHS"]
        self.assertEqual(g["sum_estimated"], Decimal("7200.00"))
        self.assertEqual(g["sum_approved"], Decimal("5550.00"))
        self.assertEqual(g["sum_total_paid"], Decimal("2870.00"))  # 100 + 1520 + 250 + 1000
        self.assertEqual(g["sum_paid_on_reserved"], Decimal("100.00"))
        self.assertEqual(g["sum_paid_on_settled"], Decimal("2770.00"))
        self.assertEqual(g["sum_outstanding"], Decimal("2780.00"))  # 2980 + 0 + (-200)
        self.assertEqual(g["sum_overpaid"], Decimal("200.00"))

    def test_usd_figures(self):
        u = self.by_ccy["USD"]
        self.assertEqual(u["sum_total_paid"], Decimal("1080.00"))
        self.assertEqual(u["sum_paid_on_reserved"], Decimal("0.00"))
        self.assertEqual(u["sum_outstanding"], Decimal("7920.00"))
        self.assertEqual(u["sum_overpaid"], Decimal("0.00"))

    def test_footer_equals_sum_of_rows_for_every_currency(self):
        for ccy, totals in self.by_ccy.items():
            rows = list(self.claims.filter(currency=ccy))
            self.assertEqual(sum(r.total_paid for r in rows), totals["sum_total_paid"], ccy)
            self.assertEqual(sum(r.estimated_loss_amount for r in rows), totals["sum_estimated"], ccy)
            self.assertEqual(
                sum(r.approved_amount for r in rows if r.approved_amount is not None), totals["sum_approved"], ccy
            )
            self.assertEqual(
                sum(r.outstanding_balance for r in rows if r.outstanding_balance is not None),
                totals["sum_outstanding"],
                ccy,
            )

    def test_accounting_identities(self):
        for ccy, t in self.by_ccy.items():
            self.assertEqual(t["sum_approved"] - t["sum_paid_on_settled"], t["sum_outstanding"], ccy)
            self.assertEqual(t["sum_paid_on_settled"] + t["sum_paid_on_reserved"], t["sum_total_paid"], ccy)

    def test_outflows_by_payment_currency(self):
        self.assertEqual(
            {o["currency"]: o["amount"] for o in self.outflows},
            {"EUR": Decimal("1000.00"), "GHS": Decimal("1350.00"), "USD": Decimal("100.00")},
        )

    def test_totals_follow_the_filter(self):
        filtered = self.claims.filter(status="settled_paid")
        rows, outflows = totals_by_currency(filtered)
        self.assertEqual([r["currency"] for r in rows], ["GHS"])
        self.assertEqual(rows[0]["claims"], 2)
        self.assertEqual(rows[0]["sum_total_paid"], Decimal("1250.00"))
        self.assertEqual(rows[0]["sum_outstanding"], Decimal("-200.00"))
        self.assertEqual({o["currency"]: o["amount"] for o in outflows}, {"GHS": Decimal("1250.00")})

    def test_empty_queryset_gives_no_rows(self):
        rows, outflows = totals_by_currency(self.claims.filter(currency="GBP"))
        self.assertEqual(rows, [])
        self.assertEqual(outflows, [])
