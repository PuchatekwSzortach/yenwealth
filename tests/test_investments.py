import decimal

import pytest

import yenwealth.constants
import yenwealth.investments


class TestAsset:

    def test_sell(self):

        asset = yenwealth.investments.Asset(
            name="whatever",
            principal=decimal.Decimal(100),
            gain=decimal.Decimal(60),
            annual_management_cost_rate=decimal.Decimal(0)
        )

        asset.sell(decimal.Decimal(50))

        assert asset.principal == decimal.Decimal("68.75")
        assert asset.gain == decimal.Decimal("41.25")
        assert asset.value == decimal.Decimal(110)

    def test_advance_one_year(self):

        asset = yenwealth.investments.Asset(
            name="whatever",
            principal=decimal.Decimal(100),
            gain=decimal.Decimal(60),
            annual_management_cost_rate=decimal.Decimal("0.1")
        )

        assert asset.value == decimal.Decimal(160)

        asset.advance_one_year(change_rate=decimal.Decimal("0.15"))

        assert asset.value == decimal.Decimal(168)
        assert asset.principal == decimal.Decimal(100)
        assert asset.gain == decimal.Decimal(68)

    def test_buy(self):

        asset = yenwealth.investments.Asset(
            name="whatever",
            principal=decimal.Decimal(100),
            gain=decimal.Decimal(60),
            annual_management_cost_rate=decimal.Decimal("0.1")
        )

        assert asset.value == decimal.Decimal(160)

        asset.buy(decimal.Decimal(20))

        assert asset.principal == decimal.Decimal(120)
        assert asset.gain == decimal.Decimal(60)
        assert asset.value == decimal.Decimal(180)


class TestProportionalDepositStrategy:

    def test_proportional_allocation(self):

        strategy = yenwealth.investments.ProportionalDepositStrategy(
            {
                "VGT": decimal.Decimal(5),
                "S&P500": decimal.Decimal(10),
            }
        )

        result = strategy.allocate(
            decimal.Decimal(15000),
            ["VGT", "S&P500"],
        )

        assert result == {
            "VGT": decimal.Decimal(5000),
            "S&P500": decimal.Decimal(10000),
        }

    def test_allocation_with_zero_weight(self):

        strategy = yenwealth.investments.ProportionalDepositStrategy(
            {
                "VGT": decimal.Decimal(1),
                "S&P500": decimal.Decimal(0),
            }
        )

        result = strategy.allocate(
            decimal.Decimal(10000),
            ["VGT", "S&P500"],
        )

        assert result == {
            "VGT": decimal.Decimal(10000),
            "S&P500": decimal.Decimal(0),
        }


class TestSequentiallWithdrawStrategy:

    def test_withdraws_from_first_asset_only(self):

        strategy = yenwealth.investments.SequentialWithdrawStrategy(["VGG", "VGT"])

        result = strategy.calculate_withdrawal_amounts(
            decimal.Decimal(4000),
            {
                "VGG": decimal.Decimal(10000),
                "VGT": decimal.Decimal(20000)
            }
        )

        assert result == {
            "VGG": decimal.Decimal(4000)
        }

    def test_moves_to_next_asset_when_first_is_depleted(self):

        strategy = yenwealth.investments.SequentialWithdrawStrategy(["VGG", "VGT"])

        result = strategy.calculate_withdrawal_amounts(
            decimal.Decimal(15000),
            {
                "VGG": decimal.Decimal(10000),
                "VGT": decimal.Decimal(20000)
            }
        )

        assert result == {
            "VGG": decimal.Decimal(10000),
            "VGT": decimal.Decimal(5000),
        }

    def test_raises_if_all_assets_are_insufficient(self):

        strategy = yenwealth.investments.SequentialWithdrawStrategy(["VGG", "VGT"])

        with pytest.raises(yenwealth.investments.InsufficientFunds):

            strategy.calculate_withdrawal_amounts(
                decimal.Decimal(31000),
                {
                    "VGG": decimal.Decimal(10000),
                    "VGT": decimal.Decimal(20000)
                }
            )


