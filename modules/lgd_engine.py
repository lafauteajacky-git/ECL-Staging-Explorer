"""Pedagogical recovery-based LGD engine.

The engine estimates LGD from synthetic recovery assumptions. It is designed
for explanation and demonstration, not for production calibration.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from modules.calculation_utils import safe_divide
from modules.data_types import coerce_boolean_series


LGD_METHOD = "Discounted recovery cash flows with collateral and unsecured recovery"

LGD_SCENARIOS = {
    "Baseline": {
        "haircut_addon": 0.00,
        "delay_addon_months": 0,
        "cost_addon": 0.00,
        "unsecured_recovery_multiplier": 1.00,
    },
    "Downside": {
        "haircut_addon": 0.15,
        "delay_addon_months": 12,
        "cost_addon": 0.04,
        "unsecured_recovery_multiplier": 0.80,
    },
    "Upside": {
        "haircut_addon": -0.05,
        "delay_addon_months": -6,
        "cost_addon": -0.02,
        "unsecured_recovery_multiplier": 1.10,
    },
}


def _numeric_series(
    frame: pd.DataFrame,
    column: str,
    default: float = 0.0,
) -> pd.Series:
    """Return a numeric Series even when an optional column is absent."""
    values = (
        frame[column]
        if column in frame.columns
        else pd.Series(default, index=frame.index, dtype=float)
    )
    return pd.to_numeric(values, errors="coerce")


def add_synthetic_lgd_inputs(
    portfolio: pd.DataFrame,
    seed: int = 42,
) -> pd.DataFrame:
    """Add reproducible synthetic recovery assumptions and a baseline LGD."""
    result = portfolio.copy()
    rng = np.random.default_rng(seed)
    n = len(result)
    if not n:
        return result

    collateral = coerce_boolean_series(result["collateral_flag"])
    ead = pd.to_numeric(result["ead"], errors="coerce").clip(lower=0)
    ltv = pd.to_numeric(result["ltv"], errors="coerce")
    implied_collateral_value = safe_divide(ead, ltv)

    collateral_type = np.full(n, "Unsecured", dtype=object)
    mortgage = result["product_type"].eq("Mortgage") & collateral
    cre = result["sector"].eq("Real estate") & collateral & ~mortgage
    corporate_security = (
        result["product_type"].isin(["Corporate loan", "SME term loan"])
        & collateral
        & ~cre
    )
    other_security = collateral & ~(mortgage | cre | corporate_security)
    collateral_type[mortgage] = "Residential real estate"
    collateral_type[cre] = "Commercial real estate"
    collateral_type[corporate_security] = "Equipment / business assets"
    collateral_type[other_security] = "Financial / other collateral"
    result["collateral_type"] = collateral_type

    haircut_map = {
        "Residential real estate": 0.18,
        "Commercial real estate": 0.30,
        "Equipment / business assets": 0.40,
        "Financial / other collateral": 0.15,
        "Unsecured": 1.00,
    }
    result["collateral_haircut"] = (
        pd.Series(collateral_type, index=result.index)
        .map(haircut_map)
        .astype(float)
    )
    result["collateral_haircut"] = (
        result["collateral_haircut"] + rng.normal(0.0, 0.025, n)
    ).clip(0.05, 1.00).round(4)

    result["collateral_value"] = np.where(
        collateral,
        np.asarray(implied_collateral_value, dtype=float),
        0.0,
    )
    result["collateral_value"] = (
        pd.to_numeric(result["collateral_value"], errors="coerce")
        .fillna(0.0)
        .clip(lower=0.0)
        .round(2)
    )

    cost_by_type = {
        "Residential real estate": 0.07,
        "Commercial real estate": 0.10,
        "Equipment / business assets": 0.12,
        "Financial / other collateral": 0.05,
        "Unsecured": 0.04,
    }
    result["liquidation_cost_rate"] = (
        pd.Series(collateral_type, index=result.index).map(cost_by_type)
        + rng.normal(0.0, 0.01, n)
    ).clip(0.01, 0.25).round(4)

    product_recovery = {
        "Mortgage": 0.18,
        "SME term loan": 0.12,
        "Corporate loan": 0.15,
        "Consumer loan": 0.08,
        "Credit card": 0.05,
    }
    result["unsecured_recovery_rate"] = (
        result["product_type"].map(product_recovery).fillna(0.10)
        + rng.normal(0.0, 0.02, n)
    ).clip(0.01, 0.35).round(4)

    result["seniority"] = np.where(
        result["product_type"].isin(["Mortgage", "Corporate loan"]),
        "Senior secured",
        np.where(
            result["product_type"].eq("SME term loan"),
            "Senior unsecured",
            "Unsecured",
        ),
    )
    result["recovery_delay_months"] = np.select(
        [
            result["collateral_type"].eq("Commercial real estate"),
            result["collateral_type"].eq("Residential real estate"),
            result["collateral_type"].eq("Equipment / business assets"),
        ],
        [30, 24, 20],
        default=14,
    )
    result["recovery_delay_months"] = (
        pd.Series(result["recovery_delay_months"], index=result.index)
        + rng.integers(-3, 7, size=n)
    ).clip(6, 60)
    result["recovery_cost_amount"] = (
        ead.fillna(0.0) * rng.uniform(0.005, 0.025, size=n)
    ).round(2)
    result["lgd_method"] = LGD_METHOD

    calculated = calculate_lgd(result, scenario="Baseline", preserve_missing_lgd=False)
    result["lgd"] = calculated["lgd"]
    return result


def calculate_lgd(
    portfolio: pd.DataFrame,
    scenario: str = "Baseline",
    preserve_missing_lgd: bool = True,
) -> pd.DataFrame:
    """Calculate discounted recovery LGD for one scenario."""
    if scenario not in LGD_SCENARIOS:
        raise ValueError(f"Unknown LGD scenario: {scenario}")

    result = portfolio.copy()
    original_lgd = _numeric_series(result, "lgd", np.nan)
    assumptions = LGD_SCENARIOS[scenario]
    ead = _numeric_series(result, "ead", np.nan)
    positive_ead = ead.clip(lower=0.0)
    collateral_value = (
        _numeric_series(result, "collateral_value").fillna(0.0).clip(lower=0.0)
    )
    haircut = (
        _numeric_series(result, "collateral_haircut", 1.0)
        .fillna(1.0)
        .add(assumptions["haircut_addon"])
        .clip(0.0, 1.0)
    )
    liquidation_cost = (
        _numeric_series(result, "liquidation_cost_rate")
        .fillna(0.0)
        .add(assumptions["cost_addon"])
        .clip(0.0, 1.0)
    )
    unsecured_rate = (
        _numeric_series(result, "unsecured_recovery_rate")
        .fillna(0.0)
        .mul(assumptions["unsecured_recovery_multiplier"])
        .clip(0.0, 1.0)
    )
    seniority = result.get(
        "seniority",
        pd.Series("Senior unsecured", index=result.index),
    )
    seniority_multiplier = (
        seniority.astype(str)
        .map(
            {
                "Senior secured": 1.10,
                "Senior unsecured": 1.00,
                "Unsecured": 0.85,
                "Subordinated": 0.60,
            }
        )
        .fillna(1.00)
    )
    unsecured_rate = (unsecured_rate * seniority_multiplier).clip(0.0, 1.0)
    recovery_delay = (
        _numeric_series(result, "recovery_delay_months", 12)
        .fillna(12)
        .add(assumptions["delay_addon_months"])
        .clip(lower=0)
    )
    recovery_cost_amount = (
        _numeric_series(result, "recovery_cost_amount")
        .fillna(0.0)
        .clip(lower=0.0)
    )
    effective_rate = (
        _numeric_series(result, "effective_interest_rate")
        .fillna(0.0)
        .clip(0.0, 1.0)
    )

    stage = result.get("stage", pd.Series("Stage 1", index=result.index))
    stage_haircut_addon = np.select(
        [stage.eq("Stage 2"), stage.eq("Stage 3")],
        [0.03, 0.10],
        default=0.0,
    )
    stage_delay_addon = np.select(
        [stage.eq("Stage 2"), stage.eq("Stage 3")],
        [3, 12],
        default=0,
    )
    haircut = (haircut + stage_haircut_addon).clip(0.0, 1.0)
    recovery_delay = recovery_delay + stage_delay_addon
    unsecured_rate = unsecured_rate * np.select(
        [stage.eq("Stage 2"), stage.eq("Stage 3")],
        [0.95, 0.75],
        default=1.0,
    )

    gross_secured_recovery = (
        collateral_value * (1.0 - haircut) * (1.0 - liquidation_cost)
    ).clip(lower=0.0)
    secured_recovery = np.minimum(gross_secured_recovery, positive_ead)
    unsecured_exposure = (positive_ead - secured_recovery).clip(lower=0.0)
    unsecured_recovery = unsecured_exposure * unsecured_rate
    recovery_before_discount = (
        secured_recovery + unsecured_recovery - recovery_cost_amount
    ).clip(lower=0.0)
    discount_factor = np.power(
        1.0 + effective_rate,
        recovery_delay / 12.0,
    )
    discounted_recovery = safe_divide(recovery_before_discount, discount_factor)
    discounted_recovery = pd.Series(
        np.minimum(discounted_recovery, positive_ead),
        index=result.index,
    )
    lgd = (1.0 - safe_divide(discounted_recovery, positive_ead)).clip(0.0, 1.0)
    lgd = pd.Series(lgd, index=result.index)
    lgd.loc[ead.le(0) | ead.isna()] = np.nan
    if preserve_missing_lgd:
        lgd.loc[original_lgd.isna()] = np.nan

    result["lgd_input"] = original_lgd
    result["lgd_scenario"] = scenario
    result["lgd_haircut_adjusted"] = haircut
    result["lgd_recovery_delay_adjusted"] = recovery_delay
    result["lgd_seniority_multiplier"] = seniority_multiplier
    result["secured_recovery_amount"] = secured_recovery
    result["unsecured_recovery_amount"] = unsecured_recovery
    result["recovery_before_discount"] = recovery_before_discount
    result["discounted_recovery_amount"] = discounted_recovery
    result["lgd"] = lgd.round(6)
    result["lgd_method"] = LGD_METHOD
    return result


def summarize_lgd(portfolio: pd.DataFrame) -> dict[str, float | str]:
    """Build portfolio-level LGD and recovery indicators."""
    ead = pd.to_numeric(portfolio["ead"], errors="coerce").clip(lower=0).fillna(0.0)
    lgd = pd.to_numeric(portfolio["lgd"], errors="coerce")
    recovery = _numeric_series(
        portfolio,
        "discounted_recovery_amount",
    ).fillna(0.0)
    collateral = coerce_boolean_series(portfolio["collateral_flag"])
    stage_3 = portfolio.get("stage", pd.Series("", index=portfolio.index)).eq("Stage 3")

    def weighted_lgd(mask: pd.Series) -> float:
        valid = mask & lgd.notna() & ead.gt(0)
        return safe_divide(
            float((lgd.loc[valid] * ead.loc[valid]).sum()),
            float(ead.loc[valid].sum()),
        )

    return {
        "lgd_ead_weighted": weighted_lgd(pd.Series(True, index=portfolio.index)),
        "lgd_secured_ead_weighted": weighted_lgd(collateral),
        "lgd_unsecured_ead_weighted": weighted_lgd(~collateral),
        "lgd_stage3_ead_weighted": weighted_lgd(stage_3),
        "discounted_recovery_amount": float(recovery.sum()),
        "recovery_rate_ead_weighted": safe_divide(float(recovery.sum()), float(ead.sum())),
        "average_recovery_delay_months": float(
            _numeric_series(portfolio, "lgd_recovery_delay_adjusted").mean()
        ),
        "lgd_method": LGD_METHOD,
    }


def aggregate_lgd_by_dimension(
    portfolio: pd.DataFrame,
    dimension: str,
) -> pd.DataFrame:
    """Aggregate LGD and recoveries by a portfolio dimension."""
    if dimension not in portfolio:
        raise ValueError(f"Unknown LGD aggregation dimension: {dimension}")
    records = []
    for value, group in portfolio.groupby(dimension, dropna=False):
        ead = pd.to_numeric(group["ead"], errors="coerce").clip(lower=0).fillna(0.0)
        lgd = pd.to_numeric(group["lgd"], errors="coerce")
        valid = lgd.notna() & ead.gt(0)
        records.append(
            {
                dimension: value,
                "exposure_count": len(group),
                "ead": float(ead.sum()),
                "lgd": safe_divide(
                    float((lgd.loc[valid] * ead.loc[valid]).sum()),
                    float(ead.loc[valid].sum()),
                ),
                "discounted_recovery_amount": float(
                    _numeric_series(
                        group,
                        "discounted_recovery_amount",
                    ).fillna(0.0).sum()
                ),
            }
        )
    return pd.DataFrame(records).sort_values("ead", ascending=False).reset_index(drop=True)


def build_lgd_sensitivity(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Calculate portfolio LGD under baseline, downside and upside assumptions."""
    rows = []
    for scenario in LGD_SCENARIOS:
        scenario_result = calculate_lgd(
            portfolio,
            scenario=scenario,
            preserve_missing_lgd=True,
        )
        summary = summarize_lgd(scenario_result)
        rows.append(
            {
                "scenario": scenario,
                "lgd": summary["lgd_ead_weighted"],
                "discounted_recovery_amount": summary["discounted_recovery_amount"],
                **LGD_SCENARIOS[scenario],
            }
        )
    sensitivity = pd.DataFrame(rows)
    baseline = float(
        sensitivity.loc[sensitivity["scenario"].eq("Baseline"), "lgd"].iloc[0]
    )
    sensitivity["lgd_impact_vs_baseline"] = sensitivity["lgd"] - baseline
    return sensitivity


def build_lgd_waterfall(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Build a portfolio recovery waterfall for visual restitution."""
    ead = float(pd.to_numeric(portfolio["ead"], errors="coerce").clip(lower=0).sum())
    secured = float(
        _numeric_series(
            portfolio,
            "secured_recovery_amount",
        ).fillna(0.0).sum()
    )
    unsecured = float(
        _numeric_series(
            portfolio,
            "unsecured_recovery_amount",
        ).fillna(0.0).sum()
    )
    discounted = float(
        _numeric_series(
            portfolio,
            "discounted_recovery_amount",
        ).fillna(0.0).sum()
    )
    loss = max(ead - discounted, 0.0)
    return pd.DataFrame(
        [
            {"step": "EAD", "amount": ead, "measure": "absolute"},
            {"step": "Recouvrement garanti", "amount": -secured, "measure": "relative"},
            {"step": "Recouvrement non garanti", "amount": -unsecured, "measure": "relative"},
            {
                "step": "Effet actualisation et couts",
                "amount": secured + unsecured - discounted,
                "measure": "relative",
            },
            {"step": "Perte finale", "amount": loss, "measure": "total"},
        ]
    )
