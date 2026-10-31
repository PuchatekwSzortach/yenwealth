# yenwealth

Financial planning tools for individuals living in Japan.

yenwealth simulates annual income, living costs, investment returns, and
Japanese investment accounts. The model is under active development.

## Documentation

Read the [yenwealth documentation](https://puchatekwszortach.github.io/yenwealth/)
for setup instructions, model behavior, examples, and the Python API reference.

## Examples

This example runs a deterministic simulation using ordinary and NISA accounts.

<!-- front_page_example:start -->
```python
import decimal

import pandas

import yenwealth.investments
import yenwealth.simulations
import yenwealth.utilities


def main() -> None:

    simulation_start_age = 30
    simulation_end_age = 85
    simulation_start_year = 2020

    asset_purchase_strategy = yenwealth.investments.ProportionalAssetPurchaseStrategy(
        weights={"VOO": decimal.Decimal("1.0")}
    )
    asset_sale_strategy = yenwealth.investments.SequentialAssetSaleStrategy(sale_order=["VOO"])

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

    inputs = yenwealth.simulations.FinancesSimulatorInputs(
        parameters=yenwealth.simulations.FinancesSimulatorParameters(
            simulation_start_age=simulation_start_age,
            simulation_end_age=simulation_end_age,
            simulation_start_year=simulation_start_year,
        ),
        runtime=yenwealth.simulations.FinancesSimulatorRuntime(
            annual_costs_callable=lambda age: decimal.Decimal(4_000_000),
            earned_annual_income_callable=lambda age: (
                decimal.Decimal(5_000_000) if age < 65 else decimal.Decimal(2_000_000)
            ),
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
            )
        ),
        simulated_economic_data=simulated_economic_data,
    )

    simulation_result = yenwealth.simulations.FinancesSimulator(inputs=inputs).run_simulation()
    print(yenwealth.utilities.pretty_format_simulation_summary(simulation_result))


if __name__ == "__main__":
    main()
```
<!-- front_page_example:end -->

- [`examples/simple_simulation.py`](examples/simple_simulation.py) runs one
  deterministic projection.
- [`examples/monte_carlo_simulation.py`](examples/monte_carlo_simulation.py)
  runs multiple projections and summarizes financial targets.
