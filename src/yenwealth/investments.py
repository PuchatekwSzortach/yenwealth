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


@beartype.beartype
class OrdinaryInvestmentAccount:

    def __init__(
        self,
        principal: decimal.Decimal,
        gain: decimal.Decimal,
        investment_return_rate: decimal.Decimal,
        capital_gain_tax_rate: decimal.Decimal = decimal.Decimal("0.20325")
    ):

        self.investment_return_rate = investment_return_rate
        self.capital_gain_tax_rate = capital_gain_tax_rate
        self.principal = principal
        self.gain = gain

    @property
    def portfolio_value(self) -> decimal.Decimal:
        return self.principal + self.gain

    def deposit(self, amount: decimal.Decimal):

        if amount < 0:
            raise ValueError(f"Deposit amount should be non-negative, got {amount}")

        self.principal += amount

    def advance_one_year(self):

        self.gain += self.investment_return_rate * (self.principal + self.gain)

    def withdraw(self, desired_cash: decimal.Decimal):

        if desired_cash < 0:
            raise ValueError(f"Withdrawal value should be non-negative, got {desired_cash}")

        gain_ratio = self.gain / self.portfolio_value

        # Calculate gross amount needed to liquidate
        gross_withdrawal = desired_cash / (1 - (gain_ratio * self.capital_gain_tax_rate))

        if gross_withdrawal > self.portfolio_value:
            raise ValueError(
                f"Gross withdrawal value {gross_withdrawal} needed to realize desired cash "
                f"{desired_cash} exceeds portfolio value {self.portfolio_value}"
            )

        # Proportional splits
        principal_withdrawn = gross_withdrawal * (1 - gain_ratio)
        gain_withdrawn = gross_withdrawal * gain_ratio

        # Deduct proportionally from remaining balances
        self.principal -= principal_withdrawn
        self.gain -= gain_withdrawn

    @property
    def max_cash_withdrawal(self) -> decimal.Decimal:

        return (self.portfolio_value - (self.capital_gain_tax_rate * self.gain)) \
            .quantize(constants.YEN, decimal.ROUND_DOWN)


@beartype.beartype
class IdecoInvestmentAccount:

    def __init__(
            self,
            portfolio_value: decimal.Decimal,
            investment_return_rate: decimal.Decimal,
            contribution_start_year: int):

        self.investment_return_rate = investment_return_rate
        self.portfolio_value = portfolio_value
        self.contribution_start_year = contribution_start_year

        self.max_annual_contribution = decimal.Decimal("0.276") * constants.MILLION
        self.max_deposit_age = 65
        self.minimum_withdrawal_start_age = 60
        self.maximum_withdrawal_start_age = 75

        self.has_started_drawing_pension = False
        self.maybe_pension_period_in_years: returns.maybe.Maybe[int] = returns.maybe.Nothing
        self.maybe_pension_schema_start_age: returns.maybe.Maybe[int] = returns.maybe.Nothing
        self.pension_payout_ages: list[int] = []

    def deposit(self, amount: decimal.Decimal, age: int):

        if age >= self.max_deposit_age:
            raise ValueError(f"Deposit age {age} exceeds maximum allowed deposit age of {self.max_deposit_age}")

        if amount < 0:
            raise ValueError(f"Deposit amount should be non-negative, got {amount}")

        if amount > self.max_annual_contribution:
            raise ValueError(
                f"Deposit amount {amount} exceeds maximum allowed contribution of {self.max_annual_contribution}")

        self.portfolio_value += amount

    def advance_one_year(self):

        self.portfolio_value = self.portfolio_value * (1 + self.investment_return_rate)

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

        withdrawal_proportion = 1 / (pension_period_in_years - len(self.pension_payout_ages))

        withdrawal = self.portfolio_value * decimal.Decimal(withdrawal_proportion)
        self.portfolio_value -= withdrawal
        self.pension_payout_ages.append(age)

        return withdrawal

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
        self.portfolio_value -= amount_withdrawn
        return amount_withdrawn


