"""
Integrity check for the live database: schema, counts, and the money identities.

    python manage.py check_register

Exits non-zero if any stored conversion disagrees with amount × rate, or if a
totals row does not equal the sum of its claims.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from claims.models import Claim, Payment
from claims.money import to_claim_currency
from claims.queries import totals_by_currency


class Command(BaseCommand):
    help = "Verify schema, seed presence and money identities against the connected database."

    def handle(self, *args, **options):
        problems = []

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name, data_type, numeric_precision, numeric_scale "
                "FROM information_schema.columns WHERE table_name = 'claims_claim' ORDER BY ordinal_position"
            )
            columns = cursor.fetchall()
            cursor.execute(
                "SELECT conname FROM pg_constraint WHERE contype = 'c' AND conrelid IN "
                "('claims_claim'::regclass, 'claims_payment'::regclass) ORDER BY conname"
            )
            checks = [row[0] for row in cursor.fetchall()]

        self.stdout.write("claims_claim columns:")
        for name, dtype, precision, scale in columns:
            extra = f"({precision},{scale})" if precision else ""
            self.stdout.write(f"  {name:<24} {dtype}{extra}")
        if not any(c[0] == "loss_description" for c in columns):
            problems.append("loss_description column missing")
        self.stdout.write(f"CHECK constraints ({len(checks)}): {', '.join(checks)}")

        claims = Claim.objects.with_financials()
        self.stdout.write(f"\nclaims: {claims.count()}   payments: {Payment.objects.count()}")
        if claims.count() < 15:
            problems.append("fewer than 15 claims")
        mix = {s: claims.filter(status=s).count() for s in ("reserved", "settled_outstanding", "settled_paid")}
        self.stdout.write(f"status mix: {mix}")
        if not all(mix.values()):
            problems.append("a status branch has no claims")
        others = list(Claim.objects.filter(loss_nature="other").values_list("policy_number", "loss_description"))
        self.stdout.write(f"'other' claims: {others}")
        if any(not d for _, d in others):
            problems.append("an 'other' claim has no description")

        self.stdout.write("\npayment conversions:")
        bad = [
            p.id
            for p in Payment.objects.all()
            if p.amount_in_claim_currency != to_claim_currency(p.amount, p.exchange_rate)
        ]
        self.stdout.write(f"  stored != round(amount × rate): {bad or 'none'}")
        if bad:
            problems.append(f"payments with wrong stored conversion: {bad}")

        self.stdout.write("\ntotals identities per currency:")
        rows, outflows = totals_by_currency(claims)
        for t in rows:
            rows_for_ccy = list(claims.filter(currency=t["currency"]))
            paid_ok = sum(r.total_paid for r in rows_for_ccy) == t["sum_total_paid"]
            out_ok = sum(r.outstanding_balance for r in rows_for_ccy if r.outstanding_balance is not None) == t["sum_outstanding"]
            id1 = t["sum_approved"] - t["sum_paid_on_settled"] == t["sum_outstanding"]
            id2 = t["sum_paid_on_settled"] + t["sum_paid_on_reserved"] == t["sum_total_paid"]
            ok = paid_ok and out_ok and id1 and id2
            self.stdout.write(
                f"  {t['currency']}: {t['claims']} claims  paid {t['sum_total_paid']}  "
                f"outstanding {t['sum_outstanding']}  overpaid {t['sum_overpaid']}  -> {'OK' if ok else 'BROKEN'}"
            )
            if not ok:
                problems.append(f"totals identity broken for {t['currency']}")
        self.stdout.write(f"outflows by payment currency: {[(o['currency'], str(o['amount'])) for o in outflows]}")

        if problems:
            raise CommandError("Register check FAILED: " + "; ".join(problems))
        self.stdout.write(self.style.SUCCESS("\nRegister check passed."))
