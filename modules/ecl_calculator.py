"""Expected Credit Loss calculations for the ECL Staging Explorer MVP."""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_ecl(staged_portfolio: pd.DataFrame) -> pd.DataFrame:
    """Calculate ECL according to simplified Stage 1, Stage 2 and Stage 3 rules."""
    result = staged_portfolio.copy()
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
    result["ecl"] = result["pd_used_for_ecl"] * result["lgd_used_for_ecl"] * ead
    result["coverage_ratio"] = np.where(ead > 0, result["ecl"] / ead, 0.0)
    return result


def summarize_ecl(ecl_portfolio: pd.DataFrame) -> pd.DataFrame:
    """Aggregate exposure and ECL metrics by stage."""
    summary = (
        ecl_portfolio.groupby("stage", as_index=False)
        .agg(ead=("ead", "sum"), ecl=("ecl", "sum"), exposure_count=("loan_id", "count"))
        .sort_values("stage")
        .reset_index(drop=True)
    )
    summary["coverage_ratio"] = np.where(
        summary["ead"] > 0,
        summary["ecl"] / summary["ead"],
        0.0,
    )
    return summary


def calculate_portfolio_metrics(ecl_portfolio: pd.DataFrame) -> dict[str, float]:
    """Calculate portfolio-level ECL dashboard metrics."""
    total_ead = float(ecl_portfolio["ead"].sum())
    total_ecl = float(ecl_portfolio["ecl"].sum())
    return {
        "total_ead": total_ead,
        "total_ecl": total_ecl,
        "coverage_ratio": total_ecl / total_ead if total_ead else 0.0,
        "exposure_count": int(len(ecl_portfolio)),
    }
