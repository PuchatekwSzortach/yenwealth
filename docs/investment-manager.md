# Investment managers

[`FinancesSimulator`](reference/yenwealth/simulations/#yenwealth.simulations.FinancesSimulator)
controls the finance simulation. It's in charge of calling income and expense callables, calling appropriate methods of investment manager, moving the simulation forward along the time axis, and gathering results. An
[`InvestmentManager`](reference/yenwealth/investments/#yenwealth.investments.InvestmentManager)
handles portfolio operations: it performs deposits and withdrawals, applies investment returns, and runs account-specific events and investment policy.


You can pass
[`SimpleInvestmentManager`](reference/yenwealth/investments/#yenwealth.investments.SimpleInvestmentManager)
to the simulator, or implement your own manager to use a different account mix,
cash-management rule, or investment policy.

## The yearly interaction

For each simulated age, `FinancesSimulator.run_simulation()` performs these
steps:

1. Calls `investment_manager.process_start_of_year_account_events()`.
2. Evaluates earned income and living costs for the current age.
3. Calls `investment_manager.withdraw()` for a spending shortfall, or `investment_manager.deposit()` for a surplus.
4. Calls `investment_manager.apply_post_cash_flow_investment_policy()`.
5. Subtracts that year's inflation rate from each asset return and passes the
   resulting real return map to `investment_manager.advance_one_year()`.
6. Records gross and after-tax portfolio values for the age.

The two lifecycle methods do not receive the age or calendar year. A manager
that needs to schedule age- or year-based actions should retain its own clock.
Initialize it from the simulation start values and advance it in
`advance_one_year()`. `SimpleInvestmentManager` does this with its
`current_year` and derives the current age from the start age and year.

The simulator stops when the end age is reached or `portfolio_value` is no
longer positive. If a withdrawal raises `investments.InsufficientFunds`, the
simulator returns the projection rows completed so far; the remaining rows have
missing values.

## The `InvestmentManager` protocol

`yenwealth.investments.InvestmentManager` is a Python protocol. A custom class
can satisfy it by providing the following attributes and methods:

- `simulation_start_year`: the calendar year corresponding to the first
  simulated age.
- `portfolio_value`: gross value of all managed accounts.
- `after_tax_portfolio_value`: estimated value available after modeled taxes.
- `deposit(amount, age)`: invest a positive cash surplus for that age.
- `withdraw(desired_cash)`: raise the requested cash, or raise
  `yenwealth.investments.InsufficientFunds` if it cannot be met.
- `process_start_of_year_account_events()`: run due account events before
  income and spending are processed.
- `apply_post_cash_flow_investment_policy()`: run investment policy after the
  simulator has handled that year's income and costs.
- `advance_one_year(investment_returns)`: apply the supplied per-asset returns
  and advance the manager's clock.
- `get_portfolio_summary()` and
  `get_formatted_portfolio_summary_description()`: return account totals and a
  human-readable summary. The simulator uses the formatted description for
  debug logging.

The protocol describes the calls the simulator makes; it does not prescribe
how many accounts you keep or how you allocate money between them. Use
`decimal.Decimal` for balances and calculations, as the account implementations
do.

## Start-of-year account events

`process_start_of_year_account_events()` is the place for operations tied to a
specific age or calendar year that need to happen before the year's cash flow.
Examples include transferring holdings that have reached an account deadline,
starting a pension phase, or processing a scheduled one-time distribution.

This method runs once at the beginning of every year the simulator processes,
before it asks for income and costs. It should therefore be safe to call once
per year and should not apply that year's investment returns. Events that move
money between accounts should update both accounts and keep the manager's
reported total consistent. If an event creates cash that should be invested,
the manager can route it according to its policy here.

`SimpleInvestmentManager` provides two examples:

- It liquidates old NISA holdings when their 20-year holding period ends and
  redeposits the proceeds to configured accounts.
- At the configured iDeCo payout start age, it transfers the modeled tax-free
  lump sum to other accounts and starts iDeCo pension mode. Periodic iDeCo
  payments are requested separately by the user's income callback via
  `withdraw_pension(age)`; the manager does not add them to income itself.

If you implement your own manager with iDeCo or another account that pays
income, decide whether the callback or the manager initiates each payment and
keep that responsibility consistent. The simulator only sees the amount
returned by the income callback.

## Post-cash-flow investment policy

`apply_post_cash_flow_investment_policy()` runs after the simulator has handled
spending and surplus income, but before returns are applied. Use it for
rebalancing, moving idle cash, filling contribution room, or other rules that
should see the portfolio after this year's cash flow.

The method receives no amount. It should inspect the manager's current account
state and apply its own policy. Transfers between accounts should preserve
total portfolio value apart from modeled fees, taxes, or rounding, and should
respect each destination account's limits. It may do nothing when no eligible
transfer is available. Avoid repeating the simulator's cash-flow step here:
surplus income has already been passed to `deposit()`, and spending shortfalls
have already been passed to `withdraw()`.

In `SimpleInvestmentManager`, the policy attempts transfers in this order:

1. Ordinary account to iDeCo, up to remaining iDeCo contribution room.
2. NISA to iDeCo, if iDeCo room remains.
3. Ordinary account to NISA, up to remaining NISA contribution room.

Each transfer is capped by both the source's available funds and the
destination's remaining contribution capacity. That policy is an example, not
a requirement of the protocol.

## Implementing a custom manager

Here is a structural outline. Replace the event and policy comments with your
account-specific operations, and make sure every portfolio value includes all
assets managed by the class.

```python
import collections.abc
import decimal

import yenwealth.investments
import yenwealth.numeric


class MyInvestmentManager:
    def __init__(self, *, simulation_start_age: int, simulation_start_year: int):
        self.simulation_start_age = simulation_start_age
        self.simulation_start_year = simulation_start_year
        self.current_year = simulation_start_year
        # Initialize your accounts here.

    @property
    def current_age(self) -> int:
        return self.simulation_start_age + self.current_year - self.simulation_start_year

    @property
    def portfolio_value(self) -> decimal.Decimal:
        # Return the sum of gross values across all your accounts.
        ...

    @property
    def after_tax_portfolio_value(self) -> decimal.Decimal:
        # Return your estimate of the value available after modeled taxes.
        ...

    def process_start_of_year_account_events(self) -> None:
        if self.current_age == 65:
            # Process any event scheduled for age 65.
            ...

    def withdraw(self, desired_cash: yenwealth.numeric.DecimalInput) -> None:
        # Raise yenwealth.investments.InsufficientFunds if the cash is unavailable.
        ...

    def deposit(self, amount: yenwealth.numeric.DecimalInput, age: int) -> None:
        # Allocate the surplus among your accounts.
        ...

    def apply_post_cash_flow_investment_policy(self) -> None:
        # Rebalance or transfer funds based on the post-cash-flow balances.
        ...

    def advance_one_year(
        self,
        investment_returns: collections.abc.Mapping[str, yenwealth.numeric.DecimalInput],
    ) -> None:
        # Apply each asset's supplied real return to all managed accounts.
        ...
        self.current_year += 1

    def get_portfolio_summary(self) -> dict[str, decimal.Decimal]:
        ...

    def get_formatted_portfolio_summary_description(self) -> str:
        ...
```

`FinancesSimulatorRuntime` groups an `InvestmentManager` instance with the
income and living-cost callbacks. For a single deterministic run, set its
`investment_manager` field to your custom manager, then pass the runtime in
`FinancesSimulatorInputs` to `FinancesSimulator`.

For a Monte Carlo run, set `MonteCarloSimulatorInputs.runtime_factory` to a
no-argument function that returns a new `FinancesSimulatorRuntime`.
`MonteCarloSimulator` calls this function once per scenario and uses the
returned runtime for that scenario's `FinancesSimulator`. Create the manager,
its account objects, and any stateful callbacks inside the factory so each
scenario starts with independent state.

For a complete working example of the standard account setup, see the
[deterministic simulation guide](simulations/deterministic.md). For the
included account rules and `SimpleInvestmentManager` priorities, see the
[account model](account-model.md).
