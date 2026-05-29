"""Synthetic portfolio generation for the ECL Staging Explorer MVP.

The data produced here is fictional and designed for demonstration only.
It must not be interpreted as representative of any real bank portfolio.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


PRODUCT_TYPES = ["Mortgage", "SME term loan", "Corporate loan", "Consumer loan", "Credit card"]
SECTORS = ["Households", "Manufacturing", "Retail", "Real estate", "Technology", "Energy"]
COUNTRIES = ["FR", "DE", "IT", "ES", "BE", "NL"]
RATINGS = np.arange(1, 11)
DEMO_PORTFOLIO_PROFILES = [
    "Balanced Portfolio",
    "Low Risk Portfolio",
    "Deteriorated Portfolio",
    "Data Quality Issues Portfolio",
    "CRE Stress Portfolio",
]


def generate_portfolio(n_exposures: int = 1_000, seed: int = 42) -> pd.DataFrame:
    """Generate a synthetic credit portfolio with simplified IFRS 9 inputs."""
    rng = np.random.default_rng(seed)

    origination_rating = rng.choice(RATINGS, size=n_exposures, p=[0.05, 0.08, 0.12, 0.16, 0.18, 0.16, 0.11, 0.08, 0.04, 0.02])
    migration = rng.choice([-2, -1, 0, 1, 2, 3], size=n_exposures, p=[0.05, 0.12, 0.50, 0.20, 0.09, 0.04])
    current_rating = np.clip(origination_rating + migration, 1, 10)

    ead = rng.lognormal(mean=11.2, sigma=0.9, size=n_exposures).round(2)
    maturity = rng.integers(1, 121, size=n_exposures)
    base_pd = np.clip(0.002 + (current_rating - 1) * 0.012 + rng.normal(0, 0.005, n_exposures), 0.0005, 0.35)
    pd_12m = np.round(base_pd, 5)
    lifetime_multiplier = np.clip(maturity / 24, 1.2, 5.0)
    pd_lifetime = np.round(np.clip(pd_12m * lifetime_multiplier, 0.001, 0.95), 5)
    lgd = np.round(rng.uniform(0.18, 0.65, size=n_exposures), 4)

    default_flag = rng.random(n_exposures) < np.clip((current_rating - 7) * 0.035, 0.005, 0.18)
    days_past_due = rng.choice([0, 5, 15, 30, 45, 60, 90, 120], size=n_exposures, p=[0.56, 0.14, 0.10, 0.08, 0.05, 0.03, 0.025, 0.015])
    days_past_due = np.where(default_flag, np.maximum(days_past_due, rng.choice([90, 120, 180], n_exposures)), days_past_due)

    collateral_flag = rng.random(n_exposures) < 0.45
    ltv = np.where(collateral_flag, rng.uniform(0.25, 1.25, size=n_exposures), np.nan)

    portfolio = pd.DataFrame(
        {
            "loan_id": [f"LN-{i:06d}" for i in range(1, n_exposures + 1)],
            "client_id": [f"CL-{client:05d}" for client in rng.integers(1, max(2, n_exposures // 2), size=n_exposures)],
            "product_type": rng.choice(PRODUCT_TYPES, size=n_exposures),
            "sector": rng.choice(SECTORS, size=n_exposures),
            "country": rng.choice(COUNTRIES, size=n_exposures),
            "ead": ead,
            "effective_interest_rate": np.round(rng.uniform(0.015, 0.085, size=n_exposures), 4),
            "residual_maturity_months": maturity,
            "origination_rating": origination_rating,
            "current_rating": current_rating,
            "pd_12m": pd_12m,
            "pd_lifetime": pd_lifetime,
            "lgd": lgd,
            "days_past_due": days_past_due.astype(int),
            "default_flag": default_flag,
            "forbearance_flag": rng.random(n_exposures) < 0.07,
            "watchlist_flag": rng.random(n_exposures) < 0.10,
            "collateral_flag": collateral_flag,
            "ltv": np.round(ltv, 4),
        }
    )
    portfolio["initial_stage"] = "Stage 1"
    return portfolio


def generate_demo_portfolio(
    profile: str = "Balanced Portfolio",
    n_exposures: int = 1_000,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a synthetic portfolio shaped for a client demonstration profile.

    The profiles are pedagogical and only adjust fictional data distributions.
    They are not calibrated on real banking observations.
    """
    if profile not in DEMO_PORTFOLIO_PROFILES:
        raise ValueError(f"Unknown demo portfolio profile: {profile}")

    portfolio = generate_portfolio(n_exposures=n_exposures, seed=seed)
    rng = np.random.default_rng(seed + 10_000)

    if profile == "Balanced Portfolio":
        return portfolio
    if profile == "Low Risk Portfolio":
        return _apply_low_risk_profile(portfolio, rng)
    if profile == "Deteriorated Portfolio":
        return _apply_deteriorated_profile(portfolio, rng)
    if profile == "Data Quality Issues Portfolio":
        return _apply_data_quality_profile(portfolio, rng)
    if profile == "CRE Stress Portfolio":
        return _apply_cre_stress_profile(portfolio, rng)
    return portfolio


