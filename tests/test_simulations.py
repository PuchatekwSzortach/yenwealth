"""
Tests for simulations module
"""

import decimal

import numpy
import pandas

import yenwealth.core
import yenwealth.investments
import yenwealth.simulations


class FakeInvestmentManager:

    def __init__(
        self,
        portfolio_value: decimal.Decimal,
        after_tax_portfolio_value: decimal.Decimal,
        simulation_start_year: int
    ):
        self.portfolio_value = portfolio_value
        self.after_tax_portfolio_value = after_tax_portfolio_value
        self.simulation_start_year = simulation_start_year

        self.current_year = simulation_start_year

        self.calls = []

    def get_formatted_portfolio_summary_description(self) -> str:
        return "fake portfolio"

    def optimize_investments(self):
        self.calls.append(("optimize_investments", self.current_year))

    def withdraw(self, desired_cash: decimal.Decimal):
        self.calls.append(("withdraw", desired_cash))
        self.portfolio_value -= desired_cash

    def deposit(self, amount: decimal.Decimal, age: int):
        self.calls.append(("deposit", amount, age))
        self.portfolio_value += amount

    def advance_one_year(self):
        self.current_year += 1
        self.calls.append(("advance_one_year", self.current_year))

    def get_portfolio_summary(self) -> dict[str, decimal.Decimal]:
        ...


def make_inputs(
    investment_manager: yenwealth.investments.InvestmentManager,
    *,
    start_age: int,
    end_age: int,
    costs: decimal.Decimal,
    income: decimal.Decimal,
):

    simulation_steps = end_age - start_age + 1

    simulated_economic_data = yenwealth.core.EconomicData(
        return_on_assets_over_time=pandas.DataFrame({"S&P500": [0.1] * simulation_steps}),
        inflation_over_time=pandas.DataFrame({"inflation_rate": [0.03] * simulation_steps})
    )

    return yenwealth.simulations.FinancesSimulatorInputs(
        annual_costs_callable=lambda age: costs,
        earned_annual_income_callable=lambda age: income,
        investment_manager=investment_manager,
        simulated_economic_data=simulated_economic_data,
        simulation_start_age=start_age,
        simulation_end_age=end_age
    )


def test_simulation_contains_initial_state():

    investment_manager = FakeInvestmentManager(
        portfolio_value=decimal.Decimal(123),
        after_tax_portfolio_value=decimal.Decimal(100),
        simulation_start_year=2026
    )

    simulator = yenwealth.simulations.FinancesSimulator(
        make_inputs(
            investment_manager,
            start_age=50,
            end_age=50,
            costs=decimal.Decimal(100),
            income=decimal.Decimal(100)
        )
    )

    result = simulator.run_simulation()

    assert result["age"][0] == 50
    assert result["portfolio_value"][0] == decimal.Decimal(123)
    assert result["after_tax_portfolio_value"][0] == decimal.Decimal(100)
    assert result["cost_of_living"][0] == decimal.Decimal(100)


def test_simulation_runs_until_end_age():

    investment_manager = FakeInvestmentManager(
        portfolio_value=decimal.Decimal(100),
        after_tax_portfolio_value=decimal.Decimal(100),
        simulation_start_year=2026
    )

    simulator = yenwealth.simulations.FinancesSimulator(
        make_inputs(
            investment_manager,
            start_age=50,
            end_age=52,
            costs=decimal.Decimal(0),
            income=decimal.Decimal(0),
        )
    )

    result = simulator.run_simulation()

    assert result["age"].tolist() == [50, 51, 52]


def test_simulation_stops_when_portfolio_is_depleted():

    investment_manager = FakeInvestmentManager(
        portfolio_value=decimal.Decimal(100),
        after_tax_portfolio_value=decimal.Decimal(100),
        simulation_start_year=2026
    )

    simulator = yenwealth.simulations.FinancesSimulator(
        make_inputs(
            investment_manager,
            start_age=50,
            end_age=55,
            costs=decimal.Decimal(60),
            income=decimal.Decimal(0),
        )
    )

    result = simulator.run_simulation()

    # Initial state + ages 50 and 51.
    # After withdrawing 60 at age 50, 40 remains.
    # After withdrawing 60 at age 51, the portfolio reaches -20.
    numpy.testing.assert_allclose(
        result["age"].tolist(),
        [50, 51, numpy.nan, numpy.nan, numpy.nan, numpy.nan],
        equal_nan=True
    )


