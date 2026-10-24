"""
Module with investment logic
"""

import collections
import copy
import dataclasses
import decimal
import logging
import typing

import beartype
import pydantic
import returns.maybe

from . import constants, utilities

LOGGER = logging.getLogger(__name__)


class InsufficientFunds(Exception):

    pass


@beartype.beartype
class Asset:

    def __init__(
            self, name: str,
            principal: decimal.Decimal,
            gain: decimal.Decimal,
            annual_management_cost_rate: decimal.Decimal):

        self.name = name
        self.principal = principal
        self.gain = gain
        self.annual_management_cost_rate = annual_management_cost_rate

    @property
    def value(self) -> decimal.Decimal:
        return (self.principal + self.gain).quantize(constants.YEN, decimal.ROUND_DOWN)

    def advance_one_year(self, change_rate: decimal.Decimal):

        self.gain += self.value * (change_rate - self.annual_management_cost_rate)

    def sell(self, amount: decimal.Decimal):

        if amount < 0:
            raise ValueError(f"amount value should be non-negative, got {amount}")

        if amount > self.value:
            raise InsufficientFunds(
                f"amount value {amount} exceeds current value {self.value}"
            )

        gain_ratio = self.gain / self.value

        withdrawal_from_gain = gain_ratio * amount
        withdrawal_from_principal = amount - withdrawal_from_gain

        self.principal -= withdrawal_from_principal
        self.gain -= withdrawal_from_gain

    def buy(self, amount: decimal.Decimal):

        if amount <= 0:
            raise ValueError(f"amount value should be non-negative, got {amount}")

        self.principal += amount


@typing.runtime_checkable
@beartype.beartype
class AssetPurchaseStrategy(typing.Protocol):

    @property
    def asset_names(self) -> set[str]:
        ...

    def allocate(
        self,
        amount: decimal.Decimal,
        assets: list[str],
    ) -> dict[str, decimal.Decimal]:
        ...


class ProportionalAssetPurchaseStrategy(AssetPurchaseStrategy):

    def __init__(self, weights: dict[str, decimal.Decimal]):

        if len(weights.keys()) == 0:
            raise ValueError("At least one asset name must be provided")

        self.weights = weights

    @property
    def asset_names(self) -> set[str]:
        return set(self.weights)

    def allocate(self, amount: decimal.Decimal, assets: list[str]) -> dict[str, decimal.Decimal]:

        missing = set(assets) - self.weights.keys()

        if missing:
            raise ValueError(f"Missing weights for assets: {missing}")

        weights = {
            asset: self.weights[asset]
            for asset in assets
        }

        total_weight = sum(weights.values(), decimal.Decimal(0))

        if total_weight <= 0:
            raise ValueError("Total weight must be positive")

        return {
            asset: amount * weight / total_weight
            for asset, weight in weights.items()
        }


@typing.runtime_checkable
@beartype.beartype
class AssetSaleStrategy(typing.Protocol):

    @property
    def asset_names(self) -> set[str]:
        ...

    def calculate_withdrawal_amounts(
        self,
        amount: decimal.Decimal,
        asset_map: dict[str, decimal.Decimal],
    ) -> dict[str, decimal.Decimal]:
        ...


def _validate_strategy_asset_names(
    account_name: str,
    account_asset_names: typing.Collection[str],
    strategies: dict[str, AssetPurchaseStrategy | AssetSaleStrategy]
) -> None:

    account_asset_names = set(account_asset_names)

    for strategy_name, strategy in strategies.items():
        strategy_asset_names = set(strategy.asset_names)

        if account_asset_names != strategy_asset_names:
            raise ValueError(
                f"Asset names for {account_name} do not match {strategy_name}: "
                f"account assets {sorted(account_asset_names)}, strategy assets {sorted(strategy_asset_names)}"
            )


