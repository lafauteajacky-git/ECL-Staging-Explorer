"""Numerical helpers shared by the demonstrator calculation modules."""

from __future__ import annotations

import numpy as np
import pandas as pd


def safe_divide(
    numerator: float | pd.Series | np.ndarray,
    denominator: float | pd.Series | np.ndarray,
    default: float = 0.0,
):
    """Divide values while returning ``default`` for zero or invalid denominators."""
    numerator_array = np.asarray(numerator, dtype=float)
    denominator_array = np.asarray(denominator, dtype=float)
    broadcast_numerator, broadcast_denominator = np.broadcast_arrays(
        numerator_array,
        denominator_array,
    )
    result = np.full(broadcast_numerator.shape, default, dtype=float)
    valid = (
        np.isfinite(broadcast_numerator)
        & np.isfinite(broadcast_denominator)
        & (broadcast_denominator != 0)
    )
    np.divide(
        broadcast_numerator,
        broadcast_denominator,
        out=result,
        where=valid,
    )

    if np.ndim(result) == 0:
        return float(result)
    if isinstance(numerator, pd.Series):
        return pd.Series(result, index=numerator.index, name=numerator.name)
    if isinstance(denominator, pd.Series):
        return pd.Series(result, index=denominator.index)
    return result
