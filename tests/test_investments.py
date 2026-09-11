import decimal
import math

import pytest

import yenwealth.investments


class TestOrdinaryInvestmentAccount:
    """
    Test for OrdinaryInvestmentAccount
    """

    def test_value_of_portfolio_without_investments(self):

        assert yenwealth.investments.OrdinaryInvestmentAccount(
            principal=decimal.Decimal("0"),
            gain=decimal.Decimal("0"),
            investment_return_rate=decimal.Decimal("0.1"),
            capital_gain_tax_rate=decimal.Decimal("0.2")
        ).portfolio_value == decimal.Decimal("0")

    def test_value_of_portfolio_with_investments(self):

        investment_account = yenwealth.investments.OrdinaryInvestmentAccount(
            principal=decimal.Decimal("1000"),
            gain=decimal.Decimal("0"),
            investment_return_rate=decimal.Decimal("0.1"),
            capital_gain_tax_rate=decimal.Decimal("0.2"))

        assert math.isclose(investment_account.principal, decimal.Decimal("1000"), rel_tol=1e-2)
        assert math.isclose(investment_account.gain, decimal.Decimal("0"), rel_tol=1e-2)
        assert math.isclose(investment_account.portfolio_value, decimal.Decimal("1000"), rel_tol=1e-2)

        investment_account.deposit(decimal.Decimal("10"))

        assert math.isclose(investment_account.principal, decimal.Decimal("1010"), rel_tol=1e-2)
        assert math.isclose(investment_account.gain, decimal.Decimal("0"), rel_tol=1e-2)
        assert math.isclose(investment_account.portfolio_value, decimal.Decimal("1010"), rel_tol=1e-2)

    def test_advancement_of_portfolio_value_over_time(self):

        investment_account = yenwealth.investments.OrdinaryInvestmentAccount(
            principal=decimal.Decimal("1000"),
            gain=decimal.Decimal("0"),
            investment_return_rate=decimal.Decimal("0.1"),
            capital_gain_tax_rate=decimal.Decimal("0.2")
        )

        investment_account.advance_one_year()

        assert math.isclose(investment_account.principal, 1000, rel_tol=1e-2)
        assert math.isclose(investment_account.gain, 100, rel_tol=1e-2)
        assert math.isclose(investment_account.portfolio_value, 1100, rel_tol=1e-2)

        investment_account.advance_one_year()

        assert math.isclose(investment_account.principal, 1000, rel_tol=1e-2)
        assert math.isclose(investment_account.gain, 210, rel_tol=1e-2)
        assert math.isclose(investment_account.portfolio_value, 1210, rel_tol=1e-2)

        investment_account.deposit(amount=decimal.Decimal("1000"))

        assert math.isclose(investment_account.principal, 2000, rel_tol=1e-2)
        assert math.isclose(investment_account.gain, 210, rel_tol=1e-2)
        assert math.isclose(investment_account.portfolio_value, 2210, rel_tol=1e-2)

        investment_account.advance_one_year()

        assert math.isclose(investment_account.principal, 2000, rel_tol=1e-2)
        assert math.isclose(investment_account.gain, 431, rel_tol=1e-2)
        assert math.isclose(investment_account.portfolio_value, 2431, rel_tol=1e-2)

    def test_withdraw_over_portfolio_value(self):

        investment_account = yenwealth.investments.OrdinaryInvestmentAccount(
            principal=decimal.Decimal("1000"),
            gain=decimal.Decimal("0"),
            investment_return_rate=decimal.Decimal("0.1"),
            capital_gain_tax_rate=decimal.Decimal("0.2"))

        with pytest.raises(ValueError):
            investment_account.withdraw(desired_cash=decimal.Decimal("2000"))

    def test_withdraw(self):

        investment_account = yenwealth.investments.OrdinaryInvestmentAccount(
            principal=decimal.Decimal("1000"),
            gain=decimal.Decimal("0"),
            investment_return_rate=decimal.Decimal("0.1"),
            capital_gain_tax_rate=decimal.Decimal("0.2")
        )

        investment_account.advance_one_year()
        investment_account.advance_one_year()

        assert math.isclose(investment_account.principal, decimal.Decimal("1000"), rel_tol=1e-2)
        assert math.isclose(investment_account.gain, decimal.Decimal("210"), rel_tol=1e-2)
        assert math.isclose(investment_account.portfolio_value, decimal.Decimal("1210"), rel_tol=1e-2)

        investment_account.withdraw(desired_cash=decimal.Decimal("500"))

        assert math.isclose(investment_account.principal, decimal.Decimal("571.9178"), rel_tol=1e-4)
        assert math.isclose(investment_account.gain, decimal.Decimal("120.1027"), rel_tol=1e-4)
        assert math.isclose(investment_account.portfolio_value, decimal.Decimal("692.0205"), rel_tol=1e-4)

    def test_withdrawing_zero(self):

        investment_account = yenwealth.investments.OrdinaryInvestmentAccount(
            principal=decimal.Decimal("1000"),
            gain=decimal.Decimal("0"),
            investment_return_rate=decimal.Decimal("0.1"),
            capital_gain_tax_rate=decimal.Decimal("0.2")
        )

        investment_account.advance_one_year()
        investment_account.advance_one_year()

        assert math.isclose(investment_account.principal, decimal.Decimal("1000"), rel_tol=1e-2)
        assert math.isclose(investment_account.gain, decimal.Decimal("210"), rel_tol=1e-2)

        investment_account.withdraw(desired_cash=decimal.Decimal("0"))

        assert math.isclose(investment_account.principal, decimal.Decimal("1000"), rel_tol=1e-2)
        assert math.isclose(investment_account.gain, decimal.Decimal("210"), rel_tol=1e-2)

    def test_withdrawing_negative_amount(self):

        investment_account = yenwealth.investments.OrdinaryInvestmentAccount(
            principal=decimal.Decimal("1000"),
            gain=decimal.Decimal("0"),
            investment_return_rate=decimal.Decimal("0.1"),
            capital_gain_tax_rate=decimal.Decimal("0.2"))

        with pytest.raises(ValueError):
            investment_account.withdraw(desired_cash=decimal.Decimal("-100"))

    def test_max_cash_withdrawal(self):

        investment_account = yenwealth.investments.OrdinaryInvestmentAccount(
            principal=decimal.Decimal("1000"),
            gain=decimal.Decimal("0"),
            investment_return_rate=decimal.Decimal("0.1"),
            capital_gain_tax_rate=decimal.Decimal("0.2")
        )

        investment_account.advance_one_year()
        investment_account.advance_one_year()

        assert math.isclose(investment_account.principal, decimal.Decimal("1000"), rel_tol=1e-2)
        assert math.isclose(investment_account.gain, decimal.Decimal("210"), rel_tol=1e-2)

        assert investment_account.max_cash_withdrawal == decimal.Decimal("1168")
