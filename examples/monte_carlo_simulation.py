"""
A simple script showing how to set up MonteCarloSimulatorInputs inputs and
execute a number of simulations using the MonteCarloSimulator class, and analyze the results.
"""

import decimal
import logging
import random

import pandas

import yenwealth.analysis
import yenwealth.investments
import yenwealth.simulations


def main():

    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger(__name__)

    simulation_start_age = 30
    simulation_end_age = 85
    simulation_start_year = 2020

    deposit_strategy = yenwealth.investments.ProportionalDepositStrategy(weights={"VOO": decimal.Decimal("1.0")})
    withdrawal_strategy = yenwealth.investments.SequentialWithdrawStrategy(withdraw_order=["VOO"])

    investment_policy = yenwealth.investments.InvestmentPolicy(
        ideco=yenwealth.investments.IdecoPolicy(
            withdrawal_start_age=65,
            withdrawal_period_in_years=20
        ),
        ideco_account_deposit_strategy=deposit_strategy,
        ideco_account_withdraw_strategy=withdrawal_strategy,
        old_nisa_account_withdraw_strategy=withdrawal_strategy,
        nisa_account_deposit_strategy=deposit_strategy,
        nisa_account_withdraw_strategy=withdrawal_strategy,
        ordinary_account_deposit_strategy=deposit_strategy,
        ordinary_account_withdraw_strategy=withdrawal_strategy
    )

    economic_data_index = range(2000, 2020)

    historical_economic_data = yenwealth.simulations.core.EconomicData(
        return_on_assets_over_time=pandas.DataFrame(
            {"VOO": [decimal.Decimal(random.uniform(-0.2, 0.2)) for _ in economic_data_index]},
            index=economic_data_index),
        inflation_over_time=pandas.DataFrame(
            {"inflation_rate": [decimal.Decimal(random.uniform(0, 0.1)) for _ in economic_data_index]},
            index=economic_data_index)
    )

    inputs = yenwealth.simulations.MonteCarloSimulatorInputs(
        parameters=yenwealth.simulations.MonteCarloSimulatorParameters(
            simulation_start_age=simulation_start_age,
            simulation_end_age=simulation_end_age,
            simulation_start_year=simulation_start_year,
            simulation_count=10
        ),
        runtime=yenwealth.simulations.FinancesSimulatorRuntime(
            annual_costs_callable=lambda age: decimal.Decimal(4_000_000),
            earned_annual_income_callable=
            lambda age: decimal.Decimal(5_000_000) if age < 65 else decimal.Decimal(2_000_000),
            investment_manager=yenwealth.investments.SimpleInvestmentManager(
                ordinary_investment_account=yenwealth.investments.OrdinaryInvestmentAccount(
                    asset_map={
                        "VOO": yenwealth.investments.Asset(
                            name="VOO",
                            principal=decimal.Decimal(1_000_000),
                            gain=decimal.Decimal(0),
                            annual_management_cost_rate=decimal.Decimal("0.001")
                        )
                    }
                ),
                ideco_investment_account=yenwealth.investments.IdecoInvestmentAccount(
                    asset_map={
                        "VOO": yenwealth.investments.Asset(
                            name="VOO",
                            principal=decimal.Decimal(500_000),
                            gain=decimal.Decimal(200_000),
                            annual_management_cost_rate=decimal.Decimal("0.001")
                        )
                    },
                    contribution_start_year=2015
                ),
                old_nisa_account=yenwealth.investments.OldNisaAccount(
                    year_to_asset_map={
                        2020: {
                            "VOO": yenwealth.investments.Asset(
                                name="VOO",
                                principal=decimal.Decimal(1_000_000),
                                gain=decimal.Decimal(500_000),
                                annual_management_cost_rate=decimal.Decimal("0.001")
                            )
                        }
                    }
                ),
                nisa_account=yenwealth.investments.NisaAccount(
                    asset_map={
                        "VOO": yenwealth.investments.Asset(
                            name="VOO",
                            principal=decimal.Decimal(500_000),
                            gain=decimal.Decimal(0),
                            annual_management_cost_rate=decimal.Decimal("0.001")
                        )
                    }
                ),
                investment_policy=investment_policy,
                simulation_start_age=simulation_start_age,
                simulation_start_year=simulation_start_year
            )
        ),
        historical_economic_data=historical_economic_data
    )

    simulations = yenwealth.simulations.MonteCarloSimulator(inputs=inputs).run_simulations()

    report = yenwealth.analysis.SimulationAnalyzer().get_report(
        simulations=simulations,
        targets=[
            yenwealth.analysis.FinancialTarget(age=45, net_portfolio_value=decimal.Decimal(10_000_000)),
            yenwealth.analysis.FinancialTarget(age=70, net_portfolio_value=decimal.Decimal(5_000_000))
        ]
    )

    logger.info("\n" + report)

if __name__ == "__main__":
    main()