class TestOrdinaryInvestmentAccount:

    def test_portolio_value(self):

        account = yenwealth.investments.OrdinaryInvestmentAccount(
            asset_map={
                "VGT": yenwealth.investments.Asset(
                    name="VGT",
                    principal=decimal.Decimal(10),
                    gain=decimal.Decimal(5),
                    annual_management_cost_rate=decimal.Decimal("0.1")
                ),
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(20),
                    gain=decimal.Decimal(5),
                    annual_management_cost_rate=decimal.Decimal("0.1")
                )
            }
        )

        assert decimal.Decimal(40) == account.portfolio_value

    def test_deposit(self):

        account = yenwealth.investments.OrdinaryInvestmentAccount(
            asset_map={
                "VGT": yenwealth.investments.Asset(
                    name="VGT",
                    principal=decimal.Decimal(10),
                    gain=decimal.Decimal(5),
                    annual_management_cost_rate=decimal.Decimal("0.1")
                ),
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(20),
                    gain=decimal.Decimal(5),
                    annual_management_cost_rate=decimal.Decimal("0.1")
                )
            }
        )

        strategy = yenwealth.investments.ProportionalDepositStrategy(
            weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(3)}
        )

        account.deposit(amount=decimal.Decimal(10), strategy=strategy)

        assert account.asset_map["VGT"].principal == decimal.Decimal("12.5")
        assert account.asset_map["VOO"].principal == decimal.Decimal("27.5")

    def test_advance_one_year(self):

        account = yenwealth.investments.OrdinaryInvestmentAccount(
            asset_map={
                "VGT": yenwealth.investments.Asset(
                    name="VGT",
                    principal=decimal.Decimal(10),
                    gain=decimal.Decimal(5),
                    annual_management_cost_rate=decimal.Decimal("0.1")
                ),
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(20),
                    gain=decimal.Decimal(5),
                    annual_management_cost_rate=decimal.Decimal("0.1")
                )
            }
        )

        account.advance_one_year(
            investment_returns={
                "VGT": decimal.Decimal("0.2"),
                "VOO": decimal.Decimal("-0.1")
            }
        )

        assert account.asset_map["VGT"].gain == decimal.Decimal("6.5")
        assert account.asset_map["VOO"].gain == decimal.Decimal(0)

    def test_withdraw_over_portfolio_value(self):

        account = yenwealth.investments.OrdinaryInvestmentAccount(
            asset_map={
                "VGT": yenwealth.investments.Asset(
                    name="VGT",
                    principal=decimal.Decimal(10),
                    gain=decimal.Decimal(5),
                    annual_management_cost_rate=decimal.Decimal("0.1")
                ),
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(20),
                    gain=decimal.Decimal(5),
                    annual_management_cost_rate=decimal.Decimal("0.1")
                )
            },
            capital_gain_tax_rate=decimal.Decimal("0.2")
        )

        with pytest.raises(yenwealth.investments.InsufficientFunds):

            account.withdraw(
                desired_cash=decimal.Decimal(50),
                strategy=yenwealth.investments.SequentialWithdrawStrategy(["VGT", "VOO"])
            )

    def test_withdraw(self):

        account = yenwealth.investments.OrdinaryInvestmentAccount(
            asset_map={
                "VGT": yenwealth.investments.Asset(
                    name="VGT",
                    principal=decimal.Decimal(10),
                    gain=decimal.Decimal(5),
                    annual_management_cost_rate=decimal.Decimal("0.1")
                ),
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(20),
                    gain=decimal.Decimal(80),
                    annual_management_cost_rate=decimal.Decimal("0.1")
                )
            },
            capital_gain_tax_rate=decimal.Decimal("0.5")
        )

        strategy = yenwealth.investments.SequentialWithdrawStrategy(["VGT", "VOO"])

        account.withdraw(
            desired_cash=decimal.Decimal(44),
            strategy=strategy
        )

        # We would expect that with capital gain tax rate of 0.5, VGT asset can provide 12.5 units
        # (10 untaxed from prinicipal, then 5 gross (2.5 net) from gain)
        # Then VOO needs to provide net amount of 31.5 units.
        # VOO has 80% gain and we need to pay 50% capital gain tax on it, so net cash per 1 unit sold should be
        # 1 - (0.8 * 0.5) = 0.6.
        # So to realize 31.5 units of net cash, we need a gross sale of 31.5 / 0.6 or 52.5.
        # 20% of VOO is principal, and 20% of 52.5 is 10.5, so principal should go down from 20 to 9.5.
        # Remaining 42 comes from gain, so gain should come down to 38

        assert account.asset_map["VGT"].value == decimal.Decimal(0)

        assert account.asset_map["VOO"].principal == decimal.Decimal("9.5")
        assert account.asset_map["VOO"].gain == decimal.Decimal(38)
        assert account.asset_map["VOO"].value == decimal.Decimal("47.5")

    def test_max_cash_widthdrawal(self):

        account = yenwealth.investments.OrdinaryInvestmentAccount(
            asset_map={
                "VGT": yenwealth.investments.Asset(
                    name="VGT",
                    principal=decimal.Decimal(10),
                    gain=decimal.Decimal(5),
                    annual_management_cost_rate=decimal.Decimal("0.1")
                ),
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(20),
                    gain=decimal.Decimal(80),
                    annual_management_cost_rate=decimal.Decimal("0.1")
                )
            },
            capital_gain_tax_rate=decimal.Decimal("0.2")
        )

        assert account.max_cash_withdrawal == decimal.Decimal(98)


