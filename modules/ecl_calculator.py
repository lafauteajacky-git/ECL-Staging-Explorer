"""Expected Credit Loss calculations for the ECL Staging Explorer MVP."""

from __future__ import annotations

import numpy as np
import pandas as pd

from modules.calculation_utils import safe_divide
from modules.ead_engine import (
    build_ead_term_structure,
    calculate_ead,
    has_calculated_ead,
)


def calculate_ecl(staged_portfolio: pd.DataFrame) -> pd.DataFrame:
    """Calculate ECL with dynamic EAD when contractual inputs are available."""
    result = staged_portfolio.copy()
    dynamic_ead_available = {
        "undrawn_commitment",
        "ccf_base",
        "amortisation_type",
    }.issubset(result.columns)
    if dynamic_ead_available and not has_calculated_ead(result):
        result = calculate_ead(result)

    pd_12m = pd.to_numeric(result["pd_12m"], errors="coerce").clip(0.0, 1.0)
    pd_lifetime = pd.to_numeric(result["pd_lifetime"], errors="coerce").clip(0.0, 1.0)
    lgd = pd.to_numeric(result["lgd"], errors="coerce").clip(0.0, 1.0)
    ead = pd.to_numeric(result["ead"], errors="coerce")
    pd_for_ecl = np.select(
        [result["stage"].eq("Stage 1"), result["stage"].eq("Stage 2"), result["stage"].eq("Stage 3")],
        [pd_12m, pd_lifetime, 1.0],
        default=np.nan,
    )

    result["pd_used_for_ecl"] = pd_for_ecl
    result["lgd_used_for_ecl"] = lgd
    result["ead_used_for_ecl"] = ead
    result["ecl_method"] = "Simplified stage formula"

    if dynamic_ead_available:
        result["ead_used_for_ecl"] = np.select(
            [
                result["stage"].eq("Stage 1"),
                result["stage"].eq("Stage 3"),
            ],
            [
                pd.to_numeric(result["ead_12m"], errors="coerce"),
                pd.to_numeric(result["ead_at_default"], errors="coerce"),
            ],
            default=ead,
        )

    result["ecl"] = (
        result["pd_used_for_ecl"]
        * result["lgd_used_for_ecl"]
        * result["ead_used_for_ecl"]
    )

    if dynamic_ead_available and result["stage"].eq("Stage 2").any():
        lifetime_ecl, lifetime_ead = _calculate_stage2_lifetime_ecl(result)
        stage_2 = result["stage"].eq("Stage 2")
        result.loc[stage_2, "ecl"] = result.loc[stage_2, "loan_id"].map(
            lifetime_ecl
        )
        result.loc[stage_2, "ead_used_for_ecl"] = result.loc[
            stage_2,
            "loan_id",
        ].map(lifetime_ead)
        result.loc[stage_2, "ecl_method"] = (
            "Marginal lifetime PD x projected EAD x LGD x discount factor"
        )
        result.loc[result["stage"].eq("Stage 1"), "ecl_method"] = (
            "12-month PD x average 12-month EAD x LGD"
        )
        result.loc[result["stage"].eq("Stage 3"), "ecl_method"] = (
            "100% PD x current EAD including CCF x LGD"
        )

    result["coverage_ratio"] = safe_divide(result["ecl"], ead)
    return result


def _calculate_stage2_lifetime_ecl(
    portfolio: pd.DataFrame,
) -> tuple[dict[str, float], dict[str, float]]:
    """Calculate discounted Stage 2 ECL over annual projected EAD periods."""
    stage_2_portfolio = portfolio.loc[portfolio["stage"].eq("Stage 2")].copy()
    term = build_ead_term_structure(stage_2_portfolio)
    if term.empty:
        return {}, {}

    parameters = stage_2_portfolio.set_index("loan_id")[
        ["pd_12m", "lgd", "effective_interest_rate"]
    ]
    term = term.join(parameters, on="loan_id")
    pd_12m = pd.to_numeric(term["pd_12m"], errors="coerce").clip(0, 1)
    horizon_years = pd.to_numeric(term["horizon_months"], errors="coerce") / 12.0
    previous_years = np.maximum(
        pd.to_numeric(term["year"], errors="coerce") - 1,
        0,
    )
    cumulative_pd = 1.0 - np.power(1.0 - pd_12m, horizon_years)
    previous_pd = 1.0 - np.power(1.0 - pd_12m, previous_years)
    term["marginal_pd"] = (cumulative_pd - previous_pd).clip(lower=0)
    term["discount_factor"] = np.power(
        1.0
        + pd.to_numeric(
            term["effective_interest_rate"],
            errors="coerce",
        ).fillna(0).clip(0, 1),
        -horizon_years,
    )
    term["period_ecl"] = (
        term["marginal_pd"]
        * pd.to_numeric(term["lgd"], errors="coerce").clip(0, 1)
        * pd.to_numeric(term["ead_projected"], errors="coerce").clip(lower=0)
        * term["discount_factor"]
    )
    ecl_by_loan = term.groupby("loan_id")["period_ecl"].sum().to_dict()
    marginal_weight = term.groupby("loan_id")["marginal_pd"].sum()
    weighted_ead = (
        (term["marginal_pd"] * term["ead_projected"])
        .groupby(term["loan_id"])
        .sum()
    )
    ead_by_loan = safe_divide(weighted_ead, marginal_weight)
    return ecl_by_loan, ead_by_loan.to_dict()


def summarize_ecl(ecl_portfolio: pd.DataFrame) -> pd.DataFrame:
    """Aggregate exposure and ECL metrics by stage."""
    summary = (
        ecl_portfolio.groupby("stage", as_index=False)
        .agg(ead=("ead", "sum"), ecl=("ecl", "sum"), exposure_count=("loan_id", "count"))
        .sort_values("stage")
        .reset_index(drop=True)
    )
    summary["coverage_ratio"] = safe_divide(summary["ecl"], summary["ead"])
    return summary


def calculate_portfolio_metrics(ecl_portfolio: pd.DataFrame) -> dict[str, float]:
    """Calculate portfolio-level ECL dashboard metrics."""
    total_ead = float(ecl_portfolio["ead"].sum())
    total_ecl = float(ecl_portfolio["ecl"].sum())
    return {
        "total_ead": total_ead,
        "total_ecl": total_ecl,
        "coverage_ratio": safe_divide(total_ecl, total_ead),
        "exposure_count": int(len(ecl_portfolio)),
    }
