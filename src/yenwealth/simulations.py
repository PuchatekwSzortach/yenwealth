"""
Module with simulation logic
"""

import dataclasses
import decimal
import itertools
import logging
import math
import typing

import arch.bootstrap
import loky
import numpy
import pandas
import tqdm

from . import constants, core, investments

LOGGER = logging.getLogger(__name__)


class EconomicDataSimulator:
    """
    Resample historical economic data into a simulated annual path.
    """

    def __init__(self, historical_economic_data: core.EconomicData):

        self.historical_economic_data = historical_economic_data

    def generate_simulation(self, start: int, period: int, block_size: int) -> core.EconomicData:
        """
        Create a stationary-bootstrap path with ``period`` annual rows.

        The returned rows use consecutive years beginning at ``start``.
        """

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


@dataclasses.dataclass(frozen=True)
class FinancesSimulatorParameters:
    """
    Set the inclusive age range and first calendar year for one projection.
    """

    simulation_start_age: int
    simulation_end_age: int
    simulation_start_year: int

    def __post_init__(self):

        if self.simulation_end_age < self.simulation_start_age:
            raise ValueError("simulation_end_age can't be smaller than simulation_start_age")


@dataclasses.dataclass
class FinancesSimulatorRuntime:
    """
    Provide the manager and age-based income and living-cost callables.
    """

    investment_manager: investments.InvestmentManager
    earned_annual_income_callable: core.EarnedAnnualIncome
    annual_costs_callable: core.AnnualCostsOfLiving


@dataclasses.dataclass
class FinancesSimulatorInputs:
    """
    Bundle parameters, runtime behavior, and one economic data path.
    """

    parameters: FinancesSimulatorParameters
    runtime: FinancesSimulatorRuntime
    simulated_economic_data: core.EconomicData


@dataclasses.dataclass(frozen=True)
class MonteCarloSimulatorParameters:
    """
    Set the inclusive age range, starting year, and positive scenario count.
    """

    simulation_start_age: int
    simulation_end_age: int
    simulation_start_year: int
    simulation_count: int

    def __post_init__(self):

        if self.simulation_end_age < self.simulation_start_age:
            raise ValueError("simulation_end_age can't be smaller than simulation_start_age")

        if self.simulation_count <= 0:
            raise ValueError("simulation_count must be a positive integer")


class FinancesSimulator:
    """
    Run one year-by-year personal finance projection.
    """

    def __init__(self, inputs: FinancesSimulatorInputs):

        self.inputs = inputs
        self.investment_manager = self.inputs.runtime.investment_manager

    def run_simulation(self) -> pandas.DataFrame:
        """
        Run the projection and return portfolio values indexed by age.

        Each year applies the investment policy, income and living costs, and
        returns after inflation. If a withdrawal cannot be met, later rows are
        returned with missing values.
        """

        current_age = self.inputs.parameters.simulation_start_age
        current_year = self.inputs.parameters.simulation_start_year

        simulation_step_count = self.inputs.parameters.simulation_end_age - \
            self.inputs.parameters.simulation_start_age + 1

        investment_simulation = {
            "age": numpy.full(simulation_step_count, numpy.nan),
            "gross_portfolio_value": numpy.full(simulation_step_count, decimal.Decimal("NaN")),
            "net_portfolio_value": numpy.full(simulation_step_count, decimal.Decimal("NaN")),
            "cost_of_living": numpy.full(simulation_step_count, decimal.Decimal("NaN"))
        }

        if LOGGER.isEnabledFor(logging.DEBUG):

            portfolio_summary = self.investment_manager.get_formatted_portfolio_summary_description()
            LOGGER.debug(f"Portfolio value at simulation start:\n{portfolio_summary}")

        try:

            # While we expect to be alive and have money in our portfolio
            while (current_age <= self.inputs.parameters.simulation_end_age) and \
                    (self.investment_manager.portfolio_value > 0):

                LOGGER.debug(f"Simulating year {current_year} at age {current_age}")

                self.investment_manager.optimize_investments()

                if LOGGER.isEnabledFor(logging.DEBUG):

                    portfolio_summary = self.investment_manager.get_formatted_portfolio_summary_description()
                    LOGGER.debug(f"Portfolio value at age {current_age} - at year start:\n{portfolio_summary}")

                earned_income = self.inputs.runtime.earned_annual_income_callable(current_age)
                costs_of_living = self.inputs.runtime.annual_costs_callable(current_age)

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

                simulation_index = current_age - self.inputs.parameters.simulation_start_age

                investment_simulation["gross_portfolio_value"][simulation_index] = \
                    self.investment_manager.portfolio_value
                investment_simulation["net_portfolio_value"][simulation_index] = \
                    self.investment_manager.after_tax_portfolio_value
                investment_simulation["age"][simulation_index] = current_age
                investment_simulation["cost_of_living"][simulation_index] = costs_of_living

                current_age += 1
                current_year += 1

        except investments.InsufficientFunds as error:

            LOGGER.debug(error)

            return pandas.DataFrame(
                investment_simulation,
                index=pandas.Index(
                    range(
                        self.inputs.parameters.simulation_start_age,
                        self.inputs.parameters.simulation_end_age + 1
                    ),
                    name="age"
                )
            )

        return pandas.DataFrame(
            investment_simulation,
            index=pandas.Index(
                range(
                    self.inputs.parameters.simulation_start_age,
                    self.inputs.parameters.simulation_end_age + 1
                ),
                name="age"
            )
        )


