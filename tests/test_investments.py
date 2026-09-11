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


class TestIdecoInvestmentAccount:

    def test_withdrawing_pensions_without_initializing_it_first(self):

        ideco = yenwealth.investments.IdecoInvestmentAccount(
            portfolio_value=decimal.Decimal("100"),
            investment_return_rate=decimal.Decimal("0")
        )

        with pytest.raises(ValueError):
            ideco.withdraw_pension(70)

    def test_withdrawing_pensions(self):

        period_in_years = 5

        ideco = yenwealth.investments.IdecoInvestmentAccount(
            portfolio_value=decimal.Decimal("100"),
            investment_return_rate=decimal.Decimal("0")
        )

        ideco.start_pension_scheme(
            start_age=70,
            period_in_years=period_in_years
        )

        # First withdrawal
        portfolio_value_before_withdrawal = ideco.portfolio_value
        amount = ideco.withdraw_pension(age=70)
        assert abs(amount - (portfolio_value_before_withdrawal / 5)) < decimal.Decimal("0.001")

        # Second withdrawal
        portfolio_value_before_withdrawal = ideco.portfolio_value
        amount = ideco.withdraw_pension(age=71)
        assert abs(amount - (portfolio_value_before_withdrawal / 4)) < decimal.Decimal("0.001")

        # Third withdrawal
        portfolio_value_before_withdrawal = ideco.portfolio_value
        amount = ideco.withdraw_pension(age=72)
        assert abs(amount - (portfolio_value_before_withdrawal / 3)) < decimal.Decimal("0.001")

        # # Fourth withdrawal
        portfolio_value_before_withdrawal = ideco.portfolio_value
        amount = ideco.withdraw_pension(age=73)
        assert abs(amount - (portfolio_value_before_withdrawal / 2)) < decimal.Decimal("0.001")

        # Last withdrawal
        portfolio_value_before_withdrawal = ideco.portfolio_value
        amount = ideco.withdraw_pension(age=74)
        assert abs(amount - portfolio_value_before_withdrawal) < decimal.Decimal("0.001")

        assert ideco.portfolio_value == decimal.Decimal("0")


class TestOldNisaAccount:

    def test_advance_one_year(self):

        nisa = yenwealth.investments.OldNisaAccount(
            year_to_portfolio_map={
                2020: decimal.Decimal("100"),
                2021: decimal.Decimal("50")
            },
            investment_return_rate=decimal.Decimal("0.1")
        )

        nisa.advance_one_year(2025)

        assert abs(nisa.year_to_portfolio_map[2020] - decimal.Decimal(110)) < decimal.Decimal("0.001")
        assert abs(nisa.year_to_portfolio_map[2021] - decimal.Decimal(55)) < decimal.Decimal("0.001")

    def test_advance_one_year_over_twenty_years_for_any_investment(self):

        nisa = yenwealth.investments.OldNisaAccount(
            year_to_portfolio_map={
                2020: decimal.Decimal("100"),
                2021: decimal.Decimal("50")
            },
            investment_return_rate=decimal.Decimal("0.1")
        )

        with pytest.raises(ValueError):
            nisa.advance_one_year(2041)

    def test_withdraw_for_invalid_year(self):

        nisa = yenwealth.investments.OldNisaAccount(
            year_to_portfolio_map={
                2020: decimal.Decimal("100"),
                2021: decimal.Decimal("50")
            },
            investment_return_rate=decimal.Decimal("0.1")
        )

        with pytest.raises(KeyError):
            nisa.withdraw_for_year(portfolio_year=2022, desired_cash=decimal.Decimal("10"))

    def test_valid_withdraw_for_year(self):

        nisa = yenwealth.investments.OldNisaAccount(
            year_to_portfolio_map={
                2020: decimal.Decimal("100"),
                2021: decimal.Decimal("50")
            },
            investment_return_rate=decimal.Decimal("0.1")
        )

        nisa.withdraw_for_year(portfolio_year=2020, desired_cash=decimal.Decimal("10"))

        assert nisa.year_to_portfolio_map[2020] == decimal.Decimal("90")

    def test_withdraw(self):

        nisa = yenwealth.investments.OldNisaAccount(
            year_to_portfolio_map={
                2020: decimal.Decimal("100"),
                2021: decimal.Decimal("50")
            },
            investment_return_rate=decimal.Decimal("0.1")
        )

        nisa.withdraw(desired_cash=decimal.Decimal("120"))

        assert nisa.year_to_portfolio_map[2020] == decimal.Decimal("0")
        assert nisa.year_to_portfolio_map[2021] == decimal.Decimal("30")