def _apply_low_risk_profile(portfolio: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    result = portfolio.copy()
    result["origination_rating"] = rng.choice([1, 2, 3, 4, 5], size=len(result), p=[0.18, 0.25, 0.28, 0.20, 0.09])
    result["current_rating"] = np.clip(result["origination_rating"] + rng.choice([-1, 0, 1], size=len(result), p=[0.15, 0.75, 0.10]), 1, 10)
    result["pd_12m"] = np.round(np.clip(result["pd_12m"] * 0.45, 0.0002, 0.08), 5)
    result["pd_lifetime"] = np.round(np.maximum(result["pd_12m"] * rng.uniform(1.4, 2.8, size=len(result)), result["pd_12m"]), 5)
    result["lgd"] = np.round(np.clip(result["lgd"] * 0.8, 0.10, 0.45), 4)
    result["days_past_due"] = rng.choice([0, 5, 15, 25], size=len(result), p=[0.78, 0.14, 0.06, 0.02])
    result["default_flag"] = False
    result["forbearance_flag"] = rng.random(len(result)) < 0.015
    result["watchlist_flag"] = rng.random(len(result)) < 0.025
    return result


def _apply_deteriorated_profile(portfolio: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    result = portfolio.copy()
    downgrade = rng.choice([0, 1, 2, 3, 4], size=len(result), p=[0.10, 0.22, 0.32, 0.24, 0.12])
    result["current_rating"] = np.clip(result["origination_rating"] + downgrade, 1, 10)
    result["pd_12m"] = np.round(np.clip(result["pd_12m"] * rng.uniform(1.35, 2.35, size=len(result)), 0.001, 0.65), 5)
    result["pd_lifetime"] = np.round(np.clip(result["pd_12m"] * rng.uniform(1.7, 4.5, size=len(result)), result["pd_12m"], 0.98), 5)
    result["lgd"] = np.round(np.clip(result["lgd"] * rng.uniform(1.05, 1.35, size=len(result)), 0.20, 0.85), 4)
    result["days_past_due"] = rng.choice([0, 15, 25, 30, 45, 60, 85, 90, 120], size=len(result), p=[0.34, 0.12, 0.08, 0.14, 0.10, 0.08, 0.04, 0.06, 0.04])
    result["default_flag"] = (result["days_past_due"] >= 90) | (rng.random(len(result)) < 0.05)
    result["forbearance_flag"] = rng.random(len(result)) < 0.16
    result["watchlist_flag"] = rng.random(len(result)) < 0.22
    return result


def _apply_data_quality_profile(portfolio: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    result = _apply_deteriorated_profile(portfolio, rng)
    n = len(result)
    missing_rating = rng.choice(result.index, size=max(1, int(n * 0.05)), replace=False)
    missing_pd = rng.choice(result.index, size=max(1, int(n * 0.04)), replace=False)
    missing_lgd = rng.choice(result.index, size=max(1, int(n * 0.03)), replace=False)
    invalid_ead = rng.choice(result.index, size=max(1, int(n * 0.02)), replace=False)
    invalid_dpd = rng.choice(result.index, size=max(1, int(n * 0.015)), replace=False)
    ltv_without_collateral = rng.choice(result.index, size=max(1, int(n * 0.04)), replace=False)

    result.loc[missing_rating, "current_rating"] = np.nan
    result.loc[missing_pd, ["pd_12m", "pd_lifetime"]] = np.nan
    result.loc[missing_lgd, "lgd"] = np.nan
    result.loc[invalid_ead, "ead"] = -result.loc[invalid_ead, "ead"].abs()
    result.loc[invalid_dpd, "days_past_due"] = -5
    result.loc[ltv_without_collateral, "collateral_flag"] = False
    result.loc[ltv_without_collateral, "ltv"] = rng.uniform(0.35, 1.4, size=len(ltv_without_collateral)).round(4)
    return result


def _apply_cre_stress_profile(portfolio: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    result = portfolio.copy()
    cre_share = rng.random(len(result)) < 0.45
    result.loc[cre_share, "sector"] = "Real estate"
    result.loc[cre_share, "product_type"] = rng.choice(["Corporate loan", "Mortgage"], size=int(cre_share.sum()), p=[0.65, 0.35])
    result.loc[cre_share, "ead"] = np.round(result.loc[cre_share, "ead"] * rng.uniform(1.25, 2.10, size=int(cre_share.sum())), 2)
    result.loc[cre_share, "current_rating"] = np.clip(result.loc[cre_share, "origination_rating"] + rng.choice([1, 2, 3], size=int(cre_share.sum()), p=[0.40, 0.40, 0.20]), 1, 10)
    result.loc[cre_share, "pd_12m"] = np.round(np.clip(result.loc[cre_share, "pd_12m"] * 1.65, 0.001, 0.60), 5)
    result.loc[cre_share, "pd_lifetime"] = np.round(np.clip(result.loc[cre_share, "pd_lifetime"] * 1.55, result.loc[cre_share, "pd_12m"], 0.98), 5)
    result.loc[cre_share, "lgd"] = np.round(np.clip(result.loc[cre_share, "lgd"] * 1.15, 0.20, 0.85), 4)
    result.loc[cre_share, "watchlist_flag"] = rng.random(int(cre_share.sum())) < 0.28
    result.loc[cre_share, "forbearance_flag"] = rng.random(int(cre_share.sum())) < 0.12
    return result
