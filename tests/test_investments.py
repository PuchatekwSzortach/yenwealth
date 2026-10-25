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

    def test_sell_with_negative_gain(self):

        asset = yenwealth.investments.Asset(
            name="whatever",
            principal=decimal.Decimal(100),
            gain=decimal.Decimal(-20),
            annual_management_cost_rate=decimal.Decimal(0)
        )

        assert asset.value == decimal.Decimal(80)

        asset.sell(decimal.Decimal(40))

        assert asset.value == decimal.Decimal(40)

        # Since we want to sell 40 units of the asset, and gain represents -25% of asset value,
        # gain should be decreased by (40 * -25%) or -10, meaning gain changes from -20 to -10.
        # And thus we need 50 units to come out of the principal, so principal goes from 100 to 50.
        assert asset.gain == decimal.Decimal(-10)
        assert asset.principal == decimal.Decimal(50)

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

    def test_advance_one_year_with_negative_gain(self):

        asset = yenwealth.investments.Asset(
            name="whatever",
            principal=decimal.Decimal(100),
            gain=decimal.Decimal(-20),
            annual_management_cost_rate=decimal.Decimal("0.1")
        )

        assert asset.value == decimal.Decimal(80)

        asset.advance_one_year(change_rate=decimal.Decimal("0.15"))

        assert asset.principal == decimal.Decimal(100)

        # Gain grows like this: -20 + (80 * (0.15 - 0.1) = -20 + 8 = -16
        assert asset.gain == decimal.Decimal(-16)
        assert asset.value == decimal.Decimal(84)

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


class TestInvestmentStrategy:

    def test_strategies_expose_asset_names(self):

        asset_purchase_strategy = yenwealth.investments.ProportionalAssetPurchaseStrategy(
            weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(2)}
        )
        asset_sale_strategy = yenwealth.investments.SequentialAssetSaleStrategy(["VOO", "VGT"])

        assert asset_purchase_strategy.asset_names == {"VGT", "VOO"}
        assert asset_sale_strategy.asset_names == {"VGT", "VOO"}