class TestIdecoInvestmentAccount:

    @staticmethod
    def asset_map():
        return {
            "VGT": yenwealth.investments.Asset(
                name="VGT",
                principal=decimal.Decimal(10),
                gain=decimal.Decimal(5),
                annual_management_cost_rate=decimal.Decimal("0.1")
            ),
            "VOO": yenwealth.investments.Asset(
                name="VOO",
                principal=decimal.Decimal(20),
                gain=decimal.Decimal(5),
                annual_management_cost_rate=decimal.Decimal("0.1")
            )
        }

    def test_portfolio_value(self):

        ideco = yenwealth.investments.IdecoInvestmentAccount(
            asset_map=self.asset_map(),
            contribution_start_year=2020
        )

        assert ideco.portfolio_value == decimal.Decimal(40)

    def test_deposit(self):

        ideco = yenwealth.investments.IdecoInvestmentAccount(
            asset_map=self.asset_map(),
            contribution_start_year=2020
        )

        ideco.deposit(
            amount=decimal.Decimal(10),
            age=40,
            strategy=yenwealth.investments.ProportionalDepositStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(3)}
            )
        )

        assert ideco.asset_map["VGT"].principal == decimal.Decimal("12.5")
        assert ideco.asset_map["VOO"].principal == decimal.Decimal("27.5")

    def test_advance_one_year(self):

        ideco = yenwealth.investments.IdecoInvestmentAccount(
            asset_map=self.asset_map(),
            contribution_start_year=2020
        )

        ideco.advance_one_year(
            investment_returns={
                "VGT": decimal.Decimal("0.2"),
                "VOO": decimal.Decimal("-0.1")
            }
        )

        assert ideco.asset_map["VGT"].gain == decimal.Decimal("6.5")
        assert ideco.asset_map["VOO"].gain == decimal.Decimal(0)

    def test_withdrawing_pensions_without_initializing_it_first(self):

        ideco = yenwealth.investments.IdecoInvestmentAccount(
            asset_map=self.asset_map(),
            contribution_start_year=2020
        )

        with pytest.raises(ValueError):
            ideco.withdraw_pension(
                age=70,
                strategy=yenwealth.investments.SequentialWithdrawStrategy(["VGT", "VOO"])
            )

    def test_withdrawing_pensions(self):

        period_in_years = 5

        ideco = yenwealth.investments.IdecoInvestmentAccount(
            asset_map={
                "VGT": yenwealth.investments.Asset(
                    name="VGT",
                    principal=decimal.Decimal(40),
                    gain=decimal.Decimal(0),
                    annual_management_cost_rate=decimal.Decimal(0)
                ),
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(60),
                    gain=decimal.Decimal(0),
                    annual_management_cost_rate=decimal.Decimal(0)
                )
            },
            contribution_start_year=2020
        )

        withdrawal_strategy = yenwealth.investments.SequentialWithdrawStrategy(["VGT", "VOO"])

        ideco.start_pension_scheme(
            start_age=70,
            period_in_years=period_in_years
        )

        # First withdrawal
        portfolio_value_before_withdrawal = ideco.portfolio_value
        amount = ideco.withdraw_pension(age=70, strategy=withdrawal_strategy)
        assert abs(amount - (portfolio_value_before_withdrawal / 5)) < decimal.Decimal("0.001")

        # Second withdrawal
        portfolio_value_before_withdrawal = ideco.portfolio_value
        amount = ideco.withdraw_pension(age=71, strategy=withdrawal_strategy)
        assert abs(amount - (portfolio_value_before_withdrawal / 4)) < decimal.Decimal("0.001")

        # Third withdrawal
        portfolio_value_before_withdrawal = ideco.portfolio_value
        amount = ideco.withdraw_pension(age=72, strategy=withdrawal_strategy)
        assert abs(amount - (portfolio_value_before_withdrawal / 3)) < decimal.Decimal("0.001")

        # # Fourth withdrawal
        portfolio_value_before_withdrawal = ideco.portfolio_value
        amount = ideco.withdraw_pension(age=73, strategy=withdrawal_strategy)
        assert abs(amount - (portfolio_value_before_withdrawal / 2)) < decimal.Decimal("0.001")

        # Last withdrawal
        portfolio_value_before_withdrawal = ideco.portfolio_value
        amount = ideco.withdraw_pension(age=74, strategy=withdrawal_strategy)
        assert abs(amount - portfolio_value_before_withdrawal) < decimal.Decimal("0.001")

        assert ideco.portfolio_value == decimal.Decimal(0)

    def test_max_allowed_lump_free_withdrawal(self):

        ideco = yenwealth.investments.IdecoInvestmentAccount(
            asset_map=self.asset_map(),
            contribution_start_year=2020
        )

        # Before 20 year threshold
        assert decimal.Decimal(800_000) == ideco.get_max_allowed_tax_free_lump_withdrawal_amount(2022)
        assert decimal.Decimal(4_000_000) == ideco.get_max_allowed_tax_free_lump_withdrawal_amount(2030)

        # After 20 year threshold
        assert decimal.Decimal(8_700_000) == ideco.get_max_allowed_tax_free_lump_withdrawal_amount(2041)
        assert decimal.Decimal(15_000_000) == ideco.get_max_allowed_tax_free_lump_withdrawal_amount(2050)

    def test_withdraw_tax_free_lump_sum(self):

        ideco = yenwealth.investments.IdecoInvestmentAccount(
            asset_map={
                "VGT": yenwealth.investments.Asset(
                    name="VGT",
                    principal=decimal.Decimal(10),
                    gain=decimal.Decimal(0),
                    annual_management_cost_rate=decimal.Decimal(0)
                ),
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(20),
                    gain=decimal.Decimal(0),
                    annual_management_cost_rate=decimal.Decimal(0)
                )
            },
            contribution_start_year=2020
        )

        amount = ideco.withdraw_tax_free_lump_sum(
            year=2022,
            strategy=yenwealth.investments.SequentialWithdrawStrategy(["VGT", "VOO"])
        )

        assert amount == decimal.Decimal(30)
        assert ideco.portfolio_value == decimal.Decimal(0)