class SequentialAssetSaleStrategy(AssetSaleStrategy):

    def __init__(self, sale_order: list[str]):

        if len(sale_order) == 0:
            raise ValueError("At least one asset name must be provided")

        self.sale_order = sale_order

    @property
    def asset_names(self) -> set[str]:
        return set(self.sale_order)

    def calculate_withdrawal_amounts(
        self,
        amount: decimal.Decimal,
        asset_map: dict[str, decimal.Decimal],
    ) -> dict[str, decimal.Decimal]:

        target_asset_map = {name: value for (name, value) in asset_map.items() if name in set(self.sale_order)}

        asset_value = sum(target_asset_map.values(), decimal.Decimal(0)).quantize(constants.YEN, decimal.ROUND_DOWN)

        if asset_value < amount:

            message = (
                f"Insufficient funds {asset_value} among target assets to calculate "
                f"withdrawal plan for amount {amount}."
            )

            raise InsufficientFunds(message)

        remaining = amount
        withdrawals = {}

        for asset_name in self.sale_order:

            withdrawal = min(remaining, target_asset_map[asset_name])

            if withdrawal > 0:
                withdrawals[asset_name] = withdrawal

            remaining -= withdrawal

            if remaining == 0:
                return withdrawals

        raise RuntimeError("Unexpected code path")


@beartype.beartype
class OrdinaryInvestmentAccount:

    def __init__(
        self,
        asset_map: dict[str, Asset],
        asset_purchase_strategy: AssetPurchaseStrategy,
        asset_sale_strategy: AssetSaleStrategy,
        capital_gain_tax_rate: decimal.Decimal = decimal.Decimal("0.20325")
    ):

        self.capital_gain_tax_rate = capital_gain_tax_rate
        self.asset_map = asset_map
        self.asset_purchase_strategy = asset_purchase_strategy
        self.asset_sale_strategy = asset_sale_strategy

        _validate_strategy_asset_names(
            account_name="ordinary investment account",
            account_asset_names=self.asset_map,
            strategies={
                "asset_purchase_strategy": self.asset_purchase_strategy,
                "asset_sale_strategy": self.asset_sale_strategy,
            }
        )

    @property
    def portfolio_value(self) -> decimal.Decimal:
        return decimal.Decimal(
            sum((asset.value for asset in self.asset_map.values()), decimal.Decimal(0))
        ).quantize(constants.YEN, decimal.ROUND_DOWN)

    def deposit(self, amount: decimal.Decimal):

        if amount <= 0:
            raise ValueError(f"Deposit amount should be positive, got {amount}")

        allocations = self.asset_purchase_strategy.allocate(
            amount=amount,
            assets=list(self.asset_map.keys())
        )

        for name, allocation in allocations.items():
            self.asset_map[name].buy(allocation)

    def advance_one_year(self, investment_returns: dict[str, decimal.Decimal]):

        for name, asset in self.asset_map.items():
            asset.advance_one_year(investment_returns[name])

    def _get_net_asset_value(self, asset: Asset) -> decimal.Decimal:
        taxable_gain = max(asset.gain, decimal.Decimal(0))
        return asset.value - (taxable_gain * self.capital_gain_tax_rate)

    @property
    def _asset_to_net_value_map(self) -> dict[str, decimal.Decimal]:
        return {
            name: self._get_net_asset_value(asset)
            for name, asset in self.asset_map.items()
        }

    def withdraw(self, desired_cash: decimal.Decimal):

        if desired_cash > self.max_cash_withdrawal:
            raise InsufficientFunds(
                f"Withdrawal value {desired_cash} exceeds maximum cash withdrawal {self.max_cash_withdrawal}"
            )

        net_cash_withdrawals = self.asset_sale_strategy.calculate_withdrawal_amounts(
            amount=desired_cash,
            asset_map=self._asset_to_net_value_map
        )

        for name, net_sale in net_cash_withdrawals.items():

            asset = self.asset_map[name]
            taxable_gain = max(asset.gain, decimal.Decimal(0))
            gain_ratio = taxable_gain / asset.value
            net_proceeds_ratio = 1 - (gain_ratio * self.capital_gain_tax_rate)
            gross_sale = net_sale / net_proceeds_ratio

            asset.sell(gross_sale)

    @property
    def max_cash_withdrawal(self) -> decimal.Decimal:

        net_values = self._asset_to_net_value_map.values()
        return decimal.Decimal(sum(net_values, decimal.Decimal(0))).quantize(constants.YEN, decimal.ROUND_DOWN)


