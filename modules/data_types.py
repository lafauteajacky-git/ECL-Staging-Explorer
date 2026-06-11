"""Shared data-type coercion helpers for synthetic portfolio fields."""

from __future__ import annotations

import pandas as pd


TRUE_BOOLEAN_VALUES = {"true", "1", "yes", "y", "oui", "o", "vrai"}
FALSE_BOOLEAN_VALUES = {"false", "0", "no", "n", "non", "f", "faux", ""}


def coerce_boolean_series(series: pd.Series) -> pd.Series:
    """Return a nullable input series as strict booleans.

    Native booleans and numeric 0/1 values are preserved. Common textual
    representations are parsed explicitly so that the string ``"False"`` is
    never interpreted as truthy by Python. Unknown or missing values default to
    ``False``; data-quality controls remain responsible for flagging invalid
    source values when relevant.
    """
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)

    normalized = series.fillna("").astype(str).str.strip().str.lower()
    result = pd.Series(False, index=series.index, dtype=bool)
    result.loc[normalized.isin(TRUE_BOOLEAN_VALUES)] = True
    result.loc[normalized.isin(FALSE_BOOLEAN_VALUES)] = False
    return result
