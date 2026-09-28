import pandas
import pytest

import yenwealth.core


@pytest.fixture
def sample_index():
    return pandas.date_range(start="2010-01-01", periods=10, freq="YE")


@pytest.fixture
def sample_returns(sample_index):
    return pandas.DataFrame(
        {"Asset_A": range(1, 11), "Asset_B": range(11, 21)},
        index=sample_index,
    )


@pytest.fixture
def sample_inflation(sample_index):
    return pandas.DataFrame(
        {"Inflation": [0.02] * 10},
        index=sample_index,
    )


@pytest.fixture
def sample_economic_data(sample_returns, sample_inflation):
    return yenwealth.core.EconomicData(
        return_on_assets_over_time=sample_returns,
        inflation_over_time=sample_inflation,
    )
