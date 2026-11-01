import decimal

import pandas
import pytest

import yenwealth.core


class TestEconomicData:

    def test_init_converts_supported_values_and_preserves_input_frames(self, sample_index):

        returns = pandas.DataFrame(
            {"Asset_A": [decimal.Decimal("0.1"), 1, 0.2]},
            index=sample_index[:3]
        )

        inflation = pandas.DataFrame(
            {"inflation_rate": [0.01, decimal.Decimal("0.02"), 2]},
            index=sample_index[:3]
        )

        economic_data = yenwealth.core.EconomicData(
            return_on_assets_over_time=returns,
            inflation_over_time=inflation,
        )

        assert economic_data.return_on_assets_over_time["Asset_A"].tolist() == [
            decimal.Decimal("0.1"), decimal.Decimal(1), decimal.Decimal("0.2")
        ]
        assert economic_data.inflation_over_time["inflation_rate"].tolist() == [
            decimal.Decimal("0.01"), decimal.Decimal("0.02"), decimal.Decimal(2)
        ]

        pandas.testing.assert_index_equal(economic_data.return_on_assets_over_time.index, returns.index)
        pandas.testing.assert_index_equal(economic_data.inflation_over_time.columns, inflation.columns)

        # check that EconomicData leaves the caller’s input frame unchanged.
        assert isinstance(returns.iloc[0, 0], decimal.Decimal)
        assert type(returns.iloc[1, 0]) is int

    @pytest.mark.parametrize("invalid_value", [True, "0.1"])
    @pytest.mark.parametrize(
        ("frame_name", "column_name"),
        [
            ("return_on_assets_over_time", "Asset_A"),
            ("inflation_over_time", "inflation_rate"),
        ]
    )
    def test_init_raises_contextual_value_error_for_invalid_frame_values(
        self,
        invalid_value,
        frame_name,
        column_name
    ):

        index = pandas.Index(["valid-year", "invalid-year"], name="year")
        returns = pandas.DataFrame({"Asset_A": [0.1, 0.2]}, index=index)
        inflation = pandas.DataFrame({"inflation_rate": [0.02, 0.02]}, index=index)
        bad_frame = pandas.DataFrame({column_name: [0.1, invalid_value]}, index=index)

        if frame_name == "return_on_assets_over_time":
            returns = bad_frame
        else:
            inflation = bad_frame

        with pytest.raises(ValueError, match=f"{frame_name}.*{column_name}.*invalid-year"):
            yenwealth.core.EconomicData(
                return_on_assets_over_time=returns,
                inflation_over_time=inflation,
            )

    def test_init_raises_value_error_on_mismatched_index(self, sample_returns, sample_inflation):

        mismatched_inflation = sample_inflation.copy()
        mismatched_inflation.index = pandas.date_range(start="2011-01-01", periods=10, freq="YE")

        with pytest.raises(ValueError, match="EconomicData inputs must share the same index"):
            yenwealth.core.EconomicData(
                return_on_assets_over_time=sample_returns,
                inflation_over_time=mismatched_inflation,
            )
