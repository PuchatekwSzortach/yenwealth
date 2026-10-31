"""
Module with utilities
"""

import decimal

import pandas


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
