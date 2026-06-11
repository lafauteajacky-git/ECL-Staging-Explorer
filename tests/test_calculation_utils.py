import numpy as np
import pandas as pd

from modules.calculation_utils import safe_divide


def test_safe_divide_returns_default_for_zero_denominator():
    assert safe_divide(10.0, 0.0) == 0.0


def test_safe_divide_handles_series_without_nan_or_infinity():
    numerator = pd.Series([10.0, 5.0, np.nan, 8.0])
    denominator = pd.Series([2.0, 0.0, 4.0, np.nan])

    result = safe_divide(numerator, denominator)

    assert result.tolist() == [5.0, 0.0, 0.0, 0.0]
    assert np.isfinite(result).all()


def test_safe_divide_supports_scalar_denominator_for_series():
    numerator = pd.Series([10.0, 20.0])

    result = safe_divide(numerator, 10.0)

    assert result.tolist() == [1.0, 2.0]
