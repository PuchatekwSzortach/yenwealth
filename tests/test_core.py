import pandas
import pytest

import yenwealth.core


class TestEconomicData:

    def test_init_raises_value_error_on_mismatched_index(self, sample_returns, sample_inflation):

        mismatched_inflation = sample_inflation.copy()
        mismatched_inflation.index = pandas.date_range(start="2011-01-01", periods=10, freq="YE")

        with pytest.raises(ValueError, match="EconomicData inputs must share the same index"):
            yenwealth.core.EconomicData(
                return_on_assets_over_time=sample_returns,
                inflation_over_time=mismatched_inflation,
            )
