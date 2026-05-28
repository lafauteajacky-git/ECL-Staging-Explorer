"""Macro scenario engine for the ECL Staging Explorer V0.3.

The module applies simple PD and LGD multipliers to the already staged
portfolio. It is intentionally pedagogical: no macro-econometric model is
implemented in this MVP demonstrator.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


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
    """Return True when scenario weights sum to 100%."""
    return abs(sum(values["weight"] for values in config.values()) - 1.0) <= tolerance


def calculate_scenario_ecl(staged_portfolio: pd.DataFrame, scenario_name: str, pd_multiplier: float, lgd_multiplier: float) -> pd.DataFrame:
    """Calculate ECL under one macro scenario with capped PD and LGD."""
    result = staged_portfolio.copy()
    result["scenario"] = scenario_name
    result["pd_12m_adjusted"] = np.minimum(result["pd_12m"] * pd_multiplier, 1.0)
    result["pd_lifetime_adjusted"] = np.minimum(result["pd_lifetime"] * pd_multiplier, 1.0)
    result["lgd_adjusted"] = np.minimum(result["lgd"] * lgd_multiplier, 1.0)

    result["pd_used_for_scenario"] = np.select(
        [result["stage"].eq("Stage 1"), result["stage"].eq("Stage 2"), result["stage"].eq("Stage 3")],
        [result["pd_12m_adjusted"], result["pd_lifetime_adjusted"], 1.0],
        default=np.nan,
    )
    result[f"ecl_{scenario_name.lower()}"] = result["pd_used_for_scenario"] * result["lgd_adjusted"] * result["ead"]
    result["scenario_ecl"] = result[f"ecl_{scenario_name.lower()}"]
    return result


def calculate_all_scenarios(staged_portfolio: pd.DataFrame, config: dict[str, dict[str, float]] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate scenario ECL line items and portfolio summaries."""
    scenario_config = config or DEFAULT_SCENARIOS
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
    summary["coverage_ratio"] = np.where(summary["ead"] > 0, summary["ecl"] / summary["ead"], 0.0)
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
        "downside_impact_pct": downside_impact / baseline if baseline else 0.0,
        "weighted_impact_amount": weighted_impact,
        "weighted_impact_pct": weighted_impact / baseline if baseline else 0.0,
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
    by_stage["downside_impact_pct"] = np.where(
        by_stage.get("Baseline", 0.0) > 0,
        by_stage["downside_impact_amount"] / by_stage.get("Baseline", 0.0),
        0.0,
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