@beartype.beartype
class OldNisaAccount:
    """
    Old NISA account that no longer allows deposit, and requires investments to be withdrawn within 20 years
    from when they were made.
    """

    def __init__(self, year_to_portfolio_map: dict[int, decimal.Decimal], investment_return_rate: decimal.Decimal):

        self.year_to_portfolio_map = copy.deepcopy(year_to_portfolio_map)
        self.investment_return_rate = investment_return_rate

    def advance_one_year(self, year: int):

        for investment_year in self.year_to_portfolio_map:

            if investment_year + 20 < year:
                raise ValueError(f"nisa investment for year {investment_year} must be liquidated")

            self.year_to_portfolio_map[investment_year] = \
                self.year_to_portfolio_map[investment_year] * (1 + self.investment_return_rate)

    @property
    def portfolio_value(self) -> decimal.Decimal:

        return decimal.Decimal(sum(self.year_to_portfolio_map.values()))

    def withdraw_for_year(self, portfolio_year: int, desired_cash: decimal.Decimal):
        """
        Withdraw from portfolio established on portfolio_year
        """

        portfolio_value = self.year_to_portfolio_map[portfolio_year]

        if portfolio_value < desired_cash:
            raise ValueError(f"Portfolio value for {portfolio_year} is not large enough")

        self.year_to_portfolio_map[portfolio_year] -= desired_cash

    def withdraw(self, desired_cash: decimal.Decimal):
        """
        Withdraw from portfolio in order of oldest to newest
        """

        if desired_cash < 0:
            raise ValueError(f"Withdrawal value should be non-negative, got {desired_cash}")

        if desired_cash > self.portfolio_value:
            raise ValueError(
                f"Withdrawal value {desired_cash} exceeds portfolio value {self.portfolio_value}"
            )

        total_withdrawal = decimal.Decimal(0)

        for investment_year in sorted(self.year_to_portfolio_map.keys()):

            withdrawal_from_year = min(desired_cash - total_withdrawal, self.year_to_portfolio_map[investment_year])

            self.withdraw_for_year(portfolio_year=investment_year, desired_cash=withdrawal_from_year)
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
        principal: decimal.Decimal,
        gain: decimal.Decimal,
        investment_return_rate: decimal.Decimal
    ):

        self.annual_deposit_limit = decimal.Decimal("3.6") * constants.MILLION
        self.total_deposit_limit = decimal.Decimal(18) * constants.MILLION

        if principal > self.total_deposit_limit:
            raise ValueError(f"Principal {principal} exceeds total deposit limit of {self.total_deposit_limit}")

        self.principal = principal
        self.gain = gain
        self.investment_return_rate = investment_return_rate

        self.year_to_deposit_map = collections.defaultdict(decimal.Decimal)

    @property
    def portfolio_value(self) -> decimal.Decimal:
        return self.principal + self.gain

    def deposit(self, amount: decimal.Decimal, year: int):

        if amount < 0:
            raise ValueError(f"Deposit amount should be non-negative, got {amount}")

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

        self.year_to_deposit_map[year] += amount
        self.principal += amount

    def advance_one_year(self):

        self.gain += self.investment_return_rate * (self.principal + self.gain)

    def withdraw(self, desired_amount: decimal.Decimal):

        if desired_amount > self.portfolio_value:
            raise ValueError(f"Desired amount {desired_amount} exceeds portfolio value {self.portfolio_value}")

        gain_ratio = self.portfolio_value / self.principal

        principal_withdrawn = desired_amount / gain_ratio

        self.principal -= principal_withdrawn
        self.gain -= desired_amount - principal_withdrawn


class IdecoPolicy(pydantic.BaseModel):
    withdrawal_start_age: int
    withdrawal_period_in_years: int


class InvestmentPolicy(pydantic.BaseModel):
    ideco: IdecoPolicy


