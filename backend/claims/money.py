"""
Money helpers — the one place in the codebase where rounding happens.

Amounts are `decimal.Decimal` with two decimal places. Exchange rates are
Decimals with up to eight decimal places, expressed as *units of claim
currency per one unit of payment currency* (e.g. a USD payment on a GHS claim
at 15.20 means 1 USD = 15.20 GHS).
"""

from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")
ONE = Decimal("1")

# Shared column definition so every money column agrees on precision.
MONEY_FIELD_KWARGS = {"max_digits": 14, "decimal_places": 2}
RATE_FIELD_KWARGS = {"max_digits": 18, "decimal_places": 8}


def quantize_money(value: Decimal) -> Decimal:
    """Round to the minor unit (2 dp), half-up — the convention used on payment vouchers."""
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def to_claim_currency(amount: Decimal, exchange_rate: Decimal) -> Decimal:
    """
    Convert a payment amount into the claim's currency.

    Rounded exactly once, here, at the moment the payment is recorded. The
    result is stored on the payment and never recomputed, so historical totals
    are reproducible and the totals row is always the sum of the visible rows.
    """
    return quantize_money(Decimal(amount) * Decimal(exchange_rate))