class IdecoPayoutPlan(pydantic.BaseModel):
    payout_start_age: int
    payout_period_in_years: int


@beartype.beartype
class IdecoInvestmentAccount:

    def __init__(
        self,
        asset_map: dict[str, Asset],
        contribution_start_year: int,
        asset_purchase_strategy: AssetPurchaseStrategy,
        asset_sale_strategy: AssetSaleStrategy,
        ideco_payout_plan: IdecoPayoutPlan
    ):

        self.asset_map = asset_map
        self.contribution_start_year = contribution_start_year
        self.asset_purchase_strategy = asset_purchase_strategy
        self.asset_sale_strategy = asset_sale_strategy
        self.ideco_payout_plan = ideco_payout_plan

        _validate_strategy_asset_names(
            account_name="ideco investment account",
            account_asset_names=self.asset_map,
            strategies={
                "asset_purchase_strategy": self.asset_purchase_strategy,
                "asset_sale_strategy": self.asset_sale_strategy,
            }
        )

        self.max_annual_contribution = decimal.Decimal("0.276") * constants.MILLION
        self.max_deposit_age = 65
        self.minimum_withdrawal_start_age = 60
        self.maximum_withdrawal_start_age = 75

        self.has_started_drawing_pension = False
        self.maybe_pension_period_in_years: returns.maybe.Maybe[int] = returns.maybe.Nothing
        self.maybe_pension_schema_start_age: returns.maybe.Maybe[int] = returns.maybe.Nothing
        self.pension_payout_ages: list[int] = []

    @property
    def portfolio_value(self) -> decimal.Decimal:
        return decimal.Decimal(
            sum((asset.value for asset in self.asset_map.values()), decimal.Decimal(0))
        ).quantize(constants.YEN, decimal.ROUND_DOWN)

    def deposit(self, amount: decimal.Decimal, age: int):

        if age >= self.max_deposit_age:
            raise ValueError(f"Deposit age {age} exceeds maximum allowed deposit age of {self.max_deposit_age}")

        if amount <= 0:
            raise ValueError(f"Deposit amount should be positive, got {amount}")

        if amount > self.max_annual_contribution:
            raise ValueError(
                f"Deposit amount {amount} exceeds maximum allowed contribution of {self.max_annual_contribution}")

        allocations = self.asset_purchase_strategy.allocate(
            amount=amount,
            assets=list(self.asset_map.keys())
        )

        for name, allocation in allocations.items():
            self.asset_map[name].buy(allocation)

    def advance_one_year(self, investment_returns: dict[str, decimal.Decimal]):

        for name, asset in self.asset_map.items():
            asset.advance_one_year(investment_returns[name])

    def start_pension_scheme(self, start_age: int, period_in_years: int):

        if start_age < self.minimum_withdrawal_start_age or start_age > self.maximum_withdrawal_start_age:
            raise ValueError(f"Age {start_age} outside of valid withdrawal start age")

        self.has_started_drawing_pension = True
        self.maybe_pension_period_in_years = returns.maybe.Some(period_in_years)
        self.maybe_pension_schema_start_age = returns.maybe.Some(start_age)

    def withdraw_pension(self, age: int) -> decimal.Decimal:

        if self.has_started_drawing_pension is False:
            raise ValueError("pension scheme not initialized")

        if self.maybe_pension_schema_start_age is returns.maybe.Nothing:
            raise ValueError("pension schema start age not initialized")

        if self.maybe_pension_period_in_years is returns.maybe.Nothing:
            raise ValueError("pension period not initialized")

        pension_schema_start_age = self.maybe_pension_schema_start_age.unwrap()
        pension_period_in_years = self.maybe_pension_period_in_years.unwrap()

        # Check that paid pension history exists for all years between start age and age below this
        if sorted(self.pension_payout_ages) != list(range(pension_schema_start_age, age)):
            raise ValueError("missing pension withdrawal for same ages")

        if age > pension_schema_start_age + pension_period_in_years:
            raise ValueError("iDeCo pension scheme finished")

        withdrawal_proportion = decimal.Decimal(1) / decimal.Decimal(
            pension_period_in_years - len(self.pension_payout_ages))

        withdrawal = self.portfolio_value * withdrawal_proportion
        self._withdraw(withdrawal)
        self.pension_payout_ages.append(age)

        return withdrawal

    def _withdraw(self, amount: decimal.Decimal):

        withdrawals = self.asset_sale_strategy.calculate_withdrawal_amounts(
            amount=amount,
            asset_map={name: asset.value for name, asset in self.asset_map.items()}
        )

        for name, withdrawal in withdrawals.items():
            self.asset_map[name].sell(withdrawal)

    def get_max_allowed_tax_free_lump_withdrawal_amount(self, year: int) -> decimal.Decimal:

        if year < self.contribution_start_year:
            raise ValueError(f"Year {year} has to be larger than account start year {self.contribution_start_year}")

        years_since_account_started = year - self.contribution_start_year

        # Max tax free lump sum depends on how long ago ideco account was established
        return \
            (decimal.Decimal(400_000) * min(years_since_account_started, 20)) + \
            (decimal.Decimal(700_000) * max(years_since_account_started - 20, 0))

    def withdraw_tax_free_lump_sum(self, year: int) -> decimal.Decimal:

        if year < self.contribution_start_year:
            raise ValueError(f"Year {year} has to be larger than account start year {self.contribution_start_year}")

        amount_withdrawn = min(self.portfolio_value, self.get_max_allowed_tax_free_lump_withdrawal_amount(year))
        self._withdraw(amount_withdrawn)
        return amount_withdrawn


