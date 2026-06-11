"""Pedagogical risk-parameter calculations for the ECL Staging Explorer.

Lifetime PD is derived from the 12-month PD using a constant annual hazard
assumption. The method is deliberately simple and transparent:

    cumulative PD(t) = 1 - (1 - PD 12m) ** t

where ``t`` is the contractual horizon expressed in years. A minimum horizon
of one year is retained so the demonstrator remains consistent with its
simplified 12-month PD convention.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from modules.calculation_utils import safe_divide


LIFETIME_PD_METHOD = "Constant annual hazard derived from 12-month PD"


def calculate_lifetime_pd(
    pd_12m: pd.Series | np.ndarray | float,
    residual_maturity_months: pd.Series | np.ndarray | float,
):
    """Calculate cumulative lifetime PD over the residual maturity."""
    pd_values = np.asarray(pd_12m, dtype=float)
    maturity_values = np.asarray(residual_maturity_months, dtype=float)
    pd_values, maturity_values = np.broadcast_arrays(pd_values, maturity_values)

    valid = np.isfinite(pd_values) & np.isfinite(maturity_values)
    clipped_pd = np.clip(pd_values, 0.0, 1.0)
    horizon_years = np.maximum(np.clip(maturity_values, 0.0, None) / 12.0, 1.0)
    lifetime_pd = np.full(clipped_pd.shape, np.nan, dtype=float)
    lifetime_pd[valid] = 1.0 - np.power(1.0 - clipped_pd[valid], horizon_years[valid])
    lifetime_pd = np.clip(lifetime_pd, 0.0, 1.0)

    if np.ndim(lifetime_pd) == 0:
        return float(lifetime_pd)
    if isinstance(pd_12m, pd.Series):
        return pd.Series(lifetime_pd, index=pd_12m.index, name="pd_lifetime")
    if isinstance(residual_maturity_months, pd.Series):
        return pd.Series(lifetime_pd, index=residual_maturity_months.index, name="pd_lifetime")
    return lifetime_pd


def add_lifetime_pd_metrics(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Add calculated lifetime-PD fields to an exposure-level portfolio."""
    result = portfolio.copy()
    pd_12m = pd.to_numeric(result["pd_12m"], errors="coerce")
    maturity = pd.to_numeric(result["residual_maturity_months"], errors="coerce")
    result["pd_lifetime"] = calculate_lifetime_pd(pd_12m, maturity).round(6)
    result["pd_lifetime_multiplier"] = safe_divide(result["pd_lifetime"], pd_12m)
    result["pd_lifetime_method"] = LIFETIME_PD_METHOD
    return result


def build_lifetime_pd_term_structure(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Build annual cumulative and marginal PD points for each exposure."""
    columns = [
        "loan_id",
        "stage",
        "product_type",
        "sector",
        "current_rating",
        "ead",
        "pd_12m",
        "residual_maturity_months",
        "year",
        "horizon_months",
        "survival_probability",
        "cumulative_pd",
        "marginal_pd",
    ]
    if portfolio.empty:
        return pd.DataFrame(columns=columns)

    frames: list[pd.DataFrame] = []
    for _, row in portfolio.iterrows():
        pd_12m = pd.to_numeric(pd.Series([row.get("pd_12m")]), errors="coerce").iloc[0]
        maturity = pd.to_numeric(
            pd.Series([row.get("residual_maturity_months")]),
            errors="coerce",
        ).iloc[0]
        if pd.isna(pd_12m) or pd.isna(maturity):
            continue

        effective_maturity = max(float(maturity), 12.0)
        annual_points = max(1, int(np.ceil(effective_maturity / 12.0)))
        horizons = np.minimum(np.arange(1, annual_points + 1) * 12.0, effective_maturity)
        cumulative = calculate_lifetime_pd(
            np.repeat(float(pd_12m), annual_points),
            horizons,
        )
        marginal = np.diff(np.concatenate(([0.0], cumulative)))
        frame = pd.DataFrame(
            {
                "loan_id": row.get("loan_id"),
                "stage": row.get("stage", "Not staged"),
                "product_type": row.get("product_type", "Unknown"),
                "sector": row.get("sector", "Unknown"),
                "current_rating": row.get("current_rating", np.nan),
                "ead": row.get("ead", 0.0),
                "pd_12m": float(pd_12m),
                "residual_maturity_months": float(maturity),
                "year": np.arange(1, annual_points + 1),
                "horizon_months": horizons,
                "survival_probability": 1.0 - cumulative,
                "cumulative_pd": cumulative,
                "marginal_pd": marginal,
            }
        )
        frames.append(frame)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns)


def summarize_risk_parameters(portfolio: pd.DataFrame) -> dict[str, float | str]:
    """Return portfolio-level PD, LGD and maturity indicators."""
    pd_12m = pd.to_numeric(portfolio["pd_12m"], errors="coerce")
    pd_lifetime = pd.to_numeric(portfolio["pd_lifetime"], errors="coerce")
    lgd = pd.to_numeric(portfolio["lgd"], errors="coerce")
    ead = pd.to_numeric(portfolio["ead"], errors="coerce").clip(lower=0).fillna(0.0)
    maturity = pd.to_numeric(portfolio["residual_maturity_months"], errors="coerce")

    valid_pd_12m = pd_12m.notna() & ead.gt(0)
    valid_lifetime = pd_lifetime.notna() & ead.gt(0)
    valid_lgd = lgd.notna() & ead.gt(0)
    weighted_pd_12m = safe_divide(
        float((pd_12m.loc[valid_pd_12m] * ead.loc[valid_pd_12m]).sum()),
        float(ead.loc[valid_pd_12m].sum()),
    )
    weighted_lifetime = safe_divide(
        float((pd_lifetime.loc[valid_lifetime] * ead.loc[valid_lifetime]).sum()),
        float(ead.loc[valid_lifetime].sum()),
    )
    weighted_lgd = safe_divide(
        float((lgd.loc[valid_lgd] * ead.loc[valid_lgd]).sum()),
        float(ead.loc[valid_lgd].sum()),
    )
    return {
        "pd_12m_ead_weighted": weighted_pd_12m,
        "pd_lifetime_ead_weighted": weighted_lifetime,
        "pd_lifetime_multiplier": safe_divide(weighted_lifetime, weighted_pd_12m),
        "lgd_ead_weighted": weighted_lgd,
        "average_residual_maturity_months": float(maturity.mean()) if maturity.notna().any() else 0.0,
        "lifetime_pd_method": LIFETIME_PD_METHOD,
    }


def aggregate_lifetime_pd_curve(
    term_structure: pd.DataFrame,
    dimension: str = "stage",
) -> pd.DataFrame:
    """Aggregate annual cumulative PD curves using EAD-weighted averages."""
    if term_structure.empty or dimension not in term_structure:
        return pd.DataFrame(columns=[dimension, "year", "cumulative_pd", "marginal_pd", "ead"])

    records = []
    for (dimension_value, year), group in term_structure.groupby([dimension, "year"], dropna=False):
        ead = pd.to_numeric(group["ead"], errors="coerce").clip(lower=0).fillna(0.0)
        records.append(
            {
                dimension: dimension_value,
                "year": int(year),
                "cumulative_pd": safe_divide(
                    float((group["cumulative_pd"] * ead).sum()),
                    float(ead.sum()),
                ),
                "marginal_pd": safe_divide(
                    float((group["marginal_pd"] * ead).sum()),
                    float(ead.sum()),
                ),
                "ead": float(ead.sum()),
            }
        )
    return pd.DataFrame(records).sort_values([dimension, "year"]).reset_index(drop=True)
