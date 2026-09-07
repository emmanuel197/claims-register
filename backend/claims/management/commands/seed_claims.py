"""
Seed the register with 18 sample claims (brief asks for at least fifteen).

Idempotent: a claim is identified by (policy_number, loss_date); existing
claims are left untouched, so data entered by a reviewer survives redeploys.
The mix is chosen so every status branch, the exactly-zero balance, an
overpayment, interim payments on a reserved claim, and cross-currency
payments all appear in the list and the totals row.
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from claims.models import Claim, Payment
from claims.money import ONE, to_claim_currency

D = Decimal

# (policy, insured, loss_date, notified, nature, ccy, estimated, approved, payments)
# payment = (date, amount, currency, rate or None, reference)
SEED = [
    # --- GHS ---------------------------------------------------------------
    ("GH-MOT-10021", "Akosua Mensah", date(2026, 1, 14), date(2026, 1, 16), "motor", "GHS", D("18500.00"), None, []),
    ("GH-FIR-10077", "Kofi Boateng Trading Ltd", date(2026, 2, 3), date(2026, 2, 5), "fire", "GHS", D("240000.00"), None,
     [(date(2026, 2, 20), D("50000.00"), "GHS", None, "Interim advance")]),
    ("GH-THF-10102", "Yaw Darko", date(2026, 3, 9), date(2026, 3, 9), "theft", "GHS", D("7200.00"), D("6800.00"),
     [(date(2026, 3, 30), D("3000.00"), "GHS", None, "First instalment")]),
    ("GH-FLD-10135", "Adjei & Sons Warehouse", date(2026, 4, 22), date(2026, 4, 28), "flood", "GHS", D("96000.00"), D("91200.00"),
     [(date(2026, 5, 15), D("2500.00"), "USD", D("15.20"), "Paid to overseas supplier"),
      (date(2026, 6, 2), D("20000.00"), "GHS", None, "Second instalment")]),
    ("GH-MED-10160", "Efua Owusu", date(2026, 5, 6), date(2026, 5, 7), "medical", "GHS", D("4300.00"), D("4300.00"),
     [(date(2026, 5, 20), D("4300.00"), "GHS", None, "Settled in full")]),
    ("GH-MOT-10188", "Nana Kwame Asante", date(2026, 6, 18), date(2026, 6, 19), "motor", "GHS", D("12000.00"), D("11500.00"),
     [(date(2026, 7, 1), D("8000.00"), "GHS", None, "Repair invoice"),
      (date(2026, 7, 14), D("3800.00"), "GHS", None, "Balance — overpaid by 300")]),
    # --- USD ---------------------------------------------------------------
    ("US-LIA-20014", "Harbourline Logistics Inc", date(2026, 1, 27), date(2026, 2, 10), "liability", "USD", D("55000.00"), None, []),
    ("US-MAR-20041", "Atlantic Cargo Partners", date(2026, 2, 15), date(2026, 2, 17), "marine", "USD", D("128000.00"), None, []),
    ("US-MOT-20066", "Daniel Ortega", date(2026, 3, 21), date(2026, 3, 22), "motor", "USD", D("9400.00"), D("9000.00"),
     [(date(2026, 4, 10), D("4000.00"), "USD", None, "Deposit to body shop")]),
    ("US-FIR-20090", "Redwood Studios LLC", date(2026, 4, 4), date(2026, 4, 6), "fire", "USD", D("310000.00"), D("295000.00"),
     [(date(2026, 4, 30), D("100000.00"), "USD", None, "First tranche"),
      (date(2026, 5, 22), D("60000.00"), "EUR", D("1.08"), "Paid to EU contractor")]),
    ("US-THF-20119", "Priya Raman", date(2026, 7, 8), date(2026, 7, 8), "theft", "USD", D("3200.00"), D("3200.00"),
     [(date(2026, 7, 20), D("3200.00"), "USD", None, "Settled in full")]),
    # --- EUR ---------------------------------------------------------------
    ("EU-FLD-30012", "Van der Berg Horticulture BV", date(2026, 2, 26), date(2026, 3, 2), "flood", "EUR", D("74000.00"), None, []),
    ("EU-LIA-30038", "Café Lumière SARL", date(2026, 3, 30), date(2026, 4, 1), "liability", "EUR", D("22000.00"), D("18000.00"),
     [(date(2026, 4, 25), D("6000.00"), "EUR", None, "Interim")]),
    ("EU-MED-30055", "Lukas Brandt", date(2026, 5, 19), date(2026, 5, 20), "medical", "EUR", D("15800.00"), D("15800.00"),
     [(date(2026, 6, 5), D("7900.00"), "EUR", None, "First half")]),
    ("EU-MOT-30071", "Sofia Rossi", date(2026, 6, 2), date(2026, 6, 3), "motor", "EUR", D("6100.00"), D("5900.00"),
     [(date(2026, 6, 24), D("5000.00"), "GBP", D("1.18"), "Paid to UK garage — settles in full")]),
    # --- GBP ---------------------------------------------------------------
    ("UK-MAR-40009", "Thames Estuary Shipping Ltd", date(2026, 1, 9), date(2026, 1, 30), "marine", "GBP", D("410000.00"), None, []),
    ("UK-FIR-40027", "Oliver Hughes", date(2026, 4, 15), date(2026, 4, 17), "fire", "GBP", D("48000.00"), D("45000.00"),
     [(date(2026, 5, 9), D("20000.00"), "USD", D("0.78"), "Paid to US-based loss assessor")]),
    ("UK-THF-40044", "Amelia Clarke", date(2026, 8, 11), date(2026, 8, 12), "theft", "GBP", D("2750.00"), D("2600.00"),
     [(date(2026, 8, 28), D("2600.00"), "GBP", None, "Settled in full")]),
]


class Command(BaseCommand):
    help = "Seed the register with sample claims and payments (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        created = skipped = 0
        for policy, insured, loss, notified, nature, ccy, estimated, approved, payments in SEED:
            if Claim.objects.filter(policy_number=policy, loss_date=loss).exists():
                skipped += 1
                continue
            claim = Claim.objects.create(
                policy_number=policy,
                insured_name=insured,
                loss_date=loss,
                date_notified=notified,
                loss_nature=nature,
                currency=ccy,
                estimated_loss_amount=estimated,
                approved_amount=approved,
                approved_at=timezone.now() if approved is not None else None,
            )
            for pay_date, amount, pay_ccy, rate, reference in payments:
                rate = ONE if pay_ccy == ccy else rate
                Payment.objects.create(
                    claim=claim,
                    payment_date=pay_date,
                    amount=amount,
                    currency=pay_ccy,
                    exchange_rate=rate,
                    amount_in_claim_currency=to_claim_currency(amount, rate),
                    reference=reference,
                )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Seed complete: {created} created, {skipped} already present."))
        for row in Claim.objects.with_financials().values("currency").order_by("currency").distinct():
            ccy = row["currency"]
            qs = Claim.objects.with_financials().filter(currency=ccy)
            counts = {s: qs.filter(status=s).count() for s in ("reserved", "settled_outstanding", "settled_paid")}
            self.stdout.write(f"  {ccy}: {qs.count()} claims - {counts}")
