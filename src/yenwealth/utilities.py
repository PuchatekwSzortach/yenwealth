"""
Module with utilities
"""

import decimal

import pandas

from . import numeric


def require_whole_yen(value: numeric.DecimalInput, description: str) -> decimal.Decimal:
    """Convert a value to Decimal and reject fractional or non-finite yen amounts."""

    amount = numeric.to_decimal(value)

    if not amount.is_finite() or amount != amount.to_integral_value():
        raise ValueError(f"{description} must be a whole-yen amount, got {amount}")

    return amount


def format_million_yen(value: float | decimal.Decimal) -> str:
    """
    Format a value in million yen
    """
    return f"{decimal.Decimal(str(value)) / 10**6:.2f} million yen"


def pretty_format_simulation_summary(simulation_summary_frame: pandas.DataFrame) -> str:
    """
    Pretty format a simulation summary
    """

    monetary_columns = {
        col for col in simulation_summary_frame.columns if col != "age"
    }

    transformed_frame = simulation_summary_frame.assign(**{
        col: simulation_summary_frame[col] / 10**6 for col in monetary_columns
    }).rename(columns={
        col: f"{col} (mln yen)" for col in monetary_columns
    })

    return "\n" + transformed_frame.to_string(
        index=False,
        formatters={
            "age": lambda value: f"{value:.0f}",
            **{
                f"{col} (mln yen)": lambda value: f"{value:.3f}"
                for col in monetary_columns
            },
        })