class TestProportionalAssetPurchaseStrategy:

    def test_proportional_allocation(self):

        strategy = yenwealth.investments.ProportionalAssetPurchaseStrategy(
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

        strategy = yenwealth.investments.ProportionalAssetPurchaseStrategy(
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
        }


class TestSequentialAssetSaleStrategy:

    def test_withdraws_from_first_asset_only(self):

        strategy = yenwealth.investments.SequentialAssetSaleStrategy(["VGG", "VGT"])

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

        strategy = yenwealth.investments.SequentialAssetSaleStrategy(["VGG", "VGT"])

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

        strategy = yenwealth.investments.SequentialAssetSaleStrategy(["VGG", "VGT"])

        with pytest.raises(yenwealth.investments.InsufficientFunds):

            strategy.calculate_withdrawal_amounts(
                decimal.Decimal(31000),
                {
                    "VGG": decimal.Decimal(10000),
                    "VGT": decimal.Decimal(20000)
                }
            )

    def test_raises_if_all_assets_are_from_which_strategy_should_drawe_are_insufficient(self):

        strategy = yenwealth.investments.SequentialAssetSaleStrategy(["VGT"])

        with pytest.raises(yenwealth.investments.InsufficientFunds):

            strategy.calculate_withdrawal_amounts(
                decimal.Decimal(25),
                {
                    "VGG": decimal.Decimal(10),
                    "VGT": decimal.Decimal(20)
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
            },
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"])
        )

        assert decimal.Decimal(40) == account.portfolio_value

    def test_deposit(self):

        strategy = yenwealth.investments.ProportionalAssetPurchaseStrategy(
            weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(3)}
        )

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
            asset_purchase_strategy=strategy,
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"])
        )

        account.deposit(amount=decimal.Decimal(10))

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
            },
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"])
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
            capital_gain_tax_rate=decimal.Decimal("0.2"),
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"])
        )

        with pytest.raises(yenwealth.investments.InsufficientFunds):

            account.withdraw(
                desired_cash=decimal.Decimal(50)
            )

    def test_withdraw_over_max_cash_withdrawal(self):

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
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"])
        )

        with pytest.raises(yenwealth.investments.InsufficientFunds):

            account.withdraw(
                desired_cash=account.max_cash_withdrawal + decimal.Decimal("0.5")
            )

    def test_withdraw(self):

        account = yenwealth.investments.OrdinaryInvestmentAccount(
            asset_map={
                "VGT": yenwealth.investments.Asset(
                    name="VGT",
                    principal=decimal.Decimal(1000),
                    gain=decimal.Decimal(500),
                    annual_management_cost_rate=decimal.Decimal("0.1")
                ),
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(2000),
                    gain=decimal.Decimal(8000),
                    annual_management_cost_rate=decimal.Decimal("0.1")
                )
            },
            capital_gain_tax_rate=decimal.Decimal("0.5"),
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"])
        )

        account.withdraw(
            desired_cash=decimal.Decimal(4400)
        )

        # We would expect that with capital gain tax rate of 0.5, VGT asset can provide 1250 units
        # (1000 untaxed from principal, then 500 gross (250 net) from gain)
        # Then VOO needs to provide net amount of 3150 units.
        # VOO has 80% gain and we need to pay 50% capital gain tax on it, so net cash per 1 unit sold should be
        # 1 - (0.8 * 0.5) = 0.6.
        # So to realize 3150 units of net cash, we need a gross sale of 3150 / 0.6 or 5250.
        # 20% of VOO is principal, and 20% of 5250 is 1050, so principal should go down from 2000 to 950.
        # Remaining 4200 comes from gain, so gain should come down to 3800

        assert account.asset_map["VGT"].value == decimal.Decimal(0)

        assert account.asset_map["VOO"].principal == decimal.Decimal(950)
        assert account.asset_map["VOO"].gain == decimal.Decimal(3800)
        assert account.asset_map["VOO"].value == decimal.Decimal(4750)

    def test_withdraw_with_negative_gain(self):

        account = yenwealth.investments.OrdinaryInvestmentAccount(
            asset_map={
                "VGT": yenwealth.investments.Asset(
                    name="VGT",
                    principal=decimal.Decimal(100),
                    gain=decimal.Decimal(-20),
                    annual_management_cost_rate=decimal.Decimal(0)
                )
            },
            capital_gain_tax_rate=decimal.Decimal("0.2"),
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT"])
        )

        assert account.portfolio_value == decimal.Decimal(80)
        assert account.max_cash_withdrawal == decimal.Decimal(80)

        account.withdraw(
            desired_cash=decimal.Decimal(20)
        )

        assert account.asset_map["VGT"].principal == decimal.Decimal(75)
        assert account.asset_map["VGT"].gain == decimal.Decimal(-15)
        assert account.asset_map["VGT"].value == decimal.Decimal(60)

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
            capital_gain_tax_rate=decimal.Decimal("0.2"),
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"])
        )

        assert account.max_cash_withdrawal == decimal.Decimal(98)

    def test_init_rejects_account_asset_missing_from_strategy(self):

        with pytest.raises(ValueError, match="ordinary investment account"):
            yenwealth.investments.OrdinaryInvestmentAccount(
                asset_map={
                    "VOO": yenwealth.investments.Asset(
                        name="VOO",
                        principal=decimal.Decimal(0),
                        gain=decimal.Decimal(0),
                        annual_management_cost_rate=decimal.Decimal(0)
                    ),
                    "VGT": yenwealth.investments.Asset(
                        name="VGT",
                        principal=decimal.Decimal(0),
                        gain=decimal.Decimal(0),
                        annual_management_cost_rate=decimal.Decimal(0)
                    )
                },
                capital_gain_tax_rate=decimal.Decimal("0.20"),
                asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                    weights={"VOO": decimal.Decimal(1)}
                ),
                asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VOO"])
            )

    def test_init_rejects_strategy_asset_missing_from_account(self):

        with pytest.raises(ValueError, match="asset_purchase_strategy"):
            yenwealth.investments.OrdinaryInvestmentAccount(
                asset_map={
                    "VOO": yenwealth.investments.Asset(
                        name="VOO",
                        principal=decimal.Decimal(0),
                        gain=decimal.Decimal(0),
                        annual_management_cost_rate=decimal.Decimal(0)
                    )
                },
                capital_gain_tax_rate=decimal.Decimal("0.20"),
                asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                    weights={"VOO": decimal.Decimal(1), "VGT": decimal.Decimal(1)}
                ),
                asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VOO"])
            )

    def test_init_rejects_different_assets_between_account_strategies(self):

        with pytest.raises(ValueError, match="asset_sale_strategy"):
            yenwealth.investments.OrdinaryInvestmentAccount(
                asset_map={
                    "VOO": yenwealth.investments.Asset(
                        name="VOO",
                        principal=decimal.Decimal(0),
                        gain=decimal.Decimal(0),
                        annual_management_cost_rate=decimal.Decimal(0)
                    )
                },
                capital_gain_tax_rate=decimal.Decimal("0.20"),
                asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                    weights={"VOO": decimal.Decimal(1)}
                ),
                asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT"])
            )


