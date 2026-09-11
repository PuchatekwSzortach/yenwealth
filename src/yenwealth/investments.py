"""
Module with investment logic
"""

import decimal
import logging

import beartype
import returns.maybe

from . import constants


LOGGER = logging.getLogger(__name__)


@beartype.beartype
class OrdinaryInvestmentAccount:

    def __init__(
        self,
        principal: decimal.Decimal,
        gain: decimal.Decimal,
        investment_return_rate: decimal.Decimal,
        capital_gain_tax_rate: decimal.Decimal
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

        if desired_cash > self.portfolio_value:
            raise ValueError(
                f"Withdrawal value {desired_cash} exceeds portfolio value {self.portfolio_value}"
            )

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

    def __init__(self, portfolio_value: decimal.Decimal, investment_return_rate: decimal.Decimal):

        self.investment_return_rate = investment_return_rate
        self.portfolio_value = portfolio_value

        self.max_annual_contribution = decimal.Decimal("0.276") * constants.MILLION
        self.max_deposit_age = 65
        self.minimum_withdrawal_start_age = 60
        self.maximum_withdrawal_start_age = 75

        self.max_tax_free_lump_sum = decimal.Decimal("17.8") * constants.MILLION

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

    def withdraw_tax_free_lump_sum(self) -> decimal.Decimal:

        amount_withdrawn = min(self.portfolio_value, self.max_tax_free_lump_sum)
        self.portfolio_value -= amount_withdrawn
        return amount_withdrawn

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