@beartype.beartype
class OldNisaAccount:
    """
    Old NISA account that no longer allows deposit, and requires investments to be withdrawn within 20 years
    from when they were made.
    """

    def __init__(
        self,
        year_to_asset_map: dict[int, dict[str, Asset]],
        asset_sale_strategy: AssetSaleStrategy
    ):

        self.year_to_asset_map = copy.deepcopy(year_to_asset_map)
        self.asset_sale_strategy = asset_sale_strategy

        _validate_strategy_asset_names(
            account_name="old nisa account",
            account_asset_names={
                name
                for asset_map in self.year_to_asset_map.values()
                for name in asset_map
            },
            strategies={"asset_sale_strategy": self.asset_sale_strategy}
        )

    def advance_one_year(self, investment_returns: dict[str, decimal.Decimal], year: int):

        for investment_year, asset_map in self.year_to_asset_map.items():

            if investment_year + 20 < year:
                raise ValueError(f"nisa investment for year {investment_year} must be liquidated")

            for name, asset in asset_map.items():
                asset.advance_one_year(investment_returns[name])

    @property
    def portfolio_value(self) -> decimal.Decimal:

        return decimal.Decimal(
            sum(
                (asset.value for asset_map in self.year_to_asset_map.values() for asset in asset_map.values()),
                decimal.Decimal(0)
            )
        ).quantize(constants.YEN, decimal.ROUND_DOWN)

    def withdraw_for_year(
        self,
        portfolio_year: int,
        desired_cash: decimal.Decimal
    ):
        """
        Withdraw from portfolio established on portfolio_year
        """

        asset_map = self.year_to_asset_map[portfolio_year]
        portfolio_value = decimal.Decimal(sum((asset.value for asset in asset_map.values()), decimal.Decimal(0)))

        if portfolio_value < desired_cash:
            raise ValueError(f"Portfolio value for {portfolio_year} is not large enough")

        withdrawals = self.asset_sale_strategy.calculate_withdrawal_amounts(
            amount=desired_cash,
            asset_map={name: asset.value for name, asset in asset_map.items()}
        )

        for name, withdrawal in withdrawals.items():
            asset_map[name].sell(withdrawal)

    def withdraw(self, desired_cash: decimal.Decimal):
        """
        Withdraw from portfolio in order of oldest to newest
        """

        if desired_cash < 0:
            raise ValueError(f"Withdrawal value should be non-negative, got {desired_cash}")

        if desired_cash > self.portfolio_value:
            raise InsufficientFunds(
                f"Withdrawal value {desired_cash} exceeds portfolio value {self.portfolio_value}"
            )

        total_withdrawal = decimal.Decimal(0)

        for investment_year in sorted(self.year_to_asset_map.keys()):

            year_portfolio_value = decimal.Decimal(
                sum((asset.value for asset in self.year_to_asset_map[investment_year].values()), decimal.Decimal(0))
            )
            withdrawal_from_year = min(desired_cash - total_withdrawal, year_portfolio_value)

            self.withdraw_for_year(
                portfolio_year=investment_year,
                desired_cash=withdrawal_from_year
            )
            total_withdrawal += withdrawal_from_year

            if total_withdrawal == desired_cash:
                return


