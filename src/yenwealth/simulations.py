"""
Module with simulation logic
"""

import dataclasses
import decimal
import logging
import math
import typing

import arch.bootstrap
import numpy
import pandas

from . import constants, investments

LOGGER = logging.getLogger(__name__)


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


class EconomicDataSimulator:

    def __init__(self, historical_economic_data: EconomicData):

        self.historical_economic_data = historical_economic_data

    def generate_simulation(self, start: int, period: int, block_size: int) -> EconomicData:

        economic_data_index = self.historical_economic_data.inflation_over_time.index.to_numpy()

        bootstrap = arch.bootstrap.StationaryBootstrap(block_size, economic_data_index)

        draws_needed = math.ceil(period / len(economic_data_index))

        arch_draws = [typing.cast(pandas.DataFrame, draw[0][0]) for draw in bootstrap.bootstrap(draws_needed)]

        full_simulation_index = numpy.concat(arch_draws, axis=0)[:period]

        return_on_assets_over_time = \
            self.historical_economic_data.return_on_assets_over_time.loc[full_simulation_index]

        return_on_assets_over_time.index = range(start, start + period)

        inflation_over_time = self.historical_economic_data.inflation_over_time.loc[full_simulation_index]
        inflation_over_time.index = range(start, start + period)

        return EconomicData(
            return_on_assets_over_time=return_on_assets_over_time,
            inflation_over_time=inflation_over_time
        )


@dataclasses.dataclass
class FinancesSimulatorInputs:

    annual_costs_callable: AnnualCostsOfLiving
    earned_annual_income_callable: EarnedAnnualIncome
    investment_manager: investments.InvestmentManager
    simulation_start_age: int
    simulation_end_age: int


class FinancesSimulator:

    def __init__(self, inputs: FinancesSimulatorInputs):

        self.inputs = inputs
        self.investment_manager = self.inputs.investment_manager

    def run_simulation(self) -> dict:

        current_age = self.inputs.simulation_start_age
        current_year = self.investment_manager.simulation_start_year

        investment_simulation = {
            "age": [],
            "portfolio_value": [],
            "after_tax_portfolio_value": [],
            "cost_of_living": []
        }

        if LOGGER.isEnabledFor(logging.INFO):

            portfolio_summary = self.investment_manager.get_formatted_portfolio_summary_description()
            LOGGER.debug(f"Portfolio value at simulation start:\n{portfolio_summary}")

        try:

            # While we expect to be alive and have money in our portfolio
            while (current_age <= self.inputs.simulation_end_age) and (self.investment_manager.portfolio_value > 0):

                LOGGER.info(f"Simulating year {current_year} at age {current_age}")

                self.investment_manager.optimize_investments()

                if LOGGER.isEnabledFor(logging.DEBUG):

                    portfolio_summary = self.investment_manager.get_formatted_portfolio_summary_description()
                    LOGGER.debug(f"Portfolio value at age {current_age} - at year start:\n{portfolio_summary}")

                earned_income = self.inputs.earned_annual_income_callable(current_age)
                costs_of_living = self.inputs.annual_costs_callable(current_age)

                withdrawal = max(
                    costs_of_living - earned_income,
                    decimal.Decimal(0)
                )

                if withdrawal > 0:
                    LOGGER.debug(
                        f"Withdrawing {withdrawal / constants.MILLION:.3f} mln yen for costs of living "
                        f"from age {current_age}"
                    )

                    self.investment_manager.withdraw(desired_cash=withdrawal)

                # If after withdrawing for costs of living,
                # we still have money in our portfolio,
                # we can keep on investing
                surplus_funds = max(
                    earned_income - costs_of_living,
                    decimal.Decimal(0)
                )

                if surplus_funds > 0:

                    LOGGER.debug(
                        f"Depositing {surplus_funds / constants.MILLION:.3f} mln yen of surplus funds "
                        f"for age {current_age}"
                    )

                    self.investment_manager.deposit(
                        amount=surplus_funds,
                        age=current_age
                    )

                if LOGGER.isEnabledFor(logging.DEBUG):

                    portfolio_summary = self.investment_manager.get_formatted_portfolio_summary_description()
                    LOGGER.debug(
                        f"Portfolio value at age {current_age} - after withdrawals and deposits:\n{portfolio_summary}")

                self.investment_manager.advance_one_year()

                investment_simulation["portfolio_value"].append(self.investment_manager.portfolio_value)
                investment_simulation["after_tax_portfolio_value"].append(
                    self.investment_manager.after_tax_portfolio_value)
                investment_simulation["age"].append(current_age)
                investment_simulation["cost_of_living"].append(costs_of_living)

                current_age += 1
                current_year += 1

        finally:

            LOGGER.info("Investment simulation")
            LOGGER.info(investment_simulation)

        return investment_simulation
