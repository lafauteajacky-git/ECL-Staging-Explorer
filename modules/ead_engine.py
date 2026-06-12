"""Pedagogical Exposure at Default engine.

The module enriches synthetic exposures with undrawn commitments, credit
conversion factors and simplified amortisation schedules. It is intended for
transparent IFRS 9 demonstrations, not for production calibration.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from modules.calculation_utils import safe_divide


EAD_METHOD = "Drawn exposure plus CCF-converted undrawn commitment"

CALCULATED_EAD_COLUMNS = {
    "ead_accounting",
    "ead_drawn",
    "ead_undrawn",
    "ccf_adjusted",
    "ead_off_balance",
    "ead_at_default",
    "ead_12m",
}

BASE_CCF_BY_PRODUCT = {
    "Mortgage": 0.00,
    "SME term loan": 0.20,
    "Corporate loan": 0.40,
    "Consumer loan": 0.05,
    "Credit card": 0.75,
}

AMORTISATION_BY_PRODUCT = {
    "Mortgage": "Amortising",
    "SME term loan": "Amortising",
    "Corporate loan": "Bullet",
    "Consumer loan": "Amortising",
    "Credit card": "Revolving",
}


def _numeric_series(
    frame: pd.DataFrame,
    column: str,
    default: float = 0.0,
) -> pd.Series:
    values = (
        frame[column]
        if column in frame.columns
        else pd.Series(default, index=frame.index, dtype=float)
    )
    return pd.to_numeric(values, errors="coerce")


def add_synthetic_ead_inputs(
    portfolio: pd.DataFrame,
    seed: int = 42,
) -> pd.DataFrame:
    """Add reproducible undrawn commitments and contractual EAD assumptions."""
    result = portfolio.copy()
    if result.empty:
        return result

    rng = np.random.default_rng(seed)
    drawn = _numeric_series(result, "ead", np.nan).clip(lower=0)
    product = result["product_type"].astype(str)

    undrawn_ratio_ranges = {
        "Mortgage": (0.00, 0.03),
        "SME term loan": (0.05, 0.35),
        "Corporate loan": (0.10, 0.60),
        "Consumer loan": (0.00, 0.10),
        "Credit card": (0.20, 1.20),
    }
    undrawn = np.zeros(len(result), dtype=float)
    for product_type, (low, high) in undrawn_ratio_ranges.items():
        mask = product.eq(product_type).to_numpy()
        undrawn[mask] = (
            drawn.loc[mask].fillna(0).to_numpy()
            * rng.uniform(low, high, size=int(mask.sum()))
        )

    result["undrawn_commitment"] = np.round(undrawn, 2)
    result["credit_limit"] = (
        drawn.fillna(0.0) + result["undrawn_commitment"]
    ).round(2)
    result["utilisation_rate"] = safe_divide(
        drawn.fillna(0.0),
        result["credit_limit"],
    )
    result["ccf_base"] = product.map(BASE_CCF_BY_PRODUCT).fillna(0.0)
    result["amortisation_type"] = (
        product.map(AMORTISATION_BY_PRODUCT).fillna("Bullet")
    )
    result["payment_frequency"] = np.where(
        result["amortisation_type"].eq("Amortising"),
        "Monthly",
        np.where(result["amortisation_type"].eq("Revolving"), "Revolving", "At maturity"),
    )
    result["ead_method"] = EAD_METHOD
    return result


def calculate_ead(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Calculate current and 12-month EAD with stage-sensitive CCF assumptions."""
    result = portfolio.copy()
    drawn_source = (
        "ead_accounting"
        if "ead_accounting" in result.columns
        else "ead"
    )
    drawn = _numeric_series(result, drawn_source, np.nan)
    undrawn = _numeric_series(result, "undrawn_commitment").fillna(0).clip(lower=0)
    base_ccf = _numeric_series(result, "ccf_base").fillna(
        result.get(
            "product_type",
            pd.Series("", index=result.index),
        ).map(BASE_CCF_BY_PRODUCT)
    ).fillna(0.0)
    stage = result.get("stage", pd.Series("Stage 1", index=result.index))
    rating = _numeric_series(result, "current_rating", np.nan)
    utilisation = safe_divide(drawn.clip(lower=0).fillna(0), drawn.clip(lower=0).fillna(0) + undrawn)

    stage_addon = np.select(
        [stage.eq("Stage 2"), stage.eq("Stage 3")],
        [0.10, 0.25],
        default=0.0,
    )
    rating_addon = np.where(rating.ge(8), 0.10, 0.0)
    utilisation_addon = np.where(pd.Series(utilisation, index=result.index).ge(0.80), 0.05, 0.0)
    ccf_adjusted = (
        base_ccf
        + pd.Series(stage_addon, index=result.index)
        + pd.Series(rating_addon, index=result.index)
        + pd.Series(utilisation_addon, index=result.index)
    ).clip(0.0, 1.0)

    off_balance_ead = undrawn * ccf_adjusted
    ead_at_default = drawn + off_balance_ead

    result["ead_accounting"] = drawn
    result["ead_drawn"] = drawn
    result["ead_undrawn"] = undrawn
    result["ccf_adjusted"] = ccf_adjusted
    result["ead_off_balance"] = off_balance_ead
    result["ead_at_default"] = ead_at_default
    maturity = _numeric_series(
        result,
        "residual_maturity_months",
        12,
    ).fillna(12).clip(lower=1)
    twelve_month_endpoint = _ead_at_horizon(
        result,
        np.minimum(12.0, maturity.to_numpy()),
    )
    result["ead_12m"] = (
        ead_at_default.clip(lower=0).fillna(0) + twelve_month_endpoint
    ) / 2.0
    result["ead"] = ead_at_default
    result["ead_method"] = EAD_METHOD
    return result


