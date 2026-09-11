"""
Module with investment logic
"""

import decimal
import logging

from . import constants


LOGGER = logging.getLogger(__name__)


class OrdinaryInvestmentAccount:

    def __init__(self, investment_return_rate: decimal.Decimal, capital_gain_tax_rate: decimal.Decimal):

        self.investment_return_rate = investment_return_rate
        self.capital_gain_tax_rate = capital_gain_tax_rate
        self.principal = decimal.Decimal("0")
        self.gain = decimal.Decimal("0")

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