class TestNisaAccount:

    def test_initial_deposit_over_max_limit(self):

        with pytest.raises(ValueError):

            yenwealth.investments.NisaAccount(
                principal=decimal.Decimal("20") * yenwealth.constants.MILLION,
                gain=decimal.Decimal("0"),
                investment_return_rate=decimal.Decimal("0")
            )

    def test_deposit_over_annual_limit(self):

        nisa = yenwealth.investments.NisaAccount(
            principal=decimal.Decimal("0"),
            gain=decimal.Decimal("0"),
            investment_return_rate=decimal.Decimal("0")
        )

        # Within limit
        nisa.deposit(amount=decimal.Decimal("2_000_000"), year=2025)

        with pytest.raises(ValueError):

            # Over limit for targer year
            nisa.deposit(amount=decimal.Decimal("2_000_000"), year=2025)

    def test_deposit(self):

        nisa = yenwealth.investments.NisaAccount(
            principal=decimal.Decimal("0"),
            gain=decimal.Decimal("0"),
            investment_return_rate=decimal.Decimal("0")
        )

        nisa.deposit(amount=decimal.Decimal("2_000_000"), year=2025)

        assert nisa.principal == decimal.Decimal("2_000_000")
        assert nisa.year_to_deposit_map[2025] == decimal.Decimal("2_000_000")
        assert nisa.portfolio_value == decimal.Decimal("2_000_000")

        nisa.deposit(amount=decimal.Decimal("1_000_000"), year=2025)

        assert nisa.principal == decimal.Decimal("3_000_000")
        assert nisa.year_to_deposit_map[2025] == decimal.Decimal("3_000_000")
        assert nisa.portfolio_value == decimal.Decimal("3_000_000")

        nisa.deposit(amount=decimal.Decimal("1_000_000"), year=2026)

        assert nisa.principal == decimal.Decimal("4_000_000")
        assert nisa.year_to_deposit_map[2025] == decimal.Decimal("3_000_000")
        assert nisa.year_to_deposit_map[2026] == decimal.Decimal("1_000_000")
        assert nisa.portfolio_value == decimal.Decimal("4_000_000")

    def test_advance_one_year(self):

        nisa = yenwealth.investments.NisaAccount(
            principal=decimal.Decimal("100"),
            gain=decimal.Decimal("0"),
            investment_return_rate=decimal.Decimal("0.1")
        )

        nisa.advance_one_year()

        assert nisa.principal == decimal.Decimal("100")
        assert nisa.gain == decimal.Decimal("10")
        assert nisa.portfolio_value == decimal.Decimal("110")

        nisa.deposit(amount=decimal.Decimal("50"), year=2025)

        assert nisa.principal == decimal.Decimal("150")
        assert nisa.gain == decimal.Decimal("10")
        assert nisa.portfolio_value == decimal.Decimal("160")

        nisa.advance_one_year()

        assert nisa.principal == decimal.Decimal("150")
        assert nisa.gain == decimal.Decimal("26")
        assert nisa.portfolio_value == decimal.Decimal("176")

    def test_withdrawal_over_portolio_value(self):

        nisa = yenwealth.investments.NisaAccount(
            principal=decimal.Decimal("100"),
            gain=decimal.Decimal("100"),
            investment_return_rate=decimal.Decimal("0")
        )

        with pytest.raises(ValueError):

            nisa.withdraw(decimal.Decimal("210"))

    def test_withdrawal(self):

        initial_principal = decimal.Decimal("100")
        initial_portfolio_value = decimal.Decimal("200")

        nisa = yenwealth.investments.NisaAccount(
            principal=initial_principal,
            gain=initial_portfolio_value - initial_principal,
            investment_return_rate=decimal.Decimal("0")
        )

        assert nisa.principal == initial_principal
        assert nisa.gain == decimal.Decimal("100")
        assert nisa.portfolio_value == initial_portfolio_value

        desired_amount = decimal.Decimal("50")

        nisa.withdraw(desired_amount)

        assert nisa.portfolio_value == decimal.Decimal("150")
        assert nisa.gain == decimal.Decimal("75")
        assert nisa.principal == decimal.Decimal("75")


class TestInvestmentPolicy:

    def test_construction_with_valid_data(self):

        policy = yenwealth.investments.InvestmentPolicy.model_validate(
            {
                "ideco": {
                    "withdrawal_start_age": 75,
                    "withdrawal_period_in_years": 20
                }
            }
        )

        assert policy.ideco.withdrawal_start_age == 75
        assert policy.ideco.withdrawal_period_in_years == 20


