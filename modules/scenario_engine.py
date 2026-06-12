"""Macro scenario engine for the ECL Staging Explorer V0.3.

The module applies simple PD and LGD multipliers to the already staged
portfolio. It is intentionally pedagogical: no macro-econometric model is
implemented in this MVP demonstrator.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from modules.calculation_utils import safe_divide
from modules.ecl_calculator import calculate_ecl
from modules.lgd_engine import LGD_SCENARIOS, calculate_lgd


DEFAULT_SCENARIOS = {
    "Baseline": {"weight": 0.60, "pd_multiplier": 1.00, "lgd_multiplier": 1.00},
    "Downside": {"weight": 0.30, "pd_multiplier": 1.35, "lgd_multiplier": 1.15},
    "Upside": {"weight": 0.10, "pd_multiplier": 0.85, "lgd_multiplier": 0.95},
}


def scenario_config_to_frame(config: dict[str, dict[str, float]]) -> pd.DataFrame:
    """Convert a scenario configuration dictionary to a table."""
    return pd.DataFrame(
        [
            {
                "scenario": scenario,
                "weight": values["weight"],
                "pd_multiplier": values["pd_multiplier"],
                "lgd_multiplier": values["lgd_multiplier"],
            }
            for scenario, values in config.items()
        ]
    )


def validate_scenario_weights(config: dict[str, dict[str, float]], tolerance: float = 1e-9) -> bool:
    """Return True when weights and multipliers form a valid configuration."""
    if not config:
        return False

    required_fields = {"weight", "pd_multiplier", "lgd_multiplier"}
    try:
        for values in config.values():
            if not required_fields.issubset(values):
                return False
            weight = float(values["weight"])
            pd_multiplier = float(values["pd_multiplier"])
            lgd_multiplier = float(values["lgd_multiplier"])
            if not all(np.isfinite(value) for value in (weight, pd_multiplier, lgd_multiplier)):
                return False
            if not 0.0 <= weight <= 1.0:
                return False
            if pd_multiplier < 0.0 or lgd_multiplier < 0.0:
                return False
    except (TypeError, ValueError):
        return False

    total_weight = sum(float(values["weight"]) for values in config.values())
    return abs(total_weight - 1.0) <= tolerance


def calculate_scenario_ecl(staged_portfolio: pd.DataFrame, scenario_name: str, pd_multiplier: float, lgd_multiplier: float) -> pd.DataFrame:
    """Calculate ECL under one macro scenario with capped PD and LGD."""
    result = staged_portfolio.copy()
    result["scenario"] = scenario_name
    if not np.isfinite(pd_multiplier) or not np.isfinite(lgd_multiplier):
        raise ValueError("Scenario multipliers must be finite.")
    if pd_multiplier < 0.0 or lgd_multiplier < 0.0:
        raise ValueError("Scenario multipliers cannot be negative.")

    recovery_columns = {
        "collateral_value",
        "collateral_haircut",
        "liquidation_cost_rate",
        "unsecured_recovery_rate",
        "recovery_delay_months",
    }
    if scenario_name in LGD_SCENARIOS and recovery_columns.issubset(result.columns):
        result = calculate_lgd(
            result,
            scenario=scenario_name,
            preserve_missing_lgd=True,
        )

    pd_12m = pd.to_numeric(result["pd_12m"], errors="coerce")
    pd_lifetime = pd.to_numeric(result["pd_lifetime"], errors="coerce")
    lgd = pd.to_numeric(result["lgd"], errors="coerce")
    result["pd_12m_adjusted"] = (pd_12m * pd_multiplier).clip(0.0, 1.0)
    result["pd_lifetime_adjusted"] = (pd_lifetime * pd_multiplier).clip(0.0, 1.0)
    result["lgd_adjusted"] = (lgd * lgd_multiplier).clip(0.0, 1.0)

    scenario_input = result.copy()
    scenario_input["pd_12m"] = result["pd_12m_adjusted"]
    scenario_input["pd_lifetime"] = result["pd_lifetime_adjusted"]
    scenario_input["lgd"] = result["lgd_adjusted"]
    scenario_calculation = calculate_ecl(scenario_input)
    result["pd_used_for_scenario"] = scenario_calculation["pd_used_for_ecl"]
    result["ead_used_for_scenario"] = scenario_calculation["ead_used_for_ecl"]
    result[f"ecl_{scenario_name.lower()}"] = scenario_calculation["ecl"]
    result["scenario_ecl"] = result[f"ecl_{scenario_name.lower()}"]
    return result


def calculate_all_scenarios(staged_portfolio: pd.DataFrame, config: dict[str, dict[str, float]] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate scenario ECL line items and portfolio summaries."""
    scenario_config = DEFAULT_SCENARIOS if config is None else config
    if not validate_scenario_weights(scenario_config):
        raise ValueError(
            "Scenario weights must total 100%, remain between 0% and 100%, "
            "and use non-negative finite PD/LGD multipliers."
        )
    scenario_frames = [
        calculate_scenario_ecl(
            staged_portfolio,
            scenario,
            values["pd_multiplier"],
            values["lgd_multiplier"],
        )
        for scenario, values in scenario_config.items()
    ]
    line_items = pd.concat(scenario_frames, ignore_index=True)
    summary = (
        line_items.groupby("scenario", as_index=False)
        .agg(ecl=("scenario_ecl", "sum"), ead=("ead", "sum"), exposure_count=("loan_id", "count"))
        .reset_index(drop=True)
    )
    weights = scenario_config_to_frame(scenario_config)[["scenario", "weight", "pd_multiplier", "lgd_multiplier"]]
    summary = summary.merge(weights, on="scenario", how="left")
    summary["weighted_ecl_contribution"] = summary["ecl"] * summary["weight"]
    summary["coverage_ratio"] = safe_divide(summary["ecl"], summary["ead"])
    return line_items, summary


