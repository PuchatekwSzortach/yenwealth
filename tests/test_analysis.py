"""
Tests for analysis module
"""

import decimal

import pandas
import pytest

import yenwealth.analysis


class TestSimulationAnalyzer:

    def test_financial_target_converts_numeric_values_to_decimal(self):

        target = yenwealth.analysis.FinancialTarget(age=60, net_portfolio_value=0.1)

        assert target.net_portfolio_value == decimal.Decimal("0.1")
        assert type(target.net_portfolio_value) is decimal.Decimal

    @pytest.mark.parametrize("value", [True, "100"])
    def test_financial_target_rejects_unsupported_values(self, value):

        with pytest.raises(TypeError, match="Expected a Decimal, int, or float"):
            yenwealth.analysis.FinancialTarget(age=60, net_portfolio_value=value)

    def test_get_target_hit_count_map_against_single_simulation(self):

        age_to_net_portfolio_value = {
            30: decimal.Decimal(100),
            31: decimal.Decimal(150),
            32: decimal.Decimal(200),
            33: decimal.Decimal(300)
        }

        simulation_data = {
            "net_portfolio_value": list(age_to_net_portfolio_value.values())
        }

        simulation_result = pandas.DataFrame(
            simulation_data,
            index=pandas.Index(age_to_net_portfolio_value.keys(), name="age")
        )

        targets = [
            yenwealth.analysis.FinancialTarget(age=31, net_portfolio_value=decimal.Decimal(140)),
            yenwealth.analysis.FinancialTarget(age=32, net_portfolio_value=decimal.Decimal(210)),
            yenwealth.analysis.FinancialTarget(age=33, net_portfolio_value=decimal.Decimal(240))
        ]

        analyzer = yenwealth.analysis.SimulationAnalyzer()
        actual_hit_count_map = analyzer.get_target_hit_count_map(simulations=[simulation_result], targets=targets)

        expected_hit_count_map = {
            targets[0]: 1,  # Target at age 31 is hit
            targets[1]: 0,  # Target at age 32 is not hit
            targets[2]: 1   # Target at age 33 is hit
        }

        assert expected_hit_count_map == actual_hit_count_map

    def test_get_target_hit_count_map_against_multiple_simulations(self):

        age_to_net_portfolio_value = {
            30: decimal.Decimal(100),
            31: decimal.Decimal(150),
            32: decimal.Decimal(200),
            33: decimal.Decimal(300)
        }

        simulation_data = {
            "age": age_to_net_portfolio_value.keys(),
            "net_portfolio_value": list(age_to_net_portfolio_value.values())
        }

        simulation_result = pandas.DataFrame(
            simulation_data,
            index=pandas.Index(age_to_net_portfolio_value.keys(), name="age")
        )

        targets = [
            yenwealth.analysis.FinancialTarget(age=31, net_portfolio_value=decimal.Decimal(140)),
            yenwealth.analysis.FinancialTarget(age=32, net_portfolio_value=decimal.Decimal(210)),
            yenwealth.analysis.FinancialTarget(age=33, net_portfolio_value=decimal.Decimal(240))
        ]

        analyzer = yenwealth.analysis.SimulationAnalyzer()

        actual_hit_count_map = analyzer.get_target_hit_count_map(
            simulations=[simulation_result, simulation_result, simulation_result], targets=targets)

        expected_hit_count_map = {
            targets[0]: 3,  # Target at age 31 is hit
            targets[1]: 0,  # Target at age 32 is not hit
            targets[2]: 3   # Target at age 33 is hit
        }

        assert expected_hit_count_map == actual_hit_count_map
