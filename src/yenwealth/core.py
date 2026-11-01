import typing

import pandas

from . import numeric


class AnnualCostsOfLiving(typing.Protocol):
    """
    Describe a callable that returns annual living costs for an age.
    """

    def __call__(self, age: int) -> numeric.DecimalInput:
        """
        Return annual living costs in yen for ``age``.
        """
        ...


class EarnedAnnualIncome(typing.Protocol):
    """
    Describe a callable that returns annual earned income for an age.
    """

    def __call__(self, age: int) -> numeric.DecimalInput:
        """
        Return annual earned income in yen for ``age``.
        """
        ...


class EconomicData:
    """
    Hold year-indexed asset returns and inflation rates.
    """

    def __init__(self, return_on_assets_over_time: pandas.DataFrame, inflation_over_time: pandas.DataFrame):
        """
        Store annual investment returns and inflation in aligned data frames.

        Args:
            return_on_assets_over_time: Asset return rates indexed by year. Column names identify assets.
            inflation_over_time: Inflation data indexed by the same years.

        Raises:
            ValueError: If the data frames do not have the same index.
        """

        if not return_on_assets_over_time.index.equals(inflation_over_time.index):

            raise ValueError("EconomicData inputs must share the same index")

        try:
            self.return_on_assets_over_time = _normalize_decimal_frame(return_on_assets_over_time)
        except ValueError as error:
            raise ValueError(f"Could not normalize return_on_assets_over_time: {error}") from error

        try:
            self.inflation_over_time = _normalize_decimal_frame(inflation_over_time)
        except ValueError as error:
            raise ValueError(f"Could not normalize inflation_over_time: {error}") from error


def _normalize_decimal_frame(frame: pandas.DataFrame) -> pandas.DataFrame:
    """
    Return a copy of ``frame`` with Decimal values and column/index error context.
    """

    normalized_columns = []

    for column_position, column_name in enumerate(frame.columns):
        normalized_column = []

        for row_position, index in enumerate(frame.index):
            value = frame.iloc[row_position, column_position]
            item = getattr(value, "item", None)

            if callable(item):
                value = item()

            try:
                normalized_value = numeric.to_decimal(value)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Could not convert column {column_name!r} at index {index!r}: {error}"
                ) from error

            normalized_column.append(normalized_value)

        normalized_columns.append(normalized_column)

    normalized_values = [
        list(row)
        for row in zip(*normalized_columns)
    ]

    if len(frame.columns) == 0:
        normalized_values = [[] for _ in frame.index]

    return pandas.DataFrame(
        normalized_values,
        index=frame.index.copy(),
        columns=frame.columns.copy(),
        dtype=object
    )
