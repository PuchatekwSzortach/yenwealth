"""
Module with investment logic
"""

import collections
import copy
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
        return self.principal + self.gain

    def advance_one_year(self, change_rate: decimal.Decimal):

        self.gain += self.value * (change_rate - self.annual_management_cost_rate)

    def sell(self, amount: decimal.Decimal):

        if amount < 0:
            raise ValueError(f"amount value should be non-negative, got {amount}")

        if amount > self.value:
            raise ValueError(
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
class DepositStrategy(typing.Protocol):

    def allocate(
        self,
        amount: decimal.Decimal,
        assets: list[str],
    ) -> dict[str, decimal.Decimal]:
        ...


class ProportionalDepositStrategy(DepositStrategy):

    def __init__(self, weights: dict[str, decimal.Decimal]):

        self.weights = weights

    def allocate(self, amount: decimal.Decimal, assets: list[str]) -> dict[str, decimal.Decimal]:

        missing = set(assets) - self.weights.keys()

        if missing:
            raise ValueError(f"Missing weights for assets: {missing}")

        weights = {
            asset: self.weights[asset]
            for asset in assets
        }

        total_weight = sum(weights.values())

        if total_weight <= 0:
            raise ValueError("Total weight must be positive")

        return {
            asset: amount * weight / total_weight
            for asset, weight in weights.items()
        }


@typing.runtime_checkable
@beartype.beartype
class WithdrawStrategy(typing.Protocol):

    def calculate_withdrawal_amounts(
        self,
        amount: decimal.Decimal,
        asset_map: dict[str, decimal.Decimal],
    ) -> dict[str, decimal.Decimal]:
        ...


class SequentialWithdrawStrategy(WithdrawStrategy):

    def __init__(self, withdraw_order: list[str]):
        self.withdraw_order = withdraw_order

    def calculate_withdrawal_amounts(
        self,
        amount: decimal.Decimal,
        asset_map: dict[str, decimal.Decimal],
    ) -> dict[str, decimal.Decimal]:

        remaining = amount
        withdrawals = {}

        for asset_name in self.withdraw_order:

            withdrawal = min(remaining, asset_map[asset_name])

            if withdrawal > 0:
                withdrawals[asset_name] = withdrawal

            remaining -= withdrawal

            if remaining == 0:
                return withdrawals

        raise InsufficientFunds


@beartype.beartype
class OrdinaryInvestmentAccount:

    def __init__(
        self,
        asset_map: dict[str, Asset],
        capital_gain_tax_rate: decimal.Decimal = decimal.Decimal("0.20325")
    ):

        self.capital_gain_tax_rate = capital_gain_tax_rate
        self.asset_map = asset_map

    @property
    def portfolio_value(self) -> decimal.Decimal:
        return decimal.Decimal(sum(asset.value for asset in self.asset_map.values()))

    def deposit(self, amount: decimal.Decimal, strategy: DepositStrategy):

        if amount < 0:
            raise ValueError(f"Deposit amount should be non-negative, got {amount}")

        allocations = strategy.allocate(
            amount=amount,
            assets=list(self.asset_map.keys())
        )

        for name, allocation in allocations.items():
            self.asset_map[name].buy(allocation)

    def advance_one_year(self, investment_returns: dict[str, decimal.Decimal]):

        for name, asset in self.asset_map.items():
            asset.advance_one_year(investment_returns[name])

    def withdraw(self, desired_cash: decimal.Decimal, strategy: WithdrawStrategy):

        asset_to_net_value_map = {
            name: asset.value - (asset.gain * self.capital_gain_tax_rate)
            for name, asset in self.asset_map.items()
        }

        net_cash_withdrawals = strategy.calculate_withdrawal_amounts(
            amount=desired_cash,
            asset_map=asset_to_net_value_map
        )

        for name, net_sale in net_cash_withdrawals.items():

            asset = self.asset_map[name]
            gain_ratio = asset.gain / asset.value
            net_proceeds_ratio = 1 - (gain_ratio * self.capital_gain_tax_rate)
            gross_sale = net_sale / net_proceeds_ratio

            asset.sell(gross_sale)

    @property
    def max_cash_withdrawal(self) -> decimal.Decimal:

        net_values = [asset.value - (asset.gain * self.capital_gain_tax_rate) for asset in self.asset_map.values()]

        return decimal.Decimal(sum(net_values)).quantize(constants.YEN, decimal.ROUND_DOWN)


@beartype.beartype
class IdecoInvestmentAccount:

    def __init__(
        self,
        asset_map: dict[str, Asset],
        contribution_start_year: int
    ):

        self.asset_map = asset_map
        self.contribution_start_year = contribution_start_year

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
        return decimal.Decimal(sum(asset.value for asset in self.asset_map.values()))

    def deposit(self, amount: decimal.Decimal, age: int, strategy: DepositStrategy):

        if age >= self.max_deposit_age:
            raise ValueError(f"Deposit age {age} exceeds maximum allowed deposit age of {self.max_deposit_age}")

        if amount < 0:
            raise ValueError(f"Deposit amount should be non-negative, got {amount}")

        if amount > self.max_annual_contribution:
            raise ValueError(
                f"Deposit amount {amount} exceeds maximum allowed contribution of {self.max_annual_contribution}")

        allocations = strategy.allocate(
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

    def withdraw_pension(self, age: int, strategy: WithdrawStrategy) -> decimal.Decimal:

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
        self._withdraw(withdrawal, strategy)
        self.pension_payout_ages.append(age)

        return withdrawal

    def _withdraw(self, amount: decimal.Decimal, strategy: WithdrawStrategy):

        withdrawals = strategy.calculate_withdrawal_amounts(
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

    def withdraw_tax_free_lump_sum(self, year: int, strategy: WithdrawStrategy) -> decimal.Decimal:

        if year < self.contribution_start_year:
            raise ValueError(f"Year {year} has to be larger than account start year {self.contribution_start_year}")

        amount_withdrawn = min(self.portfolio_value, self.get_max_allowed_tax_free_lump_withdrawal_amount(year))
        self._withdraw(amount_withdrawn, strategy)
        return amount_withdrawn


@beartype.beartype
class OldNisaAccount:
    """
    Old NISA account that no longer allows deposit, and requires investments to be withdrawn within 20 years
    from when they were made.
    """

    def __init__(self, year_to_asset_map: dict[int, dict[str, Asset]]):

        self.year_to_asset_map = copy.deepcopy(year_to_asset_map)

    def advance_one_year(self, investment_returns: dict[str, decimal.Decimal], year: int):

        for investment_year, asset_map in self.year_to_asset_map.items():

            if investment_year + 20 < year:
                raise ValueError(f"nisa investment for year {investment_year} must be liquidated")

            for name, asset in asset_map.items():
                asset.advance_one_year(investment_returns[name])

    @property
    def portfolio_value(self) -> decimal.Decimal:

        return decimal.Decimal(
            sum(asset.value for asset_map in self.year_to_asset_map.values() for asset in asset_map.values())
        )

    def withdraw_for_year(
        self,
        portfolio_year: int,
        desired_cash: decimal.Decimal,
        strategy: WithdrawStrategy
    ):
        """
        Withdraw from portfolio established on portfolio_year
        """

        asset_map = self.year_to_asset_map[portfolio_year]
        portfolio_value = decimal.Decimal(sum(asset.value for asset in asset_map.values()))

        if portfolio_value < desired_cash:
            raise ValueError(f"Portfolio value for {portfolio_year} is not large enough")

        withdrawals = strategy.calculate_withdrawal_amounts(
            amount=desired_cash,
            asset_map={name: asset.value for name, asset in asset_map.items()}
        )

        for name, withdrawal in withdrawals.items():
            asset_map[name].sell(withdrawal)

    def withdraw(self, desired_cash: decimal.Decimal, strategy: WithdrawStrategy):
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
                sum(asset.value for asset in self.year_to_asset_map[investment_year].values())
            )
            withdrawal_from_year = min(desired_cash - total_withdrawal, year_portfolio_value)

            self.withdraw_for_year(
                portfolio_year=investment_year,
                desired_cash=withdrawal_from_year,
                strategy=strategy
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
        asset_map: dict[str, Asset]
    ):

        self.annual_deposit_limit = decimal.Decimal("3.6") * constants.MILLION
        self.total_deposit_limit = decimal.Decimal(18) * constants.MILLION
        self.asset_map = asset_map

        if self.principal > self.total_deposit_limit:
            raise ValueError(f"Principal {self.principal} exceeds total deposit limit of {self.total_deposit_limit}")

        self.year_to_deposit_map = collections.defaultdict(decimal.Decimal)

    @property
    def principal(self) -> decimal.Decimal:
        return decimal.Decimal(sum(asset.principal for asset in self.asset_map.values()))

    @property
    def portfolio_value(self) -> decimal.Decimal:
        return decimal.Decimal(sum(asset.value for asset in self.asset_map.values()))

    def deposit(self, amount: decimal.Decimal, year: int, strategy: DepositStrategy):

        if amount < 0:
            raise ValueError(f"Deposit amount should be non-negative, got {amount}")

        if amount == 0:
            return

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

        allocations = strategy.allocate(
            amount=amount,
            assets=list(self.asset_map.keys())
        )

        for name, allocation in allocations.items():
            self.asset_map[name].buy(allocation)

        self.year_to_deposit_map[year] += amount

    def advance_one_year(self, investment_returns: dict[str, decimal.Decimal]):

        for name, asset in self.asset_map.items():
            asset.advance_one_year(investment_returns[name])

    def withdraw(self, desired_cash: decimal.Decimal, strategy: WithdrawStrategy):

        if desired_cash < 0:
            raise ValueError(f"Withdrawal value should be non-negative, got {desired_cash}")

        if desired_cash > self.portfolio_value:
            raise InsufficientFunds(f"Withdrawal value {desired_cash} exceeds portfolio value {self.portfolio_value}")

        withdrawals = strategy.calculate_withdrawal_amounts(
            amount=desired_cash,
            asset_map={name: asset.value for name, asset in self.asset_map.items()}
        )

        for name, withdrawal in withdrawals.items():
            self.asset_map[name].sell(withdrawal)


class IdecoPolicy(pydantic.BaseModel):
    withdrawal_start_age: int
    withdrawal_period_in_years: int


class InvestmentPolicy(pydantic.BaseModel):

    # Needed to use protocol-based deposit and withdraw strategies
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    ideco: IdecoPolicy
    ideco_account_deposit_strategy: DepositStrategy
    ideco_account_withdraw_strategy: WithdrawStrategy
    old_nisa_account_withdraw_strategy: WithdrawStrategy
    nisa_account_deposit_strategy: DepositStrategy
    nisa_account_withdraw_strategy: WithdrawStrategy
    ordinary_account_deposit_strategy: DepositStrategy
    ordinary_account_withdraw_strategy: WithdrawStrategy


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


class SimpleInvestmentManager:
    """
    Investment manager with a strategy that:
    - prioritizes depositing into NISA before ordinary account
    - prioritizes withdrawing fron ordinary account before NISA
    - withdraws half iDeCO funds at pension start time,
    """

    def __init__(
        self,
        ordinary_investment_account: OrdinaryInvestmentAccount,
        ideco_investment_account: IdecoInvestmentAccount,
        old_nisa_account: OldNisaAccount,
        nisa_account: NisaAccount,
        investment_policy: InvestmentPolicy,
        simulation_start_age: int,
        simulation_start_year: int
    ):

        self.ordinary_investment_account = ordinary_investment_account
        self.ideco_investment_account = ideco_investment_account
        self.old_nisa_account = old_nisa_account
        self.nisa_account = nisa_account
        self.investment_policy = investment_policy
        self.simulation_start_age = simulation_start_age
        self.simulation_start_year = simulation_start_year

        self.current_year = simulation_start_year

    @property
    def _current_age(self) -> int:
        return self.simulation_start_age + self.current_year - self.simulation_start_year

    @property
    def portfolio_value(self) -> decimal.Decimal:
        return \
            self.ordinary_investment_account.portfolio_value + \
            self.ideco_investment_account.portfolio_value + \
            self.old_nisa_account.portfolio_value + \
            self.nisa_account.portfolio_value

    @property
    def after_tax_portfolio_value(self) -> decimal.Decimal:

        return \
            self.ordinary_investment_account.max_cash_withdrawal + \
            self.ideco_investment_account.portfolio_value + \
            self.old_nisa_account.portfolio_value + \
            self.nisa_account.portfolio_value

    def advance_one_year(self, investment_returns: dict):

        self.ordinary_investment_account.advance_one_year(investment_returns)
        self.ideco_investment_account.advance_one_year(investment_returns)
        self.old_nisa_account.advance_one_year(investment_returns, self.current_year)
        self.nisa_account.advance_one_year(investment_returns)

        self.current_year += 1

    def deposit(self, amount: decimal.Decimal, age: int):

        if amount < 0:
            raise ValueError(f"Deposit amount should be non-negative, got {amount}")

        if amount == 0:
            return

        if age < self.ideco_investment_account.max_deposit_age:

            amount_deposited_to_ideco = min(amount, self.ideco_investment_account.max_annual_contribution)

            self.ideco_investment_account.deposit(
                amount=amount_deposited_to_ideco,
                age=age,
                strategy=self.investment_policy.ideco_account_deposit_strategy
            )

            amount -= amount_deposited_to_ideco

            LOGGER.debug(
                f"Deposited {utilities.format_million_yen(amount_deposited_to_ideco)} to iDeCo account")

        if self.nisa_account.principal < self.nisa_account.total_deposit_limit:

            amount_deposited_to_nisa = min(
                self.nisa_account.total_deposit_limit - self.nisa_account.principal,
                self.nisa_account.annual_deposit_limit - self.nisa_account.year_to_deposit_map[self.current_year],
                amount
            )

            self.nisa_account.deposit(
                amount_deposited_to_nisa,
                self.current_year,
                self.investment_policy.nisa_account_deposit_strategy
            )
            amount -= amount_deposited_to_nisa

            LOGGER.debug(
                f"Deposited {utilities.format_million_yen(amount_deposited_to_nisa)} to NISA account")

        if amount > 0:

            self.ordinary_investment_account.deposit(amount, self.investment_policy.ordinary_account_deposit_strategy)
            LOGGER.debug(
                f"Deposited {utilities.format_million_yen(amount)} to ordinary investment account")

    def withdraw(self, desired_cash: decimal.Decimal):

        desired_cash = desired_cash.quantize(constants.YEN, decimal.ROUND_UP)

        if desired_cash < 0:
            raise ValueError(f"Withdrawal value should be non-negative, got {desired_cash}")

        total_cash_withdrawn = decimal.Decimal(0)

        # Establish how much to withdraw from ordinary account
        withdrawal_from_ordinary_account = min(
            desired_cash - total_cash_withdrawn,
            self.ordinary_investment_account.max_cash_withdrawal
        ).quantize(constants.YEN, rounding=decimal.ROUND_DOWN)

        if withdrawal_from_ordinary_account > 0:

            self.ordinary_investment_account.withdraw(
                withdrawal_from_ordinary_account,
                self.investment_policy.ordinary_account_withdraw_strategy)

            total_cash_withdrawn += withdrawal_from_ordinary_account

        withdrawal_from_old_nisa = min(
            desired_cash - total_cash_withdrawn,
            self.old_nisa_account.portfolio_value
        ).quantize(constants.YEN, rounding=decimal.ROUND_UP)

        if withdrawal_from_old_nisa > 0:

            self.old_nisa_account.withdraw(
                withdrawal_from_old_nisa,
                self.investment_policy.old_nisa_account_withdraw_strategy
            )
            total_cash_withdrawn += withdrawal_from_old_nisa

        # Establish how much to withdraw from NISA
        withdrawal_from_nisa = min(
            desired_cash - total_cash_withdrawn,
            self.nisa_account.portfolio_value
        ).quantize(constants.YEN, rounding=decimal.ROUND_UP)

        if withdrawal_from_nisa > 0:

            self.nisa_account.withdraw(
                withdrawal_from_nisa,
                self.investment_policy.nisa_account_withdraw_strategy
            )
            total_cash_withdrawn += withdrawal_from_nisa

        if total_cash_withdrawn < desired_cash:

            raise InsufficientFunds(f"Not enough funds to withdraw {desired_cash}")

    def optimize_investments(self):
        """
        Optimize investments based on the investment policy.
        """

        # Check if any old nisa account portfolio has to be liquidated
        if (self.current_year - 20) in self.old_nisa_account.year_to_asset_map:

            asset_map = self.old_nisa_account.year_to_asset_map.pop(self.current_year - 20)
            portfolio_value = decimal.Decimal(sum(asset.value for asset in asset_map.values()))

            self.ordinary_investment_account.deposit(
                portfolio_value,
                self.investment_policy.ordinary_account_deposit_strategy)

            LOGGER.debug(
                f"Moved {utilities.format_million_yen(portfolio_value)} from old NISA account "
                f"for year {self.current_year - 20} to ordinary investment account"
            )

        # Check if we should do lump withdrawal from iDeCo
        if self._current_age == self.investment_policy.ideco.withdrawal_start_age:

            tax_free_lump_sum = self.ideco_investment_account.withdraw_tax_free_lump_sum(
                self.current_year,
                self.investment_policy.ideco_account_withdraw_strategy
            )

            self.ordinary_investment_account.deposit(
                tax_free_lump_sum,
                self.investment_policy.ordinary_account_deposit_strategy)

            LOGGER.debug(
                f"Withdrew tax-free lump sum of {utilities.format_million_yen(tax_free_lump_sum)} "
                "from iDeCo account")

        if self.nisa_account.principal < self.nisa_account.total_deposit_limit:

            nisa_deposit = min(
                self.nisa_account.total_deposit_limit - self.nisa_account.principal,
                self.nisa_account.annual_deposit_limit,
                self.ordinary_investment_account.max_cash_withdrawal
            )

            self.ordinary_investment_account.withdraw(
                nisa_deposit,
                self.investment_policy.ordinary_account_withdraw_strategy)

            self.nisa_account.deposit(
                nisa_deposit,
                self.current_year,
                self.investment_policy.nisa_account_deposit_strategy
            )

            LOGGER.debug(
                f"Moved {utilities.format_million_yen(nisa_deposit)} "
                "from ordinary investment account to NISA account"
            )

    def get_portfolio_summary(self) -> dict[str, decimal.Decimal]:

        return {
            "ordinary_investment_account": self.ordinary_investment_account.portfolio_value,
            "ideco_investment_account": self.ideco_investment_account.portfolio_value,
            "old_nisa_account": self.old_nisa_account.portfolio_value,
            "nisa_account": self.nisa_account.portfolio_value,
            "total_portfolio_value": self.portfolio_value
        }

    def get_formatted_portfolio_summary_description(self) -> str:

        return "\n".join(
            f"{key}: {value / constants.MILLION:.3f} mln yen"
            for key, value in self.get_portfolio_summary().items()
        )
