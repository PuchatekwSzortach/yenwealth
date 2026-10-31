# Simulations

The simulation API separates assumptions from execution:

- `EconomicData` holds year-indexed asset returns and inflation.
- `FinancesSimulatorParameters` describes the age range and first simulation
  year.
- `FinancesSimulatorRuntime` supplies the investment manager and callables for
  annual income and living costs.
- `FinancesSimulatorInputs` combines those values with economic data.

`FinancesSimulator.run_simulation()` processes each year in order. It optimizes
investments, compares income with living costs, withdraws a shortfall or
deposits a surplus, then applies investment returns after inflation. The result
is a pandas DataFrame indexed by age, with gross and after-tax portfolio value
and living costs.

Choose a [deterministic projection](deterministic.md) for one supplied economic
path, or a [Monte Carlo projection](monte-carlo.md) to sample many paths from
historical data. [Analyze simulation results](analysis.md) to calculate target
hit counts and percentages.