class TestIdecoInvestmentAccount:

    @staticmethod
    def create_payout_plan(start_age: int = 75, period_in_years: int = 20):
        return yenwealth.investments.IdecoPensionPayoutPlan(
            start_age=start_age,
            period_in_years=period_in_years
        )

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
            contribution_start_year=2020,
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"]),
            ideco_pension_payout_plan=self.create_payout_plan()
        )

        assert ideco.portfolio_value == decimal.Decimal(40)

    def test_deposit_succeeds_before_pension_and_fails_after(self):

        ideco = yenwealth.investments.IdecoInvestmentAccount(
            asset_map=self.asset_map(),
            contribution_start_year=2020,
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(3)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"]),
            ideco_pension_payout_plan=self.create_payout_plan()
        )

        ideco.deposit(
            amount=decimal.Decimal(10),
            age=40
        )

        assert ideco.asset_map["VGT"].principal == decimal.Decimal("12.5")
        assert ideco.asset_map["VOO"].principal == decimal.Decimal("27.5")

        ideco.start_pension_scheme(age=75)

        with pytest.raises(ValueError, match="Cannot deposit after pension drawing has started"):
            ideco.deposit(amount=decimal.Decimal(10), age=40)

    def test_advance_one_year(self):

        ideco = yenwealth.investments.IdecoInvestmentAccount(
            asset_map=self.asset_map(),
            contribution_start_year=2020,
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"]),
            ideco_pension_payout_plan=self.create_payout_plan()
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
            contribution_start_year=2020,
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"]),
            ideco_pension_payout_plan=self.create_payout_plan()
        )

        with pytest.raises(ValueError):
            ideco.withdraw_pension(age=70)

    @pytest.mark.parametrize("start_age", [59, 76])
    def test_payout_plan_rejects_invalid_start_age(self, start_age):

        with pytest.raises(ValueError):
            self.create_payout_plan(start_age=start_age)

    @pytest.mark.parametrize("period_in_years", [4, 21])
    def test_payout_plan_rejects_invalid_period(self, period_in_years):

        with pytest.raises(ValueError):
            self.create_payout_plan(period_in_years=period_in_years)

    def test_start_pension_scheme_rejects_age_different_from_plan(self):

        ideco = yenwealth.investments.IdecoInvestmentAccount(
            asset_map=self.asset_map(),
            contribution_start_year=2020,
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"]),
            ideco_pension_payout_plan=self.create_payout_plan(start_age=60)
        )

        with pytest.raises(ValueError, match="Age 59 does not match planned pension start age 60"):
            ideco.start_pension_scheme(age=59)

        assert ideco.has_started_drawing_pension is False

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
            contribution_start_year=2020,
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"]),
            ideco_pension_payout_plan=self.create_payout_plan(
                start_age=70,
                period_in_years=period_in_years
            )
        )

        ideco.start_pension_scheme(age=70)

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

        assert ideco.portfolio_value == decimal.Decimal(0)

    def test_max_allowed_lump_free_withdrawal(self):

        ideco = yenwealth.investments.IdecoInvestmentAccount(
            asset_map=self.asset_map(),
            contribution_start_year=2020,
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"]),
            ideco_pension_payout_plan=self.create_payout_plan()
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
            contribution_start_year=2020,
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"]),
            ideco_pension_payout_plan=self.create_payout_plan()
        )

        amount = ideco.withdraw_tax_free_lump_sum(
            year=2022
        )

        assert amount == decimal.Decimal(30)
        assert ideco.portfolio_value == decimal.Decimal(0)

    def test_init_rejects_account_asset_missing_from_strategy(self):

        with pytest.raises(ValueError, match="ideco investment account"):
            yenwealth.investments.IdecoInvestmentAccount(
                asset_map={
                    "VGT": yenwealth.investments.Asset(
                        name="VGT",
                        principal=decimal.Decimal(0),
                        gain=decimal.Decimal(0),
                        annual_management_cost_rate=decimal.Decimal(0)
                    ),
                    "VOO": yenwealth.investments.Asset(
                        name="VOO",
                        principal=decimal.Decimal(0),
                        gain=decimal.Decimal(0),
                        annual_management_cost_rate=decimal.Decimal(0)
                    )
                },
                contribution_start_year=2020,
                asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                    weights={"VGT": decimal.Decimal(1)}
                ),
                asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT"]),
                ideco_pension_payout_plan=self.create_payout_plan()
            )

    def test_init_rejects_strategy_asset_missing_from_account(self):

        with pytest.raises(ValueError, match="asset_purchase_strategy"):
            yenwealth.investments.IdecoInvestmentAccount(
                asset_map={
                    "VGT": yenwealth.investments.Asset(
                        name="VGT",
                        principal=decimal.Decimal(0),
                        gain=decimal.Decimal(0),
                        annual_management_cost_rate=decimal.Decimal(0)
                    ),
                    "VOO": yenwealth.investments.Asset(
                        name="VOO",
                        principal=decimal.Decimal(0),
                        gain=decimal.Decimal(0),
                        annual_management_cost_rate=decimal.Decimal(0)
                    )
                },
                contribution_start_year=2020,
                asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                    weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1), "SPY": decimal.Decimal(1)}
                ),
                asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT", "VOO"]),
                ideco_pension_payout_plan=self.create_payout_plan()
            )

    def test_init_rejects_different_assets_between_account_strategies(self):

        with pytest.raises(ValueError, match="asset_sale_strategy"):
            yenwealth.investments.IdecoInvestmentAccount(
                asset_map={
                    "VGT": yenwealth.investments.Asset(
                        name="VGT",
                        principal=decimal.Decimal(0),
                        gain=decimal.Decimal(0),
                        annual_management_cost_rate=decimal.Decimal(0)
                    ),
                    "VOO": yenwealth.investments.Asset(
                        name="VOO",
                        principal=decimal.Decimal(0),
                        gain=decimal.Decimal(0),
                        annual_management_cost_rate=decimal.Decimal(0)
                    )
                },
                contribution_start_year=2020,
                asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                    weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
                ),
                asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT"]),
                ideco_pension_payout_plan=self.create_payout_plan()
            )


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

    @staticmethod
    def build_account(year_to_asset_map, asset_sale_strategy=None) -> yenwealth.investments.OldNisaAccount:
        asset_names = {
            name
            for asset_map in year_to_asset_map.values()
            for name in asset_map
        }
        if asset_sale_strategy is None:
            asset_sale_strategy = yenwealth.investments.SequentialAssetSaleStrategy(sorted(asset_names))
        return yenwealth.investments.OldNisaAccount(
            year_to_asset_map=year_to_asset_map,
            asset_sale_strategy=asset_sale_strategy
        )

    def test_advance_one_year(self):

        nisa = self.build_account(
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

        nisa = self.build_account(
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

        nisa = self.build_account(
            year_to_asset_map={
                2020: self.asset_map(100, 50),
                2021: self.asset_map(50, 25)
            }
        )

        with pytest.raises(KeyError):
            nisa.withdraw_for_year(
                portfolio_year=2022,
                desired_cash=decimal.Decimal(10)
            )

    def test_valid_withdraw_for_year(self):

        nisa = self.build_account(
            year_to_asset_map={
                2020: self.asset_map(100, 50),
                2021: self.asset_map(50, 25)
            },
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(
                ["VGT", "VOO"]
            )
        )

        nisa.withdraw_for_year(
            portfolio_year=2020,
            desired_cash=decimal.Decimal(10)
        )

        assert nisa.year_to_asset_map[2020]["VGT"].value == decimal.Decimal(90)
        assert nisa.year_to_asset_map[2020]["VOO"].value == decimal.Decimal(50)

    def test_withdraw(self):

        nisa = self.build_account(
            year_to_asset_map={
                2020: self.asset_map(100, 50),
                2021: self.asset_map(50, 25)
            },
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(
                ["VGT", "VOO"]
            )
        )

        nisa.withdraw(
            desired_cash=decimal.Decimal(120)
        )

        assert nisa.year_to_asset_map[2020]["VGT"].value == decimal.Decimal(0)
        assert nisa.year_to_asset_map[2020]["VOO"].value == decimal.Decimal(30)
        assert nisa.year_to_asset_map[2021]["VGT"].value == decimal.Decimal(50)
        assert nisa.year_to_asset_map[2021]["VOO"].value == decimal.Decimal(25)

    def test_init_rejects_asset_missing_from_strategy(self):

        with pytest.raises(ValueError, match="old nisa account"):
            yenwealth.investments.OldNisaAccount(
                year_to_asset_map={
                    2024: {
                        "VOO": yenwealth.investments.Asset(
                            name="VOO",
                            principal=decimal.Decimal(0),
                            gain=decimal.Decimal(0),
                            annual_management_cost_rate=decimal.Decimal(0)
                        )
                    },
                    2025: {
                        "VGT": yenwealth.investments.Asset(
                            name="VGT",
                            principal=decimal.Decimal(0),
                            gain=decimal.Decimal(0),
                            annual_management_cost_rate=decimal.Decimal(0)
                        )
                    }
                },
                asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VOO"])
            )


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
    def build_account(
        asset_map,
        asset_purchase_strategy=None,
        asset_sale_strategy=None
    ) -> yenwealth.investments.NisaAccount:

        asset_names = list(asset_map)

        if asset_purchase_strategy is None:
            asset_purchase_strategy = yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={name: decimal.Decimal(1) for name in asset_names}
            )

        if asset_sale_strategy is None:
            asset_sale_strategy = yenwealth.investments.SequentialAssetSaleStrategy(asset_names)

        return yenwealth.investments.NisaAccount(
            asset_map=asset_map,
            asset_purchase_strategy=asset_purchase_strategy,
            asset_sale_strategy=asset_sale_strategy
        )

    def test_initial_deposit_over_max_limit(self):

        with pytest.raises(ValueError):

            self.build_account(
                asset_map=self.asset_map(
                    principal_vgt=20 * yenwealth.constants.MILLION,
                    principal_voo=0
                )
            )

    def test_deposit_over_annual_limit(self):

        nisa = self.build_account(
            asset_map=self.asset_map(principal_vgt=0, principal_voo=0)
        )

        # Within limit
        nisa.deposit(amount=decimal.Decimal(2_000_000), year=2025)

        with pytest.raises(ValueError):

            # Over limit for target year
            nisa.deposit(amount=decimal.Decimal(2_000_000), year=2025)

    def test_deposit(self):

        nisa = self.build_account(
            asset_map=self.asset_map(principal_vgt=0, principal_voo=0),
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
            )
        )

        nisa.deposit(amount=decimal.Decimal(2_000_000), year=2025)

        assert nisa.asset_map["VGT"].principal == decimal.Decimal(1_000_000)
        assert nisa.asset_map["VOO"].principal == decimal.Decimal(1_000_000)
        assert nisa.year_to_deposit_map[2025] == decimal.Decimal(2_000_000)
        assert nisa.portfolio_value == decimal.Decimal(2_000_000)

        nisa.deposit(amount=decimal.Decimal(1_000_000), year=2025)

        assert nisa.asset_map["VGT"].principal == decimal.Decimal(1_500_000)
        assert nisa.asset_map["VOO"].principal == decimal.Decimal(1_500_000)
        assert nisa.year_to_deposit_map[2025] == decimal.Decimal(3_000_000)
        assert nisa.portfolio_value == decimal.Decimal(3_000_000)

        nisa.deposit(amount=decimal.Decimal(1_000_000), year=2026)

        assert nisa.asset_map["VGT"].principal == decimal.Decimal(2_000_000)
        assert nisa.asset_map["VOO"].principal == decimal.Decimal(2_000_000)
        assert nisa.year_to_deposit_map[2025] == decimal.Decimal(3_000_000)
        assert nisa.year_to_deposit_map[2026] == decimal.Decimal(1_000_000)
        assert nisa.portfolio_value == decimal.Decimal(4_000_000)

    def test_advance_one_year(self):

        nisa = self.build_account(
            asset_map=self.asset_map(principal_vgt=1000, principal_voo=500),
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1), "VOO": decimal.Decimal(1)}
            )
        )

        nisa.advance_one_year(investment_returns={"VGT": decimal.Decimal("0.1"), "VOO": decimal.Decimal("0.2")})

        assert nisa.asset_map["VGT"].gain == decimal.Decimal(100)
        assert nisa.asset_map["VGT"].value == decimal.Decimal(1100)

        assert nisa.asset_map["VOO"].gain == decimal.Decimal(100)
        assert nisa.asset_map["VOO"].value == decimal.Decimal(600)

        assert nisa.portfolio_value == decimal.Decimal(1700)

        nisa.deposit(amount=decimal.Decimal(500), year=2025)

        assert nisa.asset_map["VGT"].principal == decimal.Decimal(1250)
        assert nisa.asset_map["VGT"].gain == decimal.Decimal(100)

        assert nisa.asset_map["VOO"].principal == decimal.Decimal(750)
        assert nisa.asset_map["VOO"].gain == decimal.Decimal(100)

        assert nisa.portfolio_value == decimal.Decimal(2200)

        nisa.advance_one_year(investment_returns={"VGT": decimal.Decimal("0.1"), "VOO": decimal.Decimal("0.2")})

        assert nisa.asset_map["VGT"].gain == decimal.Decimal(235)
        assert nisa.asset_map["VGT"].value == decimal.Decimal(1485)

        assert nisa.asset_map["VOO"].gain == decimal.Decimal(270)
        assert nisa.asset_map["VOO"].value == decimal.Decimal(1020)

        assert nisa.portfolio_value == decimal.Decimal(2505)

    def test_withdrawal_over_portolio_value(self):

        nisa = yenwealth.investments.NisaAccount(
            asset_map={
                "VGT": yenwealth.investments.Asset(
                    name="VGT",
                    principal=decimal.Decimal(100),
                    gain=decimal.Decimal(100),
                    annual_management_cost_rate=decimal.Decimal(0)
                )
            },
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT"])
        )

        with pytest.raises(yenwealth.investments.InsufficientFunds):

            nisa.withdraw(
                decimal.Decimal(210)
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
            },
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VGT": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VGT"])
        )

        assert nisa.asset_map["VGT"].principal == initial_principal
        assert nisa.asset_map["VGT"].gain == decimal.Decimal(100)
        assert nisa.portfolio_value == initial_portfolio_value

        desired_amount = decimal.Decimal(50)

        nisa.withdraw(
            desired_amount
        )

        assert nisa.portfolio_value == decimal.Decimal(150)
        assert nisa.asset_map["VGT"].gain == decimal.Decimal(75)
        assert nisa.asset_map["VGT"].principal == decimal.Decimal(75)

    def test_init_rejects_account_asset_missing_from_strategy(self):

        with pytest.raises(ValueError, match="nisa account"):
            yenwealth.investments.NisaAccount(
                asset_map=self.asset_map(principal_vgt=0, principal_voo=0),
                asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                    weights={"VOO": decimal.Decimal(1)}
                ),
                asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VOO"])
            )

    def test_init_rejects_strategy_asset_missing_from_account(self):

        with pytest.raises(ValueError, match="asset_purchase_strategy"):
            yenwealth.investments.NisaAccount(
                asset_map={
                    "VOO": yenwealth.investments.Asset(
                        name="VOO",
                        principal=decimal.Decimal(0),
                        gain=decimal.Decimal(0),
                        annual_management_cost_rate=decimal.Decimal(0)
                    )
                },
                asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                    weights={"VOO": decimal.Decimal(1), "VGT": decimal.Decimal(1)}
                ),
                asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VOO"])
            )


