"""
Module with utilities
"""

import decimal


def format_million_yen(value: float | int | decimal.Decimal) -> str:
    """
    Format a value in million yen
    """
    return f"{decimal.Decimal(str(value)) / 10**6:.2f} million yen"