@dataclasses.dataclass
class MonteCarloSimulatorInputs:
    """
    Bundle scenario settings, a runtime factory, and historical data.
    """

    parameters: MonteCarloSimulatorParameters
    runtime_factory: typing.Callable[[], FinancesSimulatorRuntime]
    historical_economic_data: core.EconomicData


def _run_single_simulation(
        inputs: MonteCarloSimulatorInputs,
        economic_data_simulator: EconomicDataSimulator,
        simulation_index: int
) -> pandas.DataFrame:

    LOGGER.debug(f"Running simulation {simulation_index + 1} of {inputs.parameters.simulation_count}")

    simulated_economic_data = economic_data_simulator.generate_simulation(
        start=inputs.parameters.simulation_start_year,
        period=inputs.parameters.simulation_end_age - inputs.parameters.simulation_start_age + 1,
        block_size=5
    )

    finances_simulator_inputs = FinancesSimulatorInputs(
        parameters=FinancesSimulatorParameters(
            simulation_start_age=inputs.parameters.simulation_start_age,
            simulation_end_age=inputs.parameters.simulation_end_age,
            simulation_start_year=inputs.parameters.simulation_start_year
        ),
        runtime=inputs.runtime_factory(),
        simulated_economic_data=simulated_economic_data
    )

    return FinancesSimulator(inputs=finances_simulator_inputs).run_simulation()


class MonteCarloSimulator:
    """
    Run independent finance projections on bootstrapped economic paths.
    """

    def __init__(self, inputs: MonteCarloSimulatorInputs):

        self.inputs = inputs

    def run_simulations(self) -> list[pandas.DataFrame]:
        """
        Return one age-indexed result frame for each requested scenario.
        """

        economic_data_simulator = EconomicDataSimulator(
            historical_economic_data=self.inputs.historical_economic_data
        )

        show_progress_bar = LOGGER.isEnabledFor(logging.INFO)

        results = []

        with loky.get_reusable_executor() as executor:

            results_generator = executor.map(
                _run_single_simulation,
                itertools.repeat(self.inputs),
                itertools.repeat(economic_data_simulator),
                range(self.inputs.parameters.simulation_count),
                chunksize=64
            )

            results = list(
                tqdm.tqdm(
                    results_generator,
                    desc="Running simulations",
                    disable=not show_progress_bar,
                    total=self.inputs.parameters.simulation_count
                )
            )

        return results
