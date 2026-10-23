"""
A simple script showing how to set up FinancesSimulatorInputs inputs and
execute a simulation using the FinancesSimulator class.
"""

import decimal
import logging

import pandas

import yenwealth.investments
import yenwealth.simulations
import yenwealth.utilities


def main():

    logging.basicConfig(level=logging.ERROR)
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
        )
    )

    economic_data_index = range(
        simulation_start_year,
        simulation_start_year + simulation_end_age - simulation_start_age + 1
    )

    simulated_economic_data = yenwealth.simulations.core.EconomicData(
        return_on_assets_over_time=pandas.DataFrame(
            {"VOO": [decimal.Decimal("0.05")] * len(economic_data_index)}, index=economic_data_index),
        inflation_over_time=pandas.DataFrame(
            {"inflation_rate": [decimal.Decimal("0.02")] * len(economic_data_index)}, index=economic_data_index),
    )

    inputs = yenwealth.simulations.FinancesSimulatorInputs(
        parameters=yenwealth.simulations.FinancesSimulatorParameters(
            simulation_start_age=simulation_start_age,
            simulation_end_age=simulation_end_age,
            simulation_start_year=simulation_start_year
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
                    },
                    deposit_strategy=deposit_strategy,
                    withdrawal_strategy=withdrawal_strategy
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
                    contribution_start_year=2015,
                    deposit_strategy=deposit_strategy,
                    withdrawal_strategy=withdrawal_strategy
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
                    },
                    withdrawal_strategy=withdrawal_strategy
                ),
                nisa_account=yenwealth.investments.NisaAccount(
                    asset_map={
                        "VOO": yenwealth.investments.Asset(
                            name="VOO",
                            principal=decimal.Decimal(500_000),
                            gain=decimal.Decimal(0),
                            annual_management_cost_rate=decimal.Decimal("0.001")
                        )
                    },
                    deposit_strategy=deposit_strategy,
                    withdrawal_strategy=withdrawal_strategy
                ),
                investment_policy=investment_policy,
                simulation_start_age=simulation_start_age,
                simulation_start_year=simulation_start_year
            )
        ),
        simulated_economic_data=simulated_economic_data
    )

    simulation_result = yenwealth.simulations.FinancesSimulator(inputs=inputs).run_simulation()
    logger.info(yenwealth.utilities.pretty_format_simulation_summary(simulation_result))


if __name__ == "__main__":
    main()