class TestSimpleInvestmentManager:

    @pytest.fixture
    def investment_manager(self) -> yenwealth.investments.SimpleInvestmentManager:

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
            capital_gain_tax_rate=decimal.Decimal("0.20"),
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VOO"])
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
            contribution_start_year=2020,
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VOO"]),
            ideco_pension_payout_plan=yenwealth.investments.IdecoPensionPayoutPlan(
                start_age=75,
                period_in_years=20
            )
        )

        # 3. Old NISA Account: zero-value VOO portfolio
        old_nisa = yenwealth.investments.OldNisaAccount(
            year_to_asset_map={
                2024: {
                    "VOO": yenwealth.investments.Asset(
                        name="VOO",
                        principal=decimal.Decimal(0),
                        gain=decimal.Decimal(0),
                        annual_management_cost_rate=decimal.Decimal(0)
                    )
                }
            },
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VOO"])
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
            },
            asset_purchase_strategy=yenwealth.investments.ProportionalAssetPurchaseStrategy(
                weights={"VOO": decimal.Decimal(1)}
            ),
            asset_sale_strategy=yenwealth.investments.SequentialAssetSaleStrategy(["VOO"])
        )

        return yenwealth.investments.SimpleInvestmentManager(
            ordinary_investment_account=ordinary,
            ideco_investment_account=ideco,
            old_nisa_account=old_nisa,
            nisa_account=nisa,
            simulation_start_age=30,
            simulation_start_year=2024
        )

    @staticmethod
    def create_investment_manager(
        manager: yenwealth.investments.SimpleInvestmentManager,
        **overrides
    ) -> yenwealth.investments.SimpleInvestmentManager:

        arguments = {
            "ordinary_investment_account": manager.ordinary_investment_account,
            "ideco_investment_account": manager.ideco_investment_account,
            "old_nisa_account": manager.old_nisa_account,
            "nisa_account": manager.nisa_account,
            "simulation_start_age": manager.simulation_start_age,
            "simulation_start_year": manager.simulation_start_year,
        }
        arguments.update(overrides)

        return yenwealth.investments.SimpleInvestmentManager(**arguments)

    def test_init_requires_at_least_one_account(self, investment_manager):

        with pytest.raises(ValueError, match="At least one investment account must be configured"):
            self.create_investment_manager(
                investment_manager,
                ordinary_investment_account=None,
                ideco_investment_account=None,
                old_nisa_account=None,
                nisa_account=None,
            )

    def test_init_allows_ordinary_account_to_be_omitted(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ordinary_investment_account=None,
        )

        assert manager.ordinary_investment_account is None
        assert manager.portfolio_value == decimal.Decimal(0)
        assert manager.after_tax_portfolio_value == decimal.Decimal(0)
        assert "ordinary_investment_account" not in manager.get_portfolio_summary()

    def test_init_allows_ideco_account_to_be_omitted(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ideco_investment_account=None,
        )

        assert manager.ideco_investment_account is None
        assert manager.portfolio_value == decimal.Decimal(0)
        assert manager.after_tax_portfolio_value == decimal.Decimal(0)
        assert "ideco_investment_account" not in manager.get_portfolio_summary()

    def test_init_omits_only_old_nisa_account_from_summary_when_not_configured(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            old_nisa_account=None,
        )

        assert manager.old_nisa_account is None

        assert manager.nisa_account is not None
        manager.nisa_account.asset_map["VOO"].principal = decimal.Decimal(1_000_000)
        summary = manager.get_portfolio_summary()

        assert "old_nisa_account" not in set(summary)
        assert summary["nisa_account"] == decimal.Decimal(1_000_000)
        assert summary["total_portfolio_value"] == decimal.Decimal(1_000_000)

        description = manager.get_formatted_portfolio_summary_description()
        assert "old_nisa_account" not in description

    def test_init_omits_nisa_account_from_summary_when_not_configured(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            nisa_account=None,
        )

        assert manager.nisa_account is None

        ordinary_account = manager.ordinary_investment_account
        assert ordinary_account is not None
        ordinary_account.asset_map["VOO"].principal = decimal.Decimal(1_000_000)
        summary = manager.get_portfolio_summary()

        assert "nisa_account" not in summary
        assert summary["ordinary_investment_account"] == decimal.Decimal(1_000_000)
        assert summary["total_portfolio_value"] == decimal.Decimal(1_000_000)

        description = manager.get_formatted_portfolio_summary_description()
        assert "\nnisa_account:" not in description

    def test_deposit_without_old_nisa_account(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            old_nisa_account=None,
        )

        manager.deposit(amount=decimal.Decimal(4_000_000), age=30)

        assert manager.old_nisa_account is None
        assert manager.ideco_investment_account is not None
        assert manager.ideco_investment_account.portfolio_value == decimal.Decimal(276_000)
        assert manager.nisa_account is not None
        assert manager.nisa_account.portfolio_value == decimal.Decimal(3_600_000)
        assert manager.ordinary_investment_account is not None
        assert manager.ordinary_investment_account.portfolio_value == decimal.Decimal(124_000)

    def test_deposit_without_nisa_account_uses_ideco_then_ordinary_account(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            nisa_account=None,
        )

        assert manager.nisa_account is None

        manager.deposit(amount=decimal.Decimal(1_000_000), age=30)

        ideco_account = manager.ideco_investment_account
        ordinary_account = manager.ordinary_investment_account

        assert ideco_account is not None
        assert ordinary_account is not None
        assert ideco_account.portfolio_value == decimal.Decimal(276_000)
        assert ordinary_account.portfolio_value == decimal.Decimal(724_000)

    def test_deposit_without_ordinary_account_uses_tax_advantaged_capacity(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ordinary_investment_account=None,
        )

        assert manager.ideco_investment_account is not None
        assert manager.ideco_investment_account.portfolio_value == decimal.Decimal(0)
        assert manager.nisa_account is not None
        assert manager.nisa_account.portfolio_value == decimal.Decimal(0)

        manager.deposit(amount=decimal.Decimal(3_000_000), age=30)

        assert manager.ideco_investment_account.portfolio_value == decimal.Decimal(276_000)
        assert manager.nisa_account.portfolio_value == decimal.Decimal(2_724_000)

    def test_deposit_without_ideco_account_uses_nisa_then_ordinary_account(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ideco_investment_account=None,
        )
        assert manager.ordinary_investment_account is not None
        assert manager.nisa_account is not None
        assert manager.nisa_account.portfolio_value == decimal.Decimal(0)
        assert manager.ordinary_investment_account.portfolio_value == decimal.Decimal(0)

        manager.deposit(amount=decimal.Decimal(4_000_000), age=30)

        assert manager.nisa_account.portfolio_value == decimal.Decimal(3_600_000)
        assert manager.ordinary_investment_account.portfolio_value == decimal.Decimal(400_000)

    def test_deposit_without_ideco_or_ordinary_account_requires_capacity(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ordinary_investment_account=None,
            ideco_investment_account=None,
        )

        with pytest.raises(ValueError, match="ordinary investment account is not configured"):
            manager.deposit(amount=decimal.Decimal(4_000_000), age=30)

    def test_deposit_exceeding_tax_advantaged_limits_requires_ordinary_account(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ordinary_investment_account=None,
        )

        with pytest.raises(ValueError, match="ordinary investment account is not configured"):
            manager.deposit(amount=decimal.Decimal(5_000_000), age=30)

    def test_withdraw_without_ordinary_account_uses_old_nisa_then_nisa(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ordinary_investment_account=None,
        )

        old_nisa_account = manager.old_nisa_account
        assert old_nisa_account is not None

        old_nisa_account.year_to_asset_map = {
            2024: {
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(500_000),
                    gain=decimal.Decimal(0),
                    annual_management_cost_rate=decimal.Decimal(0),
                )
            }
        }

        assert manager.nisa_account is not None
        manager.nisa_account.asset_map["VOO"].principal = decimal.Decimal(2_000_000)

        manager.withdraw(desired_cash=decimal.Decimal(2_000_000))

        assert old_nisa_account.portfolio_value == decimal.Decimal(0)
        assert manager.nisa_account.portfolio_value == decimal.Decimal(500_000)

    def test_withdraw_without_ideco_account_uses_old_nisa_then_nisa(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ideco_investment_account=None,
        )

        old_nisa_account = manager.old_nisa_account
        assert old_nisa_account is not None

        old_nisa_account.year_to_asset_map = {
            2024: {
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(500_000),
                    gain=decimal.Decimal(0),
                    annual_management_cost_rate=decimal.Decimal(0),
                )
            }
        }

        assert manager.nisa_account is not None
        manager.nisa_account.asset_map["VOO"].principal = decimal.Decimal(2_000_000)

        manager.withdraw(desired_cash=decimal.Decimal(2_000_000))

        assert old_nisa_account.portfolio_value == decimal.Decimal(0)
        assert manager.nisa_account.portfolio_value == decimal.Decimal(500_000)

    def test_withdraw_without_old_nisa_account_uses_nisa(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ordinary_investment_account=None,
            old_nisa_account=None,
        )
        assert manager.nisa_account is not None
        manager.nisa_account.asset_map["VOO"].principal = decimal.Decimal(2_000_000)

        manager.withdraw(desired_cash=decimal.Decimal(1_000_000))

        assert manager.old_nisa_account is None
        assert manager.nisa_account.portfolio_value == decimal.Decimal(1_000_000)

    def test_withdraw_without_nisa_account_uses_ordinary_then_old_nisa(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            nisa_account=None,
        )

        assert manager.ordinary_investment_account is not None
        manager.ordinary_investment_account.asset_map["VOO"].principal = decimal.Decimal(500_000)

        old_nisa_account = manager.old_nisa_account

        assert old_nisa_account is not None
        old_nisa_account.year_to_asset_map[2024]["VOO"].principal = decimal.Decimal(500_000)

        manager.withdraw(desired_cash=decimal.Decimal(750_000))

        assert manager.nisa_account is None
        assert manager.ordinary_investment_account.portfolio_value == decimal.Decimal(0)
        assert old_nisa_account.portfolio_value == decimal.Decimal(250_000)

    def test_withdraw_without_ordinary_account_raises_when_funds_are_insufficient(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ordinary_investment_account=None,
        )

        old_nisa_account = manager.old_nisa_account
        assert old_nisa_account is not None

        old_nisa_account.year_to_asset_map[2024]["VOO"].principal = decimal.Decimal(500_000)
        assert manager.nisa_account is not None
        manager.nisa_account.asset_map["VOO"].principal = decimal.Decimal(2_000_000)

        with pytest.raises(yenwealth.investments.InsufficientFunds, match="Not enough funds"):
            manager.withdraw(desired_cash=decimal.Decimal(3_000_000))

    def test_advance_one_year_without_ordinary_account(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ordinary_investment_account=None,
        )

        manager.advance_one_year({"VOO": decimal.Decimal("0.05")})

        assert manager.current_year == 2025

    def test_advance_one_year_without_ideco_account(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ideco_investment_account=None,
        )

        manager.advance_one_year({"VOO": decimal.Decimal("0.05")})

        assert manager.current_year == 2025

    def test_advance_one_year_without_old_nisa_account(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            old_nisa_account=None,
        )

        manager.advance_one_year({"VOO": decimal.Decimal("0.05")})

        assert manager.old_nisa_account is None
        assert manager.current_year == 2025

    def test_advance_one_year_without_nisa_account(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            nisa_account=None,
        )

        manager.advance_one_year({"VOO": decimal.Decimal("0.05")})

        assert manager.nisa_account is None
        assert manager.current_year == 2025

    def test_optimize_investments_skips_ordinary_account_when_absent(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ordinary_investment_account=None,
        )

        manager.optimize_investments()

        assert manager.ordinary_investment_account is None

    def test_optimize_investments_skips_ideco_action_when_account_is_absent(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ideco_investment_account=None,
        )
        manager.current_year = 2069

        manager.optimize_investments()

        assert manager.ideco_investment_account is None

    def test_optimize_investments_without_old_nisa_account_still_topups_nisa(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            old_nisa_account=None,
        )

        assert manager.ordinary_investment_account is not None

        manager.ordinary_investment_account.asset_map["VOO"].principal = decimal.Decimal(10_000_000)
        manager.current_year = 2044

        manager.optimize_investments()

        assert manager.old_nisa_account is None
        assert manager.nisa_account is not None
        assert manager.nisa_account.asset_map["VOO"].principal == decimal.Decimal(3_600_000)
        assert manager.ordinary_investment_account.asset_map["VOO"].principal == decimal.Decimal(6_400_000)

    def test_optimize_investments_without_nisa_account_skips_nisa_topup(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            old_nisa_account=None,
            nisa_account=None,
        )

        assert manager.ordinary_investment_account is not None
        manager.ordinary_investment_account.asset_map["VOO"].principal = decimal.Decimal(10_000_000)

        manager.optimize_investments()

        assert manager.nisa_account is None
        assert manager.ordinary_investment_account.portfolio_value == decimal.Decimal(10_000_000)

    def test_optimize_investments_without_ideco_account_still_topups_nisa(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ideco_investment_account=None,
        )
        assert manager.ordinary_investment_account is not None
        manager.ordinary_investment_account.asset_map["VOO"].principal = decimal.Decimal(10_000_000)

        assert manager.nisa_account is not None
        assert manager.nisa_account.portfolio_value == decimal.Decimal(0)
        assert manager.ordinary_investment_account.portfolio_value == decimal.Decimal(10_000_000)

        manager.current_year = 2069
        manager.optimize_investments()

        assert manager.nisa_account.asset_map["VOO"].principal == decimal.Decimal(3_600_000)
        assert manager.ordinary_investment_account.asset_map["VOO"].principal == decimal.Decimal(6_400_000)

    def test_optimize_expired_old_nisa_requires_ordinary_account(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ordinary_investment_account=None,
        )

        old_nisa_account = manager.old_nisa_account
        assert old_nisa_account is not None

        old_nisa_account.year_to_asset_map = {
            2024: {
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(1_000_000),
                    gain=decimal.Decimal(0),
                    annual_management_cost_rate=decimal.Decimal(0),
                )
            }
        }
        manager.current_year = 2044

        with pytest.raises(ValueError, match="ordinary investment account is not configured"):
            manager.optimize_investments()

        assert 2024 not in old_nisa_account.year_to_asset_map

    def test_optimize_ideco_lump_sum_requires_ordinary_account(self, investment_manager):

        manager = self.create_investment_manager(
            investment_manager,
            ordinary_investment_account=None,
        )
        assert manager.ideco_investment_account is not None
        manager.ideco_investment_account.asset_map["VOO"].principal = decimal.Decimal(10_000_000)
        manager.current_year = 2069

        with pytest.raises(ValueError, match="ordinary investment account is not configured"):
            manager.optimize_investments()

        assert manager.ideco_investment_account is not None
        assert manager.ideco_investment_account.portfolio_value == decimal.Decimal(0)

    def test_deposit_priority(self, investment_manager):

        # Deposit 5,000,000 Yen at age 30
        # Expected order: iDeCo (max 276,000) -> NISA (max 3,600,000) -> Ordinary (rest: 1,124,000)
        investment_manager.deposit(amount=decimal.Decimal(5_000_000), age=30)

        assert investment_manager.ideco_investment_account.portfolio_value == decimal.Decimal(276_000)
        assert investment_manager.nisa_account is not None
        assert investment_manager.nisa_account.asset_map["VOO"].principal == decimal.Decimal(3_600_000)
        assert investment_manager.ordinary_investment_account.asset_map["VOO"].principal == decimal.Decimal(1_124_000)

    def test_withdraw_priority(self, investment_manager):

        # Setup initial balances directly
        investment_manager.ordinary_investment_account.asset_map["VOO"].principal = decimal.Decimal(1_000_000)
        old_nisa_account = investment_manager.old_nisa_account
        assert old_nisa_account is not None

        old_nisa_account.year_to_asset_map = {
            2010: {
                "VOO": yenwealth.investments.Asset(
                    name="VOO",
                    principal=decimal.Decimal(500_000),
                    gain=decimal.Decimal(0),
                    annual_management_cost_rate=decimal.Decimal(0)
                )
            }
        }
        assert investment_manager.nisa_account is not None
        investment_manager.nisa_account.asset_map["VOO"].principal = decimal.Decimal(2_000_000)

        # Withdraw 2,000,000 Yen
        # Expected order: Ordinary (1,000,000) -> Old NISA (500,000) -> NISA (500,000)
        investment_manager.withdraw(desired_cash=decimal.Decimal(2_000_000))

        assert investment_manager.ordinary_investment_account.portfolio_value == decimal.Decimal(0)
        assert old_nisa_account.portfolio_value == decimal.Decimal(0)
        assert investment_manager.nisa_account.portfolio_value == decimal.Decimal(1_500_000)

    def test_optimize_investments_old_nisa_liquidation(self, investment_manager):

        # Current year = start_year (2024) + age (50) - start_age (30) = 2044
        # 20 years prior = 2024. Populate Old NISA portfolio for 2024
        old_nisa_account = investment_manager.old_nisa_account
        assert old_nisa_account is not None

        old_nisa_account.year_to_asset_map = {
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
        assert 2024 not in old_nisa_account.year_to_asset_map
        assert investment_manager.nisa_account is not None
        assert investment_manager.nisa_account.asset_map["VOO"].principal == decimal.Decimal(1_000_000)

    def test_optimize_investments_ideco_lump_sum_and_nisa_topup(self, investment_manager):

        investment_manager.ideco_investment_account.asset_map["VOO"].principal = decimal.Decimal(10_000_000)

        # Year at which we hit age of 75, and ideco policy was set to do lump withdrawal at that age
        investment_manager.current_year = 2069

        investment_manager.optimize_investments()

        # 1. iDeCo 10M transferred to Ordinary Account tax-free
        # 2. Ordinary Account then transfers 3.6M (annual limit) to NISA Account
        assert investment_manager.ideco_investment_account.portfolio_value == decimal.Decimal(0)
        assert investment_manager.nisa_account is not None
        assert investment_manager.nisa_account.asset_map["VOO"].principal == decimal.Decimal(3_600_000)
        assert investment_manager.ordinary_investment_account.asset_map['VOO'].principal == decimal.Decimal(6_400_000)
