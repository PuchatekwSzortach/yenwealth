import decimal

import pytest

import yenwealth.numeric


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (decimal.Decimal("1.25"), decimal.Decimal("1.25")),
        (42, decimal.Decimal(42)),
        (0.1, decimal.Decimal("0.1")),
    ],
)
def test_to_decimal_converts_supported_types(value, expected):

    result = yenwealth.numeric.to_decimal(value)

    assert isinstance(result, decimal.Decimal)
    assert result == expected


@pytest.mark.parametrize("value", [True, "0.1", None])
def test_to_decimal_raises_type_error_for_unsupported_types(value):

    with pytest.raises(TypeError, match="Expected a Decimal, int, or float"):
        yenwealth.numeric.to_decimal(value)
