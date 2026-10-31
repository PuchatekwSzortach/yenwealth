import decimal
import typing

import pandas


class AnnualCostsOfLiving(typing.Protocol):
    """
    Describe a callable that returns annual living costs for an age.
    """

    def __call__(self, age: int) -> decimal.Decimal:
        """
        Return annual living costs in yen for ``age``.
        """
        ...


class EarnedAnnualIncome(typing.Protocol):
    """
    Describe a callable that returns annual earned income for an age.
    """

    def __call__(self, age: int) -> decimal.Decimal:
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

        self.return_on_assets_over_time = return_on_assets_over_time
        self.inflation_over_time = inflation_over_time
