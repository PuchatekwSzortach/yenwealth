"""
Shared numeric input types and conversion helpers.
"""

import decimal

type DecimalInput = decimal.Decimal | int | float
"""
Union of: ``Decimal``, ``int``, or ``float``.

In most cases, logic accepting ``DecimalInput`` will convert it to ``decimal.Decimal`` before running any computations.
"""


def to_decimal(value: object) -> decimal.Decimal:
    """
    Convert a supported numeric input to ``Decimal``.
    """

    if isinstance(value, decimal.Decimal):
        return value

    if isinstance(value, bool):
        raise TypeError("Expected a Decimal, int, or float; bool is not accepted")

    if isinstance(value, (int, float)):
        try:
            return decimal.Decimal(str(value))
        except decimal.DecimalException as error:
            raise ValueError(f"Could not convert value {value!r} to Decimal") from error

    raise TypeError(f"Expected a Decimal, int, or float; got {type(value).__name__}")
