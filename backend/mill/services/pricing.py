"""Shared pricing and integer arithmetic helpers for invoices and bills.

All calculations use Decimal and round-half-up to the nearest paisa.
Rounding rule:
- Values >= 0.5 paisa round up to the next whole paisa.
- Values < 0.5 paisa round down.

Pricing rules:
- Fabric: round_half_up(total_cm * unit_price_paise / 100)
- Kg (yarn/materials): round_half_up(total_g * rate_per_kg_paise / 1000)
- Tax: round_half_up(base_paise * tax_pct / 100)
"""
from decimal import Decimal, ROUND_HALF_UP


def round_half_up_paise(val: Decimal | int | float | str) -> int:
    """Round a Decimal paisa value to the nearest integer paisa using round-half-up."""
    return int(Decimal(str(val)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def compute_fabric_line_total(total_cm: int, unit_price_paise: int) -> int:
    """
    Calculate fabric line total in paise from roll centimetres and rate per metre:
    round_half_up(total_cm * unit_price_paise / 100)
    """
    exact = (Decimal(int(total_cm)) * Decimal(int(unit_price_paise))) / Decimal(100)
    return round_half_up_paise(exact)


def compute_yarn_line_total(total_g: int, rate_per_kg_paise: int) -> int:
    """
    Calculate yarn/material line total in paise from grams and rate per kg:
    round_half_up(total_g * rate_per_kg_paise / 1000)
    """
    exact = (Decimal(int(total_g)) * Decimal(int(rate_per_kg_paise))) / Decimal(1000)
    return round_half_up_paise(exact)


def compute_tax(base_paise: int, tax_pct: Decimal | int | str | float) -> int:
    """
    Calculate tax in paise from base amount and tax percentage using round-half-up:
    round_half_up(base_paise * tax_pct / 100)
    """
    exact = (Decimal(int(base_paise)) * Decimal(str(tax_pct))) / Decimal(100)
    return round_half_up_paise(exact)


def cm_to_meters_decimal(cm: int) -> Decimal:
    """Convert integer centimetres to Decimal metres with 3 decimal places."""
    return (Decimal(int(cm)) / Decimal(100)).quantize(Decimal("0.001"))


def meters_decimal_to_cm(m: Decimal | str | int | float) -> int:
    """Convert Decimal metres back to integer centimetres."""
    dec = Decimal(str(m))
    return int((dec * Decimal(100)).to_integral_value(rounding=ROUND_HALF_UP))


def g_to_kg_decimal(g: int) -> Decimal:
    """Convert integer grams to Decimal kg with 3 decimal places."""
    return (Decimal(int(g)) / Decimal(1000)).quantize(Decimal("0.001"))


def kg_decimal_to_g(kg: Decimal | str | int | float) -> int:
    """Convert Decimal kg back to integer grams."""
    dec = Decimal(str(kg))
    return int((dec * Decimal(1000)).to_integral_value(rounding=ROUND_HALF_UP))


def invoice_matches_dispatch(invoice_qty_m: Decimal | str | float, rolls_length_cm: list[int] | int) -> bool:
    """
    Check that invoice quantity in metres matches dispatch roll length in cm using exact integer arithmetic.

    Rule (Condition 3):
    invoice quantity x 100 must equal the sum of the dispatched rolls' length_cm exactly.
    """
    total_roll_cm = rolls_length_cm if isinstance(rolls_length_cm, int) else sum(rolls_length_cm)
    dec_qty = Decimal(str(invoice_qty_m))
    inv_cm = int((dec_qty * Decimal(100)).to_integral_value(rounding=ROUND_HALF_UP))
    return inv_cm == total_roll_cm