@beartype.beartype
class NisaAccount:
    """
    NISA account
    """

    def __init__(
        self,
        asset_map: dict[str, Asset],
        asset_purchase_strategy: AssetPurchaseStrategy,
        asset_sale_strategy: AssetSaleStrategy
    ):

        self.annual_deposit_limit = decimal.Decimal("3.6") * constants.MILLION
        self.total_deposit_limit = decimal.Decimal(18) * constants.MILLION
        self.asset_map = asset_map
        self.asset_purchase_strategy = asset_purchase_strategy
        self.asset_sale_strategy = asset_sale_strategy

        _validate_strategy_asset_names(
            account_name="nisa account",
            account_asset_names=self.asset_map,
            strategies={
                "asset_purchase_strategy": self.asset_purchase_strategy,
                "asset_sale_strategy": self.asset_sale_strategy,
            }
        )

        if self.principal > self.total_deposit_limit:
            raise ValueError(f"Principal {self.principal} exceeds total deposit limit of {self.total_deposit_limit}")

        self.year_to_deposit_map = collections.defaultdict(decimal.Decimal)

    @property
    def principal(self) -> decimal.Decimal:
        return decimal.Decimal(sum((asset.principal for asset in self.asset_map.values()), decimal.Decimal(0)))

    @property
    def portfolio_value(self) -> decimal.Decimal:
        return decimal.Decimal(
            sum((asset.value for asset in self.asset_map.values()), decimal.Decimal(0))
        ).quantize(constants.YEN, decimal.ROUND_DOWN)

    def deposit(self, amount: decimal.Decimal, year: int):

        if amount <= 0:
            raise ValueError(f"Deposit amount should be positive, got {amount}")

        if self.principal + amount > self.total_deposit_limit:

            message = f"With deposit {amount}, principal would exceed total deposit limit of {self.total_deposit_limit}"
            raise ValueError(message)

        deposit_for_target_year = self.year_to_deposit_map[year]

        if deposit_for_target_year + amount > self.annual_deposit_limit:
            message = (
                f"With deposit {amount}, annual deposit limit of {self.annual_deposit_limit} would be exceeded. "
                f"Current deposit for year {year} is {deposit_for_target_year}"
            )
            raise ValueError(message)

        allocations = self.asset_purchase_strategy.allocate(
            amount=amount,
            assets=list(self.asset_map.keys())
        )

        for name, allocation in allocations.items():
            self.asset_map[name].buy(allocation)

        self.year_to_deposit_map[year] += amount

    def advance_one_year(self, investment_returns: dict[str, decimal.Decimal]):

        for name, asset in self.asset_map.items():
            asset.advance_one_year(investment_returns[name])

    def withdraw(self, desired_cash: decimal.Decimal):

        if desired_cash < 0:
            raise ValueError(f"Withdrawal value should be non-negative, got {desired_cash}")

        if desired_cash > self.portfolio_value:
            raise InsufficientFunds(f"Withdrawal value {desired_cash} exceeds portfolio value {self.portfolio_value}")

        withdrawals = self.asset_sale_strategy.calculate_withdrawal_amounts(
            amount=desired_cash,
            asset_map={name: asset.value for name, asset in self.asset_map.items()}
        )

        for name, withdrawal in withdrawals.items():
            self.asset_map[name].sell(withdrawal)