def test_surplus_income_is_deposited():

    investment_manager = FakeInvestmentManager(
        portfolio_value=decimal.Decimal(100),
        after_tax_portfolio_value=decimal.Decimal(100),
        simulation_start_year=2026
    )

    simulator = yenwealth.simulations.FinancesSimulator(
        make_inputs(
            investment_manager,
            costs=decimal.Decimal(80),
            income=decimal.Decimal(100),
            start_age=50,
            end_age=51,
        )
    )

    simulator.run_simulation()

    assert ("deposit", decimal.Decimal(20), 50) in investment_manager.calls

    called_methods = {call[0] for call in investment_manager.calls}
    assert "withdraw" not in called_methods


def test_insufficient_income_causes_withdrawal():

    investment_manager = FakeInvestmentManager(
        portfolio_value=decimal.Decimal(100),
        after_tax_portfolio_value=decimal.Decimal(100),
        simulation_start_year=2026
    )

    simulator = yenwealth.simulations.FinancesSimulator(
        make_inputs(
            investment_manager,
            costs=decimal.Decimal(100),
            income=decimal.Decimal(80),
            start_age=50,
            end_age=50,
        )
    )

    simulator.run_simulation()

    assert ("withdraw", decimal.Decimal(20)) in investment_manager.calls

    called_methods = {call[0] for call in investment_manager.calls}
    assert "deposit" not in called_methods


def test_income_equal_to_costs_causes_neither():

    investment_manager = FakeInvestmentManager(
        portfolio_value=decimal.Decimal(100),
        after_tax_portfolio_value=decimal.Decimal(100),
        simulation_start_year=2026
    )

    simulator = yenwealth.simulations.FinancesSimulator(
        make_inputs(
            investment_manager,
            costs=decimal.Decimal(100),
            income=decimal.Decimal(100),
            start_age=50,
            end_age=50,
        )
    )

    simulator.run_simulation()

    called_methods = {call[0] for call in investment_manager.calls}
    assert "withdraw" not in called_methods
    assert "deposit" not in called_methods


def test_callables_are_called_with_correct_ages():

    investment_manager = FakeInvestmentManager(
        portfolio_value=decimal.Decimal(100),
        after_tax_portfolio_value=decimal.Decimal(100),
        simulation_start_year=2026
    )

    cost_ages = []
    income_ages = []

    def costs(age):
        cost_ages.append(age)
        return decimal.Decimal(100)

    def income(age):
        income_ages.append(age)
        return decimal.Decimal(80)

    inputs = make_inputs(
        investment_manager,
        start_age=50,
        end_age=52,
        costs=decimal.Decimal(100),
        income=decimal.Decimal(80)
    )

    # Replace the callables with ones that record their arguments.
    inputs.annual_costs_callable = costs
    inputs.earned_annual_income_callable = income

    simulator = yenwealth.simulations.FinancesSimulator(inputs)
    simulator.run_simulation()

    assert cost_ages == [50, 51, 52]
    assert income_ages == [50, 51, 52]


def test_investment_manager_operations_are_called_in_correct_order():

    investment_manager = FakeInvestmentManager(
        portfolio_value=decimal.Decimal(100),
        after_tax_portfolio_value=decimal.Decimal(100),
        simulation_start_year=2026
    )

    simulator = yenwealth.simulations.FinancesSimulator(
        make_inputs(
            investment_manager,
            start_age=50,
            end_age=50,
            costs=decimal.Decimal(100),
            income=decimal.Decimal(80),
        )
    )

    simulator.run_simulation()

    assert investment_manager.calls == [
        ("optimize_investments", 2026),
        ("withdraw", decimal.Decimal(20)),
        ("advance_one_year", 2027),
    ]


class TestEconomicDataSimulator:

    def test_generate_simulation_dimensions_and_index(self, sample_economic_data):

        simulator = yenwealth.simulations.EconomicDataSimulator(sample_economic_data)

        start_year = 2025
        period = 15
        block_size = 2

        simulated_data = simulator.generate_simulation(
            start=start_year, period=period, block_size=block_size
        )

        # Verify output is instance of EconomicData
        assert isinstance(simulated_data, yenwealth.core.EconomicData)

        # Verify row length matches requested period
        assert len(simulated_data.return_on_assets_over_time) == period
        assert len(simulated_data.inflation_over_time) == period

        # Verify new index starts at `start` and runs sequentially
        expected_index = pandas.RangeIndex(start=start_year, stop=start_year + period)
        pandas.testing.assert_index_equal(simulated_data.return_on_assets_over_time.index, expected_index)
        pandas.testing.assert_index_equal(simulated_data.inflation_over_time.index, expected_index)

        # Verify column integrity
        assert list(simulated_data.return_on_assets_over_time.columns) == ["Asset_A", "Asset_B"]
        assert list(simulated_data.inflation_over_time.columns) == ["Inflation"]
