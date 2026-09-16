"""
Module with simulation logic
"""

import dataclasses
import decimal
import logging
import typing

from . import constants
from . import investments


LOGGER = logging.getLogger(__name__)


class AnnualCostsOfLiving(typing.Protocol):
    def __call__(self, age: int) -> decimal.Decimal:
        ...


class EarnedAnnualIncome(typing.Protocol):
    def __call__(self, age: int) -> decimal.Decimal:
        ...


@dataclasses.dataclass
class LifeFinancesSimulatorInputs:

    annual_costs_of_living_callable: AnnualCostsOfLiving
    earned_annual_income_callable: EarnedAnnualIncome
    investment_manager: investments.InvestmentManager
    simulation_start_age: int
    simulation_end_age: int


class LifeFinancesSimulator:

    def __init__(self, inputs: LifeFinancesSimulatorInputs):

        self.inputs = inputs
        self.investment_manager = self.inputs.investment_manager

    def run_simulation(self) -> dict:

        LOGGER.info("Starting life finances simulation")

        current_age = self.inputs.simulation_start_age
        current_year = self.investment_manager.start_year

        investment_simulation = {
            "age": [],
            "portfolio_value": [],
            "after_tax_portfolio_value": [],
            "cost_of_living": []
        }

        if LOGGER.isEnabledFor(logging.INFO):

            portfolio_summary = self.investment_manager.get_formatted_portfolio_summary_description()
            LOGGER.debug(f"Portfolio value at simulation start:\n{portfolio_summary}")

        LOGGER.info(f"Starting simulation at age {current_age}, year {current_year}")

        try:

            # While we expect to be alive and have money in our portfolio
            while (current_age <= self.inputs.simulation_end_age) and (self.investment_manager.portfolio_value > 0):

                LOGGER.info(f"Simulating year {current_year} at age {current_age}")

                self.investment_manager.optimize_investments(age=current_age)

                if LOGGER.isEnabledFor(logging.DEBUG):

                    portfolio_summary = self.investment_manager.get_formatted_portfolio_summary_description()
                    LOGGER.debug(f"Portfolio value at age {current_age} - at year start:\n{portfolio_summary}")

                earned_income = self.inputs.earned_annual_income_callable(current_age)
                costs_of_living = self.inputs.annual_costs_of_living_callable(current_age)

                withdrawal = max(
                    costs_of_living - earned_income,
                    decimal.Decimal("0")
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
                    decimal.Decimal("0")
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

                self.investment_manager.advance_one_year(year=current_year)

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
