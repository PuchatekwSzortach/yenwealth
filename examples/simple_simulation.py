"""
A simple script showing how to set up FinancesSimulatorInputs inputs and
execute a simulation using the FinancesSimulator class.
"""

import decimal
import functools

import pandas

import yenwealth.investments
import yenwealth.simulations
import yenwealth.utilities


def earned_annual_income(
    age: int,
    *,
    ideco_account: yenwealth.investments.IdecoInvestmentAccount,
    ideco_payout_plan: yenwealth.investments.IdecoPensionPayoutPlan,
) -> decimal.Decimal:
    income = decimal.Decimal(5_000_000) if age < 65 else decimal.Decimal(2_000_000)
    payout_end_age = ideco_payout_plan.start_age + ideco_payout_plan.period_in_years

    if ideco_payout_plan.start_age <= age < payout_end_age:
        income += ideco_account.withdraw_pension(age)

    return income


def create_simulation_inputs(
    simulation_start_age: int,
    simulation_end_age: int,
    simulation_start_year: int,
) -> yenwealth.simulations.FinancesSimulatorInputs:

    asset_purchase_strategy = yenwealth.investments.ProportionalAssetPurchaseStrategy(
        weights={"VOO": decimal.Decimal("1.0")}
    )
    asset_sale_strategy = yenwealth.investments.SequentialAssetSaleStrategy(
        sale_order=["VOO"]
    )
    ideco_payout_plan = yenwealth.investments.IdecoPensionPayoutPlan(
        start_age=65,
        period_in_years=20,
    )
    ideco_account = yenwealth.investments.IdecoInvestmentAccount(
        asset_map={
            "VOO": yenwealth.investments.Asset(
                name="VOO",
                principal=decimal.Decimal(1_000_000),
                gain=decimal.Decimal(200_000),
                annual_management_cost_rate=decimal.Decimal("0.001"),
            )
        },
        contribution_start_year=2015,
        asset_purchase_strategy=asset_purchase_strategy,
        asset_sale_strategy=asset_sale_strategy,
        ideco_pension_payout_plan=ideco_payout_plan,
    )
    income_callable = functools.partial(
        earned_annual_income,
        ideco_account=ideco_account,
        ideco_payout_plan=ideco_payout_plan,
    )

    economic_data_index = range(
        simulation_start_year,
        simulation_start_year + simulation_end_age - simulation_start_age + 1,
    )
    simulated_economic_data = yenwealth.simulations.core.EconomicData(
        return_on_assets_over_time=pandas.DataFrame(
            {"VOO": [decimal.Decimal("0.05")] * len(economic_data_index)},
            index=economic_data_index,
        ),
        inflation_over_time=pandas.DataFrame(
            {"inflation_rate": [decimal.Decimal("0.02")] * len(economic_data_index)},
            index=economic_data_index,
        ),
    )

    return yenwealth.simulations.FinancesSimulatorInputs(
        parameters=yenwealth.simulations.FinancesSimulatorParameters(
            simulation_start_age=simulation_start_age,
            simulation_end_age=simulation_end_age,
            simulation_start_year=simulation_start_year,
        ),
        runtime=yenwealth.simulations.FinancesSimulatorRuntime(
            annual_costs_callable=lambda age: decimal.Decimal(4_000_000),
            earned_annual_income_callable=income_callable,
            investment_manager=yenwealth.investments.SimpleInvestmentManager(
                ordinary_investment_account=yenwealth.investments.OrdinaryInvestmentAccount(
                    asset_map={
                        "VOO": yenwealth.investments.Asset(
                            name="VOO",
                            principal=decimal.Decimal(1_000_000),
                            gain=decimal.Decimal(0),
                            annual_management_cost_rate=decimal.Decimal("0.001"),
                        )
                    },
                    asset_purchase_strategy=asset_purchase_strategy,
                    asset_sale_strategy=asset_sale_strategy,
                ),
                ideco_investment_account=ideco_account,
                old_nisa_account=yenwealth.investments.OldNisaAccount(
                    year_to_asset_map={
                        2020: {
                            "VOO": yenwealth.investments.Asset(
                                name="VOO",
                                principal=decimal.Decimal(1_000_000),
                                gain=decimal.Decimal(500_000),
                                annual_management_cost_rate=decimal.Decimal("0.001"),
                            )
                        }
                    },
                    asset_sale_strategy=asset_sale_strategy,
                ),
                nisa_account=yenwealth.investments.NisaAccount(
                    asset_map={
                        "VOO": yenwealth.investments.Asset(
                            name="VOO",
                            principal=decimal.Decimal(500_000),
                            gain=decimal.Decimal(0),
                            annual_management_cost_rate=decimal.Decimal("0.001"),
                        )
                    },
                    asset_purchase_strategy=asset_purchase_strategy,
                    asset_sale_strategy=asset_sale_strategy,
                ),
                simulation_start_age=simulation_start_age,
                simulation_start_year=simulation_start_year,
            ),
        ),
        simulated_economic_data=simulated_economic_data,
    )


def main() -> None:
    simulation_start_age = 30
    simulation_end_age = 85
    simulation_start_year = 2020
    inputs = create_simulation_inputs(
        simulation_start_age=simulation_start_age,
        simulation_end_age=simulation_end_age,
        simulation_start_year=simulation_start_year,
    )

    simulation_result = yenwealth.simulations.FinancesSimulator(inputs=inputs).run_simulation()
    print(yenwealth.utilities.pretty_format_simulation_summary(simulation_result))


if __name__ == "__main__":
    main()
