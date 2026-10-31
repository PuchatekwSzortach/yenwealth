# Getting started

## Set up the development environment

Install with `pip install yenwealth`

## Run an example

The deterministic example builds one `FinancesSimulatorInputs` object, runs a
single projection, and formats the result:

```sh
python examples/simple_simulation.py
```

The Monte Carlo example uses historical economic data to generate multiple
scenarios and reports how often selected portfolio targets are reached:

```sh
python examples/monte_carlo_simulation.py
```

Each example constructs investment accounts, income and cost callables, and
economic data in Python. Start from the example closest to your use case and
replace those inputs with your own assumptions.

## Inputs for a simulation

Two required inputs are `annual_costs_callable` and
`earned_annual_income_callable`. Each callable takes an age and returns an
annual `decimal.Decimal` amount in yen. Age-based logic can model changes such
as retirement, childcare costs, or other income.

Each year, the simulator compares income and costs. When income is below costs,
it withdraws the shortfall from accounts supported by the investment manager.
When income exceeds costs, it deposits the surplus according to the manager's
deposit policy. To account for your scenario, please include salary and other
cash income in `earned_annual_income_callable`, and spending in
`annual_costs_callable`.

Other simulation inputs include starting account balances and holdings,
investment purchase and sale strategies, annual management costs, the simulation
age range, and economic return and inflation data. The examples provide a
straightforward starting point that you can adapt to your scenario.

## iDeCo pension payouts

When an iDeCo account is configured, `SimpleInvestmentManager` transfers the
modeled tax-free lump sum at the payout plan's start age and starts the account's
pension mode. The manager does not withdraw periodic pension payments or add
them to income. Your `earned_annual_income_callable` must call
`withdraw_pension(age)` during the configured payout period and add each
payment to other income. Call it once per age so the account records every
scheduled payment.

The examples use this pattern:

```python
def earned_annual_income(age):

    income = decimal.Decimal(5_000_000) if age < 65 else decimal.Decimal(2_000_000)

    payout_plan = ideco_account.ideco_pension_payout_plan
    payout_end_age = payout_plan.start_age + payout_plan.period_in_years
    
    if payout_plan.start_age <= age < payout_end_age:
        income += ideco_account.withdraw_pension(age)

    return income
```

For Monte Carlo simulations, create a fresh manager, iDeCo account, and callback
inside `runtime_factory` for each scenario. The callback changes the account
state when it draws a payout.

## Money values and inflation

yenwealth subtracts inflation from each year's investment return, so projected
portfolio values stay in roughly the simulation's starting-year purchasing
power. Income, costs, and starting balances are not inflation-adjusted; provide
them on that same basis, and encode real changes in income or costs in your
age-based callables.