class TestOldNisaAccount:

    @staticmethod
    def asset_map(principal_vgt: int, principal_voo: int):
        return {
            "VGT": yenwealth.investments.Asset(
                name="VGT",
                principal=decimal.Decimal(principal_vgt),
                gain=decimal.Decimal(0),
                annual_management_cost_rate=decimal.Decimal(0)
            ),
            "VOO": yenwealth.investments.Asset(
                name="VOO",
                principal=decimal.Decimal(principal_voo),
                gain=decimal.Decimal(0),
                annual_management_cost_rate=decimal.Decimal(0)
            )
        }

    def test_advance_one_year(self):

        nisa = yenwealth.investments.OldNisaAccount(
            year_to_asset_map={
                2020: self.asset_map(principal_vgt=100, principal_voo=50),
                2021: self.asset_map(principal_vgt=50, principal_voo=25)
            }
        )

        nisa.advance_one_year(
            investment_returns={
                "VGT": decimal.Decimal("0.1"),
                "VOO": decimal.Decimal("0.2")
            },
            year=2025
        )

        assert nisa.year_to_asset_map[2020]["VGT"].value == decimal.Decimal(110)
        assert nisa.year_to_asset_map[2020]["VOO"].value == decimal.Decimal(60)
        assert nisa.year_to_asset_map[2021]["VGT"].value == decimal.Decimal(55)
        assert nisa.year_to_asset_map[2021]["VOO"].value == decimal.Decimal(30)

    def test_advance_one_year_over_twenty_years_for_any_investment(self):

        nisa = yenwealth.investments.OldNisaAccount(
            year_to_asset_map={
                2020: self.asset_map(100, 50),
                2021: self.asset_map(50, 25)
            }
        )

        with pytest.raises(ValueError):
            nisa.advance_one_year(
                investment_returns={"VGT": decimal.Decimal(0), "VOO": decimal.Decimal(0)},
                year=2041
            )

    def test_withdraw_for_invalid_year(self):

        nisa = yenwealth.investments.OldNisaAccount(
            year_to_asset_map={
                2020: self.asset_map(100, 50),
                2021: self.asset_map(50, 25)
            }
        )

        with pytest.raises(KeyError):
            nisa.withdraw_for_year(
                portfolio_year=2022,
                desired_cash=decimal.Decimal(10),
                strategy=yenwealth.investments.SequentialWithdrawStrategy(["VGT", "VOO"])
            )

    def test_valid_withdraw_for_year(self):

        nisa = yenwealth.investments.OldNisaAccount(
            year_to_asset_map={
                2020: self.asset_map(100, 50),
                2021: self.asset_map(50, 25)
            }
        )

        nisa.withdraw_for_year(
            portfolio_year=2020,
            desired_cash=decimal.Decimal(10),
            strategy=yenwealth.investments.SequentialWithdrawStrategy(["VGT", "VOO"])
        )

        assert nisa.year_to_asset_map[2020]["VGT"].value == decimal.Decimal(90)
        assert nisa.year_to_asset_map[2020]["VOO"].value == decimal.Decimal(50)

    def test_withdraw(self):

        nisa = yenwealth.investments.OldNisaAccount(
            year_to_asset_map={
                2020: self.asset_map(100, 50),
                2021: self.asset_map(50, 25)
            }
        )

        nisa.withdraw(
            desired_cash=decimal.Decimal(120),
            strategy=yenwealth.investments.SequentialWithdrawStrategy(["VGT", "VOO"])
        )

        assert nisa.year_to_asset_map[2020]["VGT"].value == decimal.Decimal(0)
        assert nisa.year_to_asset_map[2020]["VOO"].value == decimal.Decimal(30)
        assert nisa.year_to_asset_map[2021]["VGT"].value == decimal.Decimal(50)
        assert nisa.year_to_asset_map[2021]["VOO"].value == decimal.Decimal(25)