class TestInvestmentManager:

    @pytest.fixture
    def investment_manager(self):

        # 1. Ordinary Account: 0 principal, 0 gain, 0 tax for simple math
        ordinary = yenwealth.investments.OrdinaryInvestmentAccount(
            principal=decimal.Decimal("0"),
            gain=decimal.Decimal("0"),
            investment_return_rate=decimal.Decimal("0.05"),
            capital_gain_tax_rate=decimal.Decimal("0.20")
        )

        # 2. iDeCo Account: 0 initial portfolio
        ideco = yenwealth.investments.IdecoInvestmentAccount(
            portfolio_value=decimal.Decimal("0"),
            investment_return_rate=decimal.Decimal("0.05")
        )

        # 3. Old NISA Account: empty year map
        old_nisa = yenwealth.investments.OldNisaAccount(
            year_to_portfolio_map={},
            investment_return_rate=decimal.Decimal("0.05")
        )

        # 4. NISA Account: 0 principal, 0 gain
        nisa = yenwealth.investments.NisaAccount(
            principal=decimal.Decimal("0"),
            gain=decimal.Decimal("0"),
            investment_return_rate=decimal.Decimal("0.05")
        )

        # 5. Investment Policy: Withdrawal starts at age 75 for 20 years
        policy = yenwealth.investments.InvestmentPolicy(
            ideco=yenwealth.investments.IdecoPolicy(
                withdrawal_start_age=75,
                withdrawal_period_in_years=20
            )
        )

        return yenwealth.investments.InvestmentManager(
            ordinary_investment_account=ordinary,
            ideco_investment_account=ideco,
            old_nisa_account=old_nisa,
            nisa_account=nisa,
            investment_policy=policy,
            start_age=30,
            start_year=2024
        )

    def test_deposit_priority(self, investment_manager):

        # Deposit 5,000,000 Yen at age 30
        # Expected order: iDeCo (max 276,000) -> NISA (max 3,600,000) -> Ordinary (rest: 1,124,000)
        investment_manager.deposit(amount=decimal.Decimal("5_000_000"), age=30)

        assert investment_manager.ideco_investment_account.portfolio_value == decimal.Decimal("276_000")
        assert investment_manager.nisa_account.principal == decimal.Decimal("3_600_000")
        assert investment_manager.ordinary_investment_account.principal == decimal.Decimal("1_124_000")

    def test_withdraw_priority(self, investment_manager):

        # Setup initial balances directly
        investment_manager.ordinary_investment_account.principal = decimal.Decimal("1_000_000")
        investment_manager.old_nisa_account.year_to_portfolio_map = {2010: decimal.Decimal("500_000")}
        investment_manager.nisa_account.principal = decimal.Decimal("2_000_000")

        # Withdraw 2,000,000 Yen
        # Expected order: Ordinary (1,000,000) -> Old NISA (500,000) -> NISA (500,000)
        withdrawn = investment_manager.withdraw(desired_cash=decimal.Decimal("2_000_000"))

        assert withdrawn == decimal.Decimal("2_000_000")
        assert investment_manager.ordinary_investment_account.portfolio_value == decimal.Decimal("0")
        assert investment_manager.old_nisa_account.portfolio_value == decimal.Decimal("0")
        assert investment_manager.nisa_account.portfolio_value == decimal.Decimal("1_500_000")

    def test_optimize_investments_old_nisa_liquidation(self, investment_manager):

        # Current year = start_year (2024) + age (50) - start_age (30) = 2044
        # 20 years prior = 2024. Populate Old NISA portfolio for 2024
        investment_manager.old_nisa_account.year_to_portfolio_map = {2024: decimal.Decimal("1_000_000")}

        investment_manager.optimize_investments(age=50)

        # 2024 Old NISA portfolio should be removed and moved into NISA Account
        assert 2024 not in investment_manager.old_nisa_account.year_to_portfolio_map
        assert investment_manager.nisa_account.principal == decimal.Decimal("1_000_000")

    def test_optimize_investments_ideco_lump_sum_and_nisa_topup(self, investment_manager):

        investment_manager.ideco_investment_account.portfolio_value = decimal.Decimal("10_000_000")

        # Set age to policy withdrawal_start_age (75)
        investment_manager.optimize_investments(age=75)

        # 1. iDeCo 10M transferred to Ordinary Account tax-free
        # 2. Ordinary Account then transfers 3.6M (annual limit) to NISA Account
        assert investment_manager.ideco_investment_account.portfolio_value == decimal.Decimal("0")
        assert investment_manager.nisa_account.principal == decimal.Decimal("3_600_000")
        assert investment_manager.ordinary_investment_account.principal == decimal.Decimal("6_400_000")