def has_calculated_ead(portfolio: pd.DataFrame) -> bool:
    """Return whether the portfolio already contains reusable EAD outputs."""
    return CALCULATED_EAD_COLUMNS.issubset(portfolio.columns)


def _ead_at_horizon(portfolio: pd.DataFrame, horizon_months: float | np.ndarray) -> pd.Series:
    """Calculate exposure at a contractual horizon."""
    drawn = _numeric_series(portfolio, "ead_accounting", np.nan).clip(lower=0)
    undrawn = _numeric_series(portfolio, "ead_undrawn").fillna(0).clip(lower=0)
    ccf = _numeric_series(portfolio, "ccf_adjusted").fillna(0).clip(0, 1)
    maturity = _numeric_series(
        portfolio,
        "residual_maturity_months",
        12,
    ).fillna(12).clip(lower=1)
    amortisation = portfolio.get(
        "amortisation_type",
        pd.Series("Bullet", index=portfolio.index),
    ).astype(str)
    horizon = np.broadcast_to(
        np.asarray(horizon_months, dtype=float),
        (len(portfolio),),
    )
    remaining_share = np.where(
        amortisation.eq("Amortising"),
        np.maximum(1.0 - horizon / maturity.to_numpy(), 0.0),
        np.where(
            amortisation.eq("Bullet"),
            (horizon < maturity.to_numpy()).astype(float),
            1.0,
        ),
    )
    projected_drawn = drawn.fillna(0).to_numpy() * remaining_share
    projected_undrawn = np.where(
        amortisation.eq("Revolving"),
        undrawn.to_numpy(),
        undrawn.to_numpy() * remaining_share,
    )
    projected_ead = projected_drawn + projected_undrawn * ccf.to_numpy()
    return pd.Series(projected_ead, index=portfolio.index)