class InvestmentManager(typing.Protocol):

    simulation_start_year: int

    @property
    def portfolio_value(self) -> decimal.Decimal:
        ...

    @property
    def after_tax_portfolio_value(self) -> decimal.Decimal:
        ...

    def advance_one_year(self, investment_returns: dict):
        ...

    def deposit(self, amount: decimal.Decimal, age: int):
        ...

    def withdraw(self, desired_cash: decimal.Decimal):
        ...

    def optimize_investments(self):
        ...

    def get_portfolio_summary(self) -> dict[str, decimal.Decimal]:
        ...

    def get_formatted_portfolio_summary_description(self) -> str:
        ...


type _ConfiguredInvestmentAccount = (
    OrdinaryInvestmentAccount | IdecoInvestmentAccount | OldNisaAccount | NisaAccount
)
type _WithdrawableInvestmentAccount = (
    OrdinaryInvestmentAccount | OldNisaAccount | NisaAccount
)


@dataclasses.dataclass(frozen=True)
class _DepositAction:
    """Encapsulate a prioritized deposit operation for one account.

    ``deposit_up_to`` performs the deposit and returns the amount deposited.
    ``account_name`` is used in log messages.
    """

    deposit_up_to: typing.Callable[[decimal.Decimal], decimal.Decimal]
    account_name: str


@dataclasses.dataclass(frozen=True)
class _WithdrawalSource:
    """Describe an account's available cash and withdrawal priority."""

    account: _WithdrawableInvestmentAccount
    available_cash: decimal.Decimal
    account_name: str


