import decimal
import typing

import pandas


class AnnualCostsOfLiving(typing.Protocol):
    def __call__(self, age: int) -> decimal.Decimal:
        ...


class EarnedAnnualIncome(typing.Protocol):
    def __call__(self, age: int) -> decimal.Decimal:
        ...


class EconomicData:

    def __init__(self, return_on_assets_over_time: pandas.DataFrame, inflation_over_time: pandas.DataFrame):
        """
        Class that bundles annual return on securities over time and inflation over time

        Args:
            return_on_assets_over_time (pandas.DataFrame): dataframe with return over time on assets.
            Column names correspend to securities.
            inflation_over_time (pandas.DataFrame): dataframe with inflation over time.

        Raises:
            ValueError: raised if inputs don't share the index
        """

        if not return_on_assets_over_time.index.equals(inflation_over_time.index):

            raise ValueError("EconomicData inputs must share the same index")

        self.return_on_assets_over_time = return_on_assets_over_time
        self.inflation_over_time = inflation_over_time
