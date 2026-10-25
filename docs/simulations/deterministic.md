# Deterministic simulation

Use `FinancesSimulator` when you want to supply one economic path and inspect
the resulting annual projection. Returns and inflation are provided as
year-indexed pandas DataFrames. The return columns must match the asset names
used by the investment accounts, and the economic data index must cover every
simulation year.

The [simple simulation example](https://github.com/PuchatekwSzortach/yenwealth/blob/main/examples/simple_simulation.py)
shows the full setup. In short:

1. Create purchase and sale strategies and the accounts they use.
2. Create a `SimpleInvestmentManager` with the configured accounts.
3. Supply annual income and living-cost callables in
   `FinancesSimulatorRuntime`.
4. Combine the runtime, simulation parameters, and `EconomicData` in
   `FinancesSimulatorInputs`, then call `run_simulation()`.

The result has one row per simulated age. If a withdrawal cannot be met, the
simulator returns the rows populated up to that point; later values remain
missing.
