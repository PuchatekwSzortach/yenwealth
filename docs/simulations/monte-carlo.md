# Monte Carlo simulation

`MonteCarloSimulator` repeats a financial projection using economic paths
resampled from historical data. Configure `MonteCarloSimulatorParameters` with
an age range, starting year, and positive simulation count. Provide
`MonteCarloSimulatorInputs` with historical `EconomicData` and a
`runtime_factory` that creates a fresh `FinancesSimulatorRuntime` for each run.

The simulator uses a stationary bootstrap and runs projections through a
reusable process executor. Each result is a pandas DataFrame with the same
shape as a deterministic simulation. `run_simulations()` returns the frames as
a list.

The complete setup is in the [Monte Carlo example](https://github.com/PuchatekwSzortach/yenwealth/blob/main/examples/monte_carlo_simulation.py).
That example uses randomly generated input data for demonstration; replace it
with a vetted historical dataset for meaningful analysis.