class SimpleInvestmentManager:
    """
    Investment manager with a strategy that:
    - prioritizes depositing into iDeCo, NISA, and then ordinary account
    - prioritizes withdrawing from ordinary account, old NISA, and then NISA
    - withdraws half iDeCO funds at pension start time,
    """

    def __init__(
        self,
        *,
        ordinary_investment_account: OrdinaryInvestmentAccount | None = None,
        ideco_investment_account: IdecoInvestmentAccount | None = None,
        old_nisa_account: OldNisaAccount | None = None,
        nisa_account: NisaAccount | None = None,
        simulation_start_age: int,
        simulation_start_year: int
    ):

        if all(
            account is None
            for account in (
                ordinary_investment_account,
                ideco_investment_account,
                old_nisa_account,
                nisa_account,
            )
        ):
            raise ValueError("At least one investment account must be configured")

        self.ordinary_investment_account = ordinary_investment_account
        self.ideco_investment_account = ideco_investment_account
        self.old_nisa_account = old_nisa_account
        self.nisa_account = nisa_account
        self.simulation_start_age = simulation_start_age
        self.simulation_start_year = simulation_start_year

        self.current_year = simulation_start_year

    @property
    def _current_age(self) -> int:
        return self.simulation_start_age + self.current_year - self.simulation_start_year

    @property
    def _configured_accounts(self) -> dict[str, _ConfiguredInvestmentAccount]:
        """Return configured accounts in their stable portfolio order."""

        return {
            account_name: account
            for account_name, account in (
                ("ordinary_investment_account", self.ordinary_investment_account),
                ("ideco_investment_account", self.ideco_investment_account),
                ("old_nisa_account", self.old_nisa_account),
                ("nisa_account", self.nisa_account),
            )
            if account is not None
        }

    def _build_deposit_actions(
        self,
        age: int,
    ) -> list[_DepositAction]:
        """Build deposit operations in account priority order.

        Each action caps the requested amount according to the account's remaining
        capacity, performs the deposit, and returns the deposited amount.
        """

        actions: list[_DepositAction] = []
        ideco_account = self.ideco_investment_account

        if ideco_account is not None and age < ideco_account.max_deposit_age:

            def deposit_to_ideco(requested_amount: decimal.Decimal) -> decimal.Decimal:
                amount = min(requested_amount, ideco_account.max_annual_contribution)
                if amount > 0:
                    ideco_account.deposit(amount, age=age)
                return amount

            actions.append(
                _DepositAction(
                    deposit_up_to=deposit_to_ideco,
                    account_name="iDeCo",
                )
            )

        nisa_account = self.nisa_account

        if nisa_account is not None:

            def deposit_to_nisa(requested_amount: decimal.Decimal) -> decimal.Decimal:

                capacity = min(
                    nisa_account.total_deposit_limit - nisa_account.principal,
                    nisa_account.annual_deposit_limit
                    - nisa_account.year_to_deposit_map[self.current_year],
                )

                amount = min(requested_amount, max(capacity, decimal.Decimal(0)))

                if amount > 0:
                    nisa_account.deposit(amount, year=self.current_year)

                return amount

            actions.append(
                _DepositAction(
                    deposit_up_to=deposit_to_nisa,
                    account_name="NISA",
                )
            )

        ordinary_account = self.ordinary_investment_account

        if ordinary_account is not None:

            def deposit_to_ordinary(requested_amount: decimal.Decimal) -> decimal.Decimal:
                if requested_amount > 0:
                    ordinary_account.deposit(requested_amount)
                    return requested_amount
                return decimal.Decimal(0)

            actions.append(
                _DepositAction(
                    deposit_up_to=deposit_to_ordinary,
                    account_name="ordinary investment",
                )
            )

        return actions

    def _build_withdrawal_sources(self) -> list[_WithdrawalSource]:
        """Build withdrawal sources in account priority order."""

        sources: list[_WithdrawalSource] = []

        if self.ordinary_investment_account is not None:
            sources.append(
                _WithdrawalSource(
                    account=self.ordinary_investment_account,
                    available_cash=self.ordinary_investment_account.max_cash_withdrawal,
                    account_name="ordinary investment",
                )
            )

        if self.old_nisa_account is not None:
            sources.append(
                _WithdrawalSource(
                    account=self.old_nisa_account,
                    available_cash=self.old_nisa_account.portfolio_value,
                    account_name="old NISA",
                )
            )

        if self.nisa_account is not None:
            sources.append(
                _WithdrawalSource(
                    account=self.nisa_account,
                    available_cash=self.nisa_account.portfolio_value,
                    account_name="NISA",
                )
            )

        return sources

    @property
    def portfolio_value(self) -> decimal.Decimal:
        return sum(
            (account.portfolio_value for account in self._configured_accounts.values()),
            decimal.Decimal(0),
        )

    @property
    def after_tax_portfolio_value(self) -> decimal.Decimal:
        return sum(
            (
                account.max_cash_withdrawal
                if isinstance(account, OrdinaryInvestmentAccount)
                else account.portfolio_value
                for account in self._configured_accounts.values()
            ),
            decimal.Decimal(0),
        )

    def advance_one_year(self, investment_returns: dict):

        for account in self._configured_accounts.values():
            if isinstance(account, OldNisaAccount):
                account.advance_one_year(investment_returns, self.current_year)
            else:
                account.advance_one_year(investment_returns)

        self.current_year += 1

    def deposit(self, amount: decimal.Decimal, age: int):

        if amount <= 0:
            raise ValueError(f"Deposit amount should be positive, got {amount}")

        remaining_amount = amount

        for action in self._build_deposit_actions(age):
            deposited_amount = action.deposit_up_to(remaining_amount)

            if deposited_amount > 0:
                remaining_amount -= deposited_amount

                LOGGER.debug(
                    f"Deposited {utilities.format_million_yen(deposited_amount)} to {action.account_name} account")

                if remaining_amount == 0:
                    return

        if remaining_amount > 0:
            raise ValueError(
                "Cannot deposit the remaining amount because ordinary investment account is not configured, "
                "and deposit limits of other available accounts were exhausted"
            )

    def withdraw(self, desired_cash: decimal.Decimal):

        desired_cash = desired_cash.quantize(constants.YEN, decimal.ROUND_UP)

        if desired_cash <= 0:
            raise ValueError(f"Withdrawal value should be positive, got {desired_cash}")

        remaining_cash = desired_cash

        for source in self._build_withdrawal_sources():
            withdrawal = min(remaining_cash, source.available_cash)

            if withdrawal > 0:
                source.account.withdraw(withdrawal)
                remaining_cash -= withdrawal

                LOGGER.debug(
                    f"Withdrew {utilities.format_million_yen(withdrawal)} from {source.account_name} account")

                if remaining_cash == 0:
                    return

        if remaining_cash > 0:

            raise InsufficientFunds(f"Not enough funds to withdraw {desired_cash}")

    def optimize_investments(self):
        """
        Optimize investments based on the investment policy.
        """

        # Check if any old nisa account portfolio has to be liquidated
        if self.old_nisa_account is not None and (self.current_year - 20) in self.old_nisa_account.year_to_asset_map:

            expired_year = self.current_year - 20
            asset_map = self.old_nisa_account.year_to_asset_map[expired_year]
            portfolio_value = decimal.Decimal(sum((asset.value for asset in asset_map.values()), decimal.Decimal(0)))

            self.old_nisa_account.year_to_asset_map.pop(expired_year)

            if portfolio_value > 0:

                if self.ordinary_investment_account is None:
                    raise ValueError(
                        "Cannot deposit expired old NISA assets because ordinary investment account is not configured"
                    )
                self.ordinary_investment_account.deposit(portfolio_value)

                LOGGER.debug(
                    f"Moved {utilities.format_million_yen(portfolio_value)} from old NISA account "
                    f"for year {self.current_year - 20} to ordinary investment account"
                )

        # Check if we should do lump withdrawal from iDeCo
        if (
            self.ideco_investment_account is not None
            and self._current_age == self.ideco_investment_account.ideco_payout_plan.payout_start_age
        ):

            tax_free_lump_sum = self.ideco_investment_account.withdraw_tax_free_lump_sum(
                self.current_year
            )

            if tax_free_lump_sum > 0:

                if self.ordinary_investment_account is None:
                    raise ValueError(
                        "Cannot deposit the iDeCo tax-free lump sum because ordinary investment account is not "
                        "configured"
                    )
                self.ordinary_investment_account.deposit(tax_free_lump_sum)

                LOGGER.debug(
                    f"Withdrew tax-free lump sum of {utilities.format_million_yen(tax_free_lump_sum)} "
                    "from iDeCo account")

        if (
            self.ordinary_investment_account is not None
            and self.nisa_account is not None
            and self.nisa_account.principal < self.nisa_account.total_deposit_limit
        ):

            amount_to_move_from_ordinary_account_to_nisa = min(
                self.nisa_account.total_deposit_limit - self.nisa_account.principal,
                self.nisa_account.annual_deposit_limit,
                self.ordinary_investment_account.max_cash_withdrawal
            )

            if amount_to_move_from_ordinary_account_to_nisa > 0:

                self.ordinary_investment_account.withdraw(
                    amount_to_move_from_ordinary_account_to_nisa)

                self.nisa_account.deposit(
                    amount_to_move_from_ordinary_account_to_nisa,
                    self.current_year
                )

                LOGGER.debug(
                    f"Moved {utilities.format_million_yen(amount_to_move_from_ordinary_account_to_nisa)} "
                    "from ordinary investment account to NISA account"
                )

    def get_portfolio_summary(self) -> dict[str, decimal.Decimal]:

        account_values = {
            account_name: account.portfolio_value
            for account_name, account in self._configured_accounts.items()
        }

        return {
            **account_values,
            "total_portfolio_value": self.portfolio_value,
        }

    def get_formatted_portfolio_summary_description(self) -> str:

        return "\n".join(
            f"{key}: {value / constants.MILLION:.3f} mln yen"
            for key, value in self.get_portfolio_summary().items()
        )