class TestNisaAccount:

    @staticmethod
    def asset_map(principal_vgt: int, principal_voo: int):
        return {
            "VGT": yenwealth.investments.Asset(
                name="VGT",
                principal=decimal.Decimal(principal_vgt),
                gain=decimal.Decimal(0),
                annual_management_cost_rate=decimal.Decimal(0)
            ),
            "VOO": yenwealth.investments.Asset(
                name="VOO",
                principal=decimal.Decimal(principal_voo),
                gain=decimal.Decimal(0),
                annual_management_cost_rate=decimal.Decimal(0)
            )
        }

    @staticmethod
    def deposit_strategy():
        return yenwealth.investments.ProportionalDepositStrategy(
            weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
        )

    def test_initial_deposit_over_max_limit(self):

        with pytest.raises(ValueError):

            yenwealth.investments.NisaAccount(
                asset_map=self.asset_map(20 * yenwealth.constants.MILLION, 0)
            )

    def test_deposit_over_annual_limit(self):

        nisa = yenwealth.investments.NisaAccount(
            asset_map=self.asset_map(0, 0)
        )

        # Within limit
        nisa.deposit(amount=decimal.Decimal(2_000_000), year=2025, strategy=self.deposit_strategy())

        with pytest.raises(ValueError):

            # Over limit for targer year
            nisa.deposit(amount=decimal.Decimal(2_000_000), year=2025, strategy=self.deposit_strategy())

    def test_deposit(self):

        nisa = yenwealth.investments.NisaAccount(
            asset_map=self.asset_map(principal_vgt=0, principal_voo=0)
        )

        nisa.deposit(amount=decimal.Decimal(2_000_000), year=2025, strategy=self.deposit_strategy())

        assert nisa.asset_map["VGT"].principal == decimal.Decimal(1_000_000)
        assert nisa.asset_map["VOO"].principal == decimal.Decimal(1_000_000)
        assert nisa.year_to_deposit_map[2025] == decimal.Decimal(2_000_000)
        assert nisa.portfolio_value == decimal.Decimal(2_000_000)

        nisa.deposit(amount=decimal.Decimal(1_000_000), year=2025, strategy=self.deposit_strategy())

        assert nisa.asset_map["VGT"].principal == decimal.Decimal(1_500_000)
        assert nisa.asset_map["VOO"].principal == decimal.Decimal(1_500_000)
        assert nisa.year_to_deposit_map[2025] == decimal.Decimal(3_000_000)
        assert nisa.portfolio_value == decimal.Decimal(3_000_000)

        nisa.deposit(amount=decimal.Decimal(1_000_000), year=2026, strategy=self.deposit_strategy())

        assert nisa.asset_map["VGT"].principal == decimal.Decimal(2_000_000)
        assert nisa.asset_map["VOO"].principal == decimal.Decimal(2_000_000)
        assert nisa.year_to_deposit_map[2025] == decimal.Decimal(3_000_000)
        assert nisa.year_to_deposit_map[2026] == decimal.Decimal(1_000_000)
        assert nisa.portfolio_value == decimal.Decimal(4_000_000)

    def test_advance_one_year(self):

        nisa = yenwealth.investments.NisaAccount(
            asset_map=self.asset_map(principal_vgt=100, principal_voo=50)
        )

        nisa.advance_one_year(investment_returns={"VGT": decimal.Decimal("0.1"), "VOO": decimal.Decimal("0.2")})

        assert nisa.asset_map["VGT"].gain == decimal.Decimal(10)
        assert nisa.asset_map["VGT"].value == decimal.Decimal(110)

        assert nisa.asset_map["VOO"].gain == decimal.Decimal(10)
        assert nisa.asset_map["VOO"].value == decimal.Decimal(60)

        assert nisa.portfolio_value == decimal.Decimal(170)

        nisa.deposit(amount=decimal.Decimal(50), year=2025, strategy=self.deposit_strategy())

        assert nisa.asset_map["VGT"].principal == decimal.Decimal(125)
        assert nisa.asset_map["VGT"].gain == decimal.Decimal(10)

        assert nisa.asset_map["VOO"].principal == decimal.Decimal(75)
        assert nisa.asset_map["VOO"].gain == decimal.Decimal(10)

        assert nisa.portfolio_value == decimal.Decimal(220)

        nisa.advance_one_year(investment_returns={"VGT": decimal.Decimal("0.1"), "VOO": decimal.Decimal("0.2")})

        assert nisa.asset_map["VGT"].gain == decimal.Decimal("23.5")
        assert nisa.asset_map["VGT"].value == decimal.Decimal("148.5")

        assert nisa.asset_map["VOO"].gain == decimal.Decimal(27)
        assert nisa.asset_map["VOO"].value == decimal.Decimal(102)

        assert nisa.portfolio_value == decimal.Decimal("250.5")

    def test_withdrawal_over_portolio_value(self):

        nisa = yenwealth.investments.NisaAccount(
            asset_map={
                "VGT": yenwealth.investments.Asset(
                    name="VGT",
                    principal=decimal.Decimal(100),
                    gain=decimal.Decimal(100),
                    annual_management_cost_rate=decimal.Decimal(0)
                )
            }
        )

        with pytest.raises(yenwealth.investments.InsufficientFunds):

            nisa.withdraw(
                decimal.Decimal(210),
                yenwealth.investments.SequentialWithdrawStrategy(["VGT"])
            )

    def test_withdrawal(self):

        initial_principal = decimal.Decimal(100)
        initial_portfolio_value = decimal.Decimal(200)

        nisa = yenwealth.investments.NisaAccount(
            asset_map={
                "VGT": yenwealth.investments.Asset(
                    name="VGT",
                    principal=initial_principal,
                    gain=initial_portfolio_value - initial_principal,
                    annual_management_cost_rate=decimal.Decimal(0)
                )
            }
        )

        assert nisa.asset_map["VGT"].principal == initial_principal
        assert nisa.asset_map["VGT"].gain == decimal.Decimal(100)
        assert nisa.portfolio_value == initial_portfolio_value

        desired_amount = decimal.Decimal(50)

        nisa.withdraw(
            desired_amount,
            yenwealth.investments.SequentialWithdrawStrategy(["VGT"])
        )

        assert nisa.portfolio_value == decimal.Decimal(150)
        assert nisa.asset_map["VGT"].gain == decimal.Decimal(75)
        assert nisa.asset_map["VGT"].principal == decimal.Decimal(75)