def calculate_weighted_ecl_summary(scenario_summary: pd.DataFrame) -> dict[str, float]:
    """Calculate weighted ECL and scenario impacts."""
    ecl_by_scenario = dict(zip(scenario_summary["scenario"], scenario_summary["ecl"], strict=False))
    baseline = float(ecl_by_scenario.get("Baseline", 0.0))
    downside = float(ecl_by_scenario.get("Downside", 0.0))
    weighted = float(scenario_summary["weighted_ecl_contribution"].sum())

    downside_impact = downside - baseline
    weighted_impact = weighted - baseline
    return {
        "ecl_baseline": baseline,
        "ecl_downside": downside,
        "ecl_upside": float(ecl_by_scenario.get("Upside", 0.0)),
        "ecl_weighted": weighted,
        "downside_impact_amount": downside_impact,
        "downside_impact_pct": safe_divide(downside_impact, baseline),
        "weighted_impact_amount": weighted_impact,
        "weighted_impact_pct": safe_divide(weighted_impact, baseline),
    }


def calculate_downside_impact_by_stage(scenario_line_items: pd.DataFrame) -> pd.DataFrame:
    """Compare downside ECL against baseline ECL by stage."""
    by_stage = (
        scenario_line_items[scenario_line_items["scenario"].isin(["Baseline", "Downside"])]
        .groupby(["stage", "scenario"], as_index=False)["scenario_ecl"]
        .sum()
        .pivot(index="stage", columns="scenario", values="scenario_ecl")
        .fillna(0.0)
        .reset_index()
    )
    by_stage["downside_impact_amount"] = by_stage.get("Downside", 0.0) - by_stage.get("Baseline", 0.0)
    by_stage["downside_impact_pct"] = safe_divide(
        by_stage["downside_impact_amount"],
        by_stage.get("Baseline", pd.Series(0.0, index=by_stage.index)),
    )
    return by_stage


def build_scenario_insights(scenario_metrics: dict[str, float], downside_by_stage: pd.DataFrame, scenario_summary: pd.DataFrame) -> list[str]:
    """Generate simple management insights for macro scenario impacts."""
    insights = []
    downside_pct = scenario_metrics["downside_impact_pct"]
    weighted_pct = scenario_metrics["weighted_impact_pct"]
    insights.append(f"Le scenario downside augmente l'ECL de {downside_pct:.1%} par rapport au scenario baseline.")

    if not downside_by_stage.empty:
        sensitive_stage = downside_by_stage.sort_values("downside_impact_amount", ascending=False).iloc[0]["stage"]
        insights.append(f"Le {sensitive_stage} est le plus sensible au scenario macroeconomique.")

    downside_row = scenario_summary.loc[scenario_summary["scenario"].eq("Downside")]
    if not downside_row.empty:
        total_weighted = scenario_summary["weighted_ecl_contribution"].sum()
        downside_contribution = float(downside_row["weighted_ecl_contribution"].iloc[0])
        if total_weighted and downside_contribution / total_weighted >= 0.30:
            insights.append("La ponderation du scenario downside contribue significativement a l'ECL ponderee.")

    if abs(weighted_pct) >= 0.05:
        insights.append("Les parametres macroeconomiques ont un impact significatif sur le portefeuille.")
    else:
        insights.append("Les parametres macroeconomiques ont un impact limite sur le portefeuille.")
    return insights