class InvestmentManager(typing.Protocol):

    simulation_start_year: int

    @property
    def portfolio_value(self) -> decimal.Decimal:
        ...

    @property
    def after_tax_portfolio_value(self) -> decimal.Decimal:
        ...

    def advance_one_year(self, year: int):
        ...

    def deposit(self, amount: decimal.Decimal, age: int):
        ...

    def withdraw(self, desired_cash: decimal.Decimal):
        ...

    def optimize_investments(self, age: int):
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

    def advance_one_year(self, year):

        self.ordinary_investment_account.advance_one_year()
        self.ideco_investment_account.advance_one_year()
        self.old_nisa_account.advance_one_year(year)
        self.nisa_account.advance_one_year()

    def deposit(self, amount: decimal.Decimal, age: int):

        if amount < 0:
            raise ValueError(f"Deposit amount should be non-negative, got {amount}")

        if amount == 0:
            return

        if age < self.ideco_investment_account.max_deposit_age:

            amount_deposited_to_ideco = min(amount, self.ideco_investment_account.max_annual_contribution)
            self.ideco_investment_account.deposit(amount=amount_deposited_to_ideco, age=age)
            amount -= amount_deposited_to_ideco

            LOGGER.debug(
                f"Deposited {utilities.format_million_yen(amount_deposited_to_ideco)} to iDeCo account")

        if self.nisa_account.principal < self.nisa_account.total_deposit_limit:

            current_year = self.simulation_start_year + age - self.simulation_start_age

            amount_deposited_to_nisa = min(
                self.nisa_account.total_deposit_limit - self.nisa_account.principal,
                self.nisa_account.annual_deposit_limit - self.nisa_account.year_to_deposit_map[current_year],
                amount
            )

            self.nisa_account.deposit(amount_deposited_to_nisa, current_year)
            amount -= amount_deposited_to_nisa

            LOGGER.debug(
                f"Deposited {utilities.format_million_yen(amount_deposited_to_nisa)} to NISA account")

        if amount > 0:

            self.ordinary_investment_account.deposit(amount)
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

            self.ordinary_investment_account.withdraw(withdrawal_from_ordinary_account)
            total_cash_withdrawn += withdrawal_from_ordinary_account

        withdrawal_from_old_nisa = min(
            desired_cash - total_cash_withdrawn,
            self.old_nisa_account.portfolio_value
        ).quantize(constants.YEN, rounding=decimal.ROUND_UP)

        if withdrawal_from_old_nisa > 0:

            self.old_nisa_account.withdraw(withdrawal_from_old_nisa)
            total_cash_withdrawn += withdrawal_from_old_nisa

        # Establish how much to withdraw from NISA
        withdrawal_from_nisa = min(
            desired_cash - total_cash_withdrawn,
            self.nisa_account.portfolio_value
        ).quantize(constants.YEN, rounding=decimal.ROUND_UP)

        if withdrawal_from_nisa > 0:

            self.nisa_account.withdraw(withdrawal_from_nisa)
            total_cash_withdrawn += withdrawal_from_nisa

        if total_cash_withdrawn < desired_cash:

            raise ValueError(f"Not enough funds to withdraw {desired_cash}")

    def optimize_investments(self, age: int):
        """
        Optimize investments based on the investment policy.
        """

        current_year = self.simulation_start_year + (age - self.simulation_start_age)

        # Check if any old nisa account portfolio has to be liquidated
        if (current_year - 20) in self.old_nisa_account.year_to_portfolio_map:

            portfolio_value = self.old_nisa_account.year_to_portfolio_map.pop(current_year - 20)
            self.ordinary_investment_account.deposit(portfolio_value)

            LOGGER.debug(
                f"Moved {utilities.format_million_yen(portfolio_value)} from old NISA account "
                f"for year {current_year - 20} to ordinary investment account"
            )

        # Check if we should do lump withdrawal from iDeCo
        if age == self.investment_policy.ideco.withdrawal_start_age:

            year = self.simulation_start_year + age - self.simulation_start_age

            tax_free_lump_sum = self.ideco_investment_account.withdraw_tax_free_lump_sum(year)
            self.ordinary_investment_account.deposit(tax_free_lump_sum)

            LOGGER.debug(
                f"Withdrew tax-free lump sum of {utilities.format_million_yen(tax_free_lump_sum)} "
                "from iDeCo account")

        if self.nisa_account.principal < self.nisa_account.total_deposit_limit:

            nisa_deposit = min(
                self.nisa_account.total_deposit_limit - self.nisa_account.principal,
                self.nisa_account.annual_deposit_limit,
                self.ordinary_investment_account.max_cash_withdrawal
            )

            self.ordinary_investment_account.withdraw(nisa_deposit)
            self.nisa_account.deposit(nisa_deposit, self.simulation_start_year + age - self.simulation_start_year)

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