class TestInvestmentManager:

    @pytest.fixture
    def investment_manager(self):

        # 1. Ordinary Account: 0 principal, 0 gain, 0 tax for simple math
        ordinary = yenwealth.investments.OrdinaryInvestmentAccount(
            asset_map={
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(0),
                    gain=decimal.Decimal(0),
                    annual_management_cost_rate=decimal.Decimal(0)
                )
            },
            capital_gain_tax_rate=decimal.Decimal("0.20")
        )

        # 2. iDeCo Account: 0 initial portfolio
        ideco = yenwealth.investments.IdecoInvestmentAccount(
            asset_map={
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(0),
                    gain=decimal.Decimal(0),
                    annual_management_cost_rate=decimal.Decimal(0)
                )
            },
            contribution_start_year=2020
        )

        # 3. Old NISA Account: empty year map
        old_nisa = yenwealth.investments.OldNisaAccount(
            year_to_asset_map={}
        )

        # 4. NISA Account: 0 principal, 0 gain
        nisa = yenwealth.investments.NisaAccount(
            asset_map={
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(0),
                    gain=decimal.Decimal(0),
                    annual_management_cost_rate=decimal.Decimal(0)
                )
            }
        )

        # 5. Investment Policy: Withdrawal starts at age 75 for 20 years
        policy = yenwealth.investments.InvestmentPolicy(
            ideco=yenwealth.investments.IdecoPolicy(
                withdrawal_start_age=75,
                withdrawal_period_in_years=20
            ),
            ideco_account_deposit_strategy=yenwealth.investments.ProportionalDepositStrategy(
                weights={"VOO": decimal.Decimal(1)}),
            ideco_account_withdraw_strategy=yenwealth.investments.SequentialWithdrawStrategy(["VOO"]),
            old_nisa_account_withdraw_strategy=yenwealth.investments.SequentialWithdrawStrategy(["VOO"]),
            nisa_account_deposit_strategy=yenwealth.investments.ProportionalDepositStrategy(
                weights={"VOO": decimal.Decimal(1)}),
            nisa_account_withdraw_strategy=yenwealth.investments.SequentialWithdrawStrategy(["VOO"]),
            ordinary_account_deposit_strategy=yenwealth.investments.ProportionalDepositStrategy(
                weights={"VOO": decimal.Decimal(1)}),
            ordinary_account_withdraw_strategy=yenwealth.investments.SequentialWithdrawStrategy(["VOO"])
        )

        return yenwealth.investments.SimpleInvestmentManager(
            ordinary_investment_account=ordinary,
            ideco_investment_account=ideco,
            old_nisa_account=old_nisa,
            nisa_account=nisa,
            investment_policy=policy,
            simulation_start_age=30,
            simulation_start_year=2024
        )

    def test_deposit_priority(self, investment_manager):

        # Deposit 5,000,000 Yen at age 30
        # Expected order: iDeCo (max 276,000) -> NISA (max 3,600,000) -> Ordinary (rest: 1,124,000)
        investment_manager.deposit(amount=decimal.Decimal(5_000_000), age=30)

        assert investment_manager.ideco_investment_account.portfolio_value == decimal.Decimal(276_000)
        assert investment_manager.nisa_account.asset_map["VOO"].principal == decimal.Decimal(3_600_000)
        assert investment_manager.ordinary_investment_account.asset_map["VOO"].principal == decimal.Decimal(1_124_000)

    def test_withdraw_priority(self, investment_manager):

        # Setup initial balances directly
        investment_manager.ordinary_investment_account.asset_map["VOO"].principal = decimal.Decimal(1_000_000)
        investment_manager.old_nisa_account.year_to_asset_map = {
            2010: {
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(500_000),
                    gain=decimal.Decimal(0),
                    annual_management_cost_rate=decimal.Decimal(0)
                )
            }
        }
        investment_manager.nisa_account.asset_map["VOO"].principal = decimal.Decimal(2_000_000)

        # Withdraw 2,000,000 Yen
        # Expected order: Ordinary (1,000,000) -> Old NISA (500,000) -> NISA (500,000)
        investment_manager.withdraw(desired_cash=decimal.Decimal(2_000_000))

        assert investment_manager.ordinary_investment_account.portfolio_value == decimal.Decimal(0)
        assert investment_manager.old_nisa_account.portfolio_value == decimal.Decimal(0)
        assert investment_manager.nisa_account.portfolio_value == decimal.Decimal(1_500_000)

    def test_optimize_investments_old_nisa_liquidation(self, investment_manager):

        # Current year = start_year (2024) + age (50) - start_age (30) = 2044
        # 20 years prior = 2024. Populate Old NISA portfolio for 2024
        investment_manager.old_nisa_account.year_to_asset_map = {
            2024: {
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(1_000_000),
                    gain=decimal.Decimal(0),
                    annual_management_cost_rate=decimal.Decimal(0)
                )
            }
        }
        investment_manager.current_year = 2044

        investment_manager.optimize_investments()

        # 2024 Old NISA portfolio should be removed and moved into NISA Account
        assert 2024 not in investment_manager.old_nisa_account.year_to_asset_map
        assert investment_manager.nisa_account.asset_map["VOO"].principal == decimal.Decimal(1_000_000)

    def test_optimize_investments_ideco_lump_sum_and_nisa_topup(self, investment_manager):

        investment_manager.ideco_investment_account.asset_map["VOO"].principal = decimal.Decimal(10_000_000)

        # Year at which we hit age of 75, and ideco policy was set to do lump withdrawal at that age
        investment_manager.current_year = 2069

        investment_manager.optimize_investments()

        # 1. iDeCo 10M transferred to Ordinary Account tax-free
        # 2. Ordinary Account then transfers 3.6M (annual limit) to NISA Account
        assert investment_manager.ideco_investment_account.portfolio_value == decimal.Decimal(0)
        assert investment_manager.nisa_account.asset_map["VOO"].principal == decimal.Decimal(3_600_000)
        assert investment_manager.ordinary_investment_account.asset_map['VOO'].principal == decimal.Decimal(6_400_000)
