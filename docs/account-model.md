# Account model

yenwealth models each account as a separate holder of named assets. An
`Asset` tracks principal, investment gain, and an annual management cost rate.
The account applies deposits, annual returns, and withdrawals according to its
configured strategies.

## Accounts

- `OrdinaryInvestmentAccount` taxes investment gains according to the configured capital gain tax
- `IdecoInvestmentAccount` accepts contributions before its configured maximum
  deposit age and exposes pension withdrawals over a configured period. The
  payout plan validates a start age from 60 through 75 and a payout period from
  5 through 20 years.
- `OldNisaAccount` keeps investments grouped by purchase year, withdraws from
  the oldest year first, and requires a purchase year's holdings to be
  liquidated after 20 years.
- `NisaAccount` tracks annual and total contribution usage and allows
  tax-free withdrawals from its holdings.

The account behavior and limits described here reflect the current
implementation. Review the source before relying on a limit or tax assumption
for financial or tax planning.

## Deposit and withdrawal order

`SimpleInvestmentManager` implements the following investment plan:

- Deposits go to iDeCo first, then NISA, then the ordinary account. It raises an
  error if configured tax-advantaged accounts reach their limits and no
  ordinary account can accept the remainder.
- Withdrawals come from the ordinary account first, then old NISA, then NISA.
  Periodic iDeCo pension withdrawals are exposed on the account API; the
  manager currently transfers only the modeled tax-free lump sum automatically.
- At the iDeCo pension start age, it withdraws the modeled tax-free lump sum
  and transfers it to the ordinary account. It also moves old NISA holdings
  after their 20-year period and can move funds from the ordinary account into
  NISA within the configured contribution limits.

## Strategies

Accounts take purchase and sale strategies as inputs. A
`ProportionalAssetPurchaseStrategy` distributes a deposit using the configured
asset weights. A `SequentialAssetSaleStrategy` sells assets in the listed order
until the requested amount is met. Custom strategies can implement the
`AssetPurchaseStrategy` or `AssetSaleStrategy` protocol.
