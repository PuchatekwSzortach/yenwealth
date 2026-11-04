# Account model

yenwealth models each account as a separate holder of named assets. An
`Asset` tracks principal, investment gain, and an annual management cost rate.
The account applies deposits, annual returns, and withdrawals according to its
configured strategies.

## Accounts

- `OrdinaryInvestmentAccount` taxes investment gains according to the configured capital gain tax
- `IdecoInvestmentAccount` requires an `IdecoContributorCategory` and applies
  the December 2026 contribution limits in every simulated year. Category 1 has
  a ¥900,000 annual shared limit; employees without a corporate pension have a
  ¥744,000 annual limit. Category 1 and employees with a corporate pension can
  pass `annual_contributions_to_other_pensions_in_yen` to subtract annual
  National Pension Fund or corporate pension contributions from their shared
  annual limit. This value is required for the corporate-pension category and
  defaults to zero for Category 1. Contributions are allowed before age 70, assuming
  eligibility for ages 65 through 69. The payout plan validates a start age
  from 60 through 75 and a payout period from 5 through 20 years.
  `SimpleInvestmentManager` starts pension mode at the configured start age
  after transferring the modeled tax-free lump sum. The user's income callback
  must still withdraw each periodic payment.
- `OldNisaAccount` keeps investments grouped by purchase year, withdraws from
  the oldest year first, and requires a purchase year's holdings to be
  liquidated after 20 years.
- `NisaAccount` tracks annual and total contribution usage and allows
  tax-free withdrawals from its holdings.

yenwealth aims to model Japanese account rules and limits in force as of
December 2026. Check the latest Japanese account rules and limits with official
sources before relying on the results.

## Numeric inputs

Account deposits, withdrawals, tax rates, return maps, and strategy weights
accept `decimal.Decimal`, `int`, and `float` values. yenwealth converts each
value to `decimal.Decimal` before arithmetic. Float conversion uses
`decimal.Decimal(str(value))`; for example, `0.1` becomes
`Decimal("0.1")`. Calculated account values remain `decimal.Decimal`.
Booleans and strings are not numeric inputs.

## Deposit and withdrawal order

`SimpleInvestmentManager` implements the following investment plan:

- Deposits go to iDeCo first, then NISA, then the ordinary account. It raises an
  error if configured tax-advantaged accounts reach their limits and no
  ordinary account can accept the remainder.
- Withdrawals come from the ordinary account first, then old NISA, then NISA.
  Periodic iDeCo pension payments are not part of this withdrawal order. The
  income callback must call `withdraw_pension(age)` and include each payment in
  annual income.
- At the iDeCo pension start age, the manager transfers the modeled tax-free
  lump sum to the ordinary account and starts pension mode.
- The manager liquidates old NISA holdings after their 20-year limit passes, depositing proceedings into an ordinary account. It can also move funds from the ordinary account into NISA within the configured
  contribution limits.

## Strategies

Accounts take purchase and sale strategies as inputs. A
`ProportionalAssetPurchaseStrategy` distributes a deposit using the configured
asset weights. A `SequentialAssetSaleStrategy` sells assets in the listed order
until the requested amount is met. Custom strategies can implement the
`AssetPurchaseStrategy` or `AssetSaleStrategy` protocol.
