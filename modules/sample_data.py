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