def build_ead_term_structure(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Build annual EAD projections for each exposure."""
    columns = [
        "loan_id",
        "stage",
        "product_type",
        "amortisation_type",
        "year",
        "horizon_months",
        "ead_drawn_projected",
        "ead_off_balance_projected",
        "ead_projected",
    ]
    if portfolio.empty:
        return pd.DataFrame(columns=columns)

    source = (
        portfolio.copy()
        if has_calculated_ead(portfolio)
        else calculate_ead(portfolio)
    ).reset_index(drop=True)
    maturity = _numeric_series(source, "residual_maturity_months", 12).fillna(12).clip(lower=1)
    annual_points = np.maximum(np.ceil(maturity.to_numpy() / 12.0).astype(int), 1)
    positions = np.repeat(np.arange(len(source)), annual_points)
    starts = np.repeat(np.cumsum(np.r_[0, annual_points[:-1]]), annual_points)
    year = np.arange(int(annual_points.sum())) - starts + 1
    repeated_maturity = maturity.to_numpy()[positions]
    horizon = np.minimum(year * 12.0, repeated_maturity)
    previous_horizon = np.maximum((year - 1) * 12.0, 0.0)
    exposure_horizon = previous_horizon + (horizon - previous_horizon) / 2.0

    drawn = source["ead_accounting"].fillna(0).clip(lower=0).to_numpy()[positions]
    undrawn = source["ead_undrawn"].fillna(0).clip(lower=0).to_numpy()[positions]
    ccf = source["ccf_adjusted"].fillna(0).clip(0, 1).to_numpy()[positions]
    amortisation = source["amortisation_type"].astype(str).to_numpy()[positions]
    remaining_share = np.where(
        amortisation == "Amortising",
        np.maximum(1.0 - exposure_horizon / repeated_maturity, 0.0),
        np.where(
            amortisation == "Bullet",
            (exposure_horizon < repeated_maturity).astype(float),
            1.0,
        ),
    )
    projected_drawn = drawn * remaining_share
    projected_undrawn = np.where(
        amortisation == "Revolving",
        undrawn,
        undrawn * remaining_share,
    )
    off_balance = projected_undrawn * ccf

    def repeat_column(column: str, default):
        values = (
            source[column].to_numpy()
            if column in source.columns
            else np.full(len(source), default)
        )
        return values[positions]

    return pd.DataFrame(
        {
            "loan_id": repeat_column("loan_id", None),
            "stage": repeat_column("stage", "Not staged"),
            "product_type": repeat_column("product_type", "Unknown"),
            "amortisation_type": amortisation,
            "year": year,
            "horizon_months": horizon,
            "ead_drawn_projected": projected_drawn,
            "ead_off_balance_projected": off_balance,
            "ead_projected": projected_drawn + off_balance,
        },
        columns=columns,
    )


def summarize_ead(portfolio: pd.DataFrame) -> dict[str, float | str]:
    """Return portfolio-level drawn, undrawn and CCF indicators."""
    result = portfolio.copy() if has_calculated_ead(portfolio) else calculate_ead(portfolio)
    drawn = _numeric_series(result, "ead_accounting").clip(lower=0).fillna(0)
    undrawn = _numeric_series(result, "ead_undrawn").clip(lower=0).fillna(0)
    off_balance = _numeric_series(result, "ead_off_balance").clip(lower=0).fillna(0)
    adjusted_ccf = _numeric_series(result, "ccf_adjusted").clip(0, 1)
    return {
        "ead_drawn": float(drawn.sum()),
        "undrawn_commitment": float(undrawn.sum()),
        "ead_off_balance": float(off_balance.sum()),
        "ead_at_default": float(_numeric_series(result, "ead_at_default").sum()),
        "ccf_weighted": safe_divide(
            float((adjusted_ccf * undrawn).sum()),
            float(undrawn.sum()),
        ),
        "utilisation_rate": safe_divide(
            float(drawn.sum()),
            float((drawn + undrawn).sum()),
        ),
        "ead_method": EAD_METHOD,
    }


def aggregate_ead_curve(
    term_structure: pd.DataFrame,
    dimension: str = "product_type",
) -> pd.DataFrame:
    """Aggregate projected EAD curves by product, stage or amortisation type."""
    if term_structure.empty or dimension not in term_structure.columns:
        return pd.DataFrame(
            columns=[
                dimension,
                "year",
                "ead_drawn_projected",
                "ead_off_balance_projected",
                "ead_projected",
            ]
        )
    return (
        term_structure.groupby([dimension, "year"], as_index=False)
        .agg(
            ead_drawn_projected=("ead_drawn_projected", "sum"),
            ead_off_balance_projected=("ead_off_balance_projected", "sum"),
            ead_projected=("ead_projected", "sum"),
        )
        .sort_values([dimension, "year"])
        .reset_index(drop=True)
    )
