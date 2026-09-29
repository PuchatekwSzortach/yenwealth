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

from . import constants, core, investments

LOGGER = logging.getLogger(__name__)


class EconomicDataSimulator:

    def __init__(self, historical_economic_data: core.EconomicData):

        self.historical_economic_data = historical_economic_data

    def generate_simulation(self, start: int, period: int, block_size: int) -> core.EconomicData:

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

        return core.EconomicData(
            return_on_assets_over_time=return_on_assets_over_time,
            inflation_over_time=inflation_over_time
        )


@dataclasses.dataclass
class FinancesSimulatorInputs:

    annual_costs_callable: core.AnnualCostsOfLiving
    earned_annual_income_callable: core.EarnedAnnualIncome
    investment_manager: investments.InvestmentManager
    simulated_economic_data: core.EconomicData
    simulation_start_age: int
    simulation_start_year: int
    simulation_end_age: int

    def __post_init__(self):

        if self.simulation_end_age < self.simulation_start_age:
            raise ValueError("simulation_end_age can't be smaller than simulation_start_age")


class FinancesSimulator:

    def __init__(self, inputs: FinancesSimulatorInputs):

        self.inputs = inputs
        self.investment_manager = self.inputs.investment_manager

    def run_simulation(self) -> pandas.DataFrame:

        current_age = self.inputs.simulation_start_age
        current_year = self.inputs.simulation_start_year

        simulation_step_count = self.inputs.simulation_end_age - self.inputs.simulation_start_age + 1

        investment_simulation = {
            "age": numpy.full(simulation_step_count, numpy.nan),
            "portfolio_value": numpy.full(simulation_step_count, numpy.nan),
            "after_tax_portfolio_value": numpy.full(simulation_step_count, numpy.nan),
            "cost_of_living": numpy.full(simulation_step_count, numpy.nan)
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

                raw_investment_returns = self.inputs.simulated_economic_data. \
                    return_on_assets_over_time.loc[current_year].to_dict()

                inflation_rate = self.inputs.simulated_economic_data.inflation_over_time.loc[current_year] \
                    .to_dict()["inflation_rate"]

                investment_returns = {key: value - inflation_rate for (key, value) in raw_investment_returns.items()}

                self.investment_manager.advance_one_year(investment_returns=investment_returns)

                simulation_index = current_age - self.inputs.simulation_start_age

                investment_simulation["portfolio_value"][simulation_index] = self.investment_manager.portfolio_value
                investment_simulation["after_tax_portfolio_value"][simulation_index] = \
                    self.investment_manager.after_tax_portfolio_value
                investment_simulation["age"][simulation_index] = current_age
                investment_simulation["cost_of_living"][simulation_index] = costs_of_living

                current_age += 1
                current_year += 1

        except investments.InsufficientFunds as error:

            LOGGER.error(error)
            return pandas.DataFrame(investment_simulation)

        return pandas.DataFrame(investment_simulation)
