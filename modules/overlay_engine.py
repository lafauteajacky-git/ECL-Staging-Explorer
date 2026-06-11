"""Management overlay engine for the ECL Staging Explorer V0.4.

Overlays are applied as simple percentage uplifts on model ECL. When several
overlays apply to the same exposure, their monetary impacts are added on the
same row. The engine never duplicates exposure rows.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


PREDEFINED_OVERLAYS = [
    {
        "name": "Commercial Real Estate Stress",
        "overlay_type": "sector",
        "scope": "Sector contains Real estate",
        "rate": 0.15,
        "justification": "Prudence on commercial real estate exposures under uncertain valuation conditions.",
    },
    {
        "name": "SME Energy Sensitivity",
        "overlay_type": "product_sector",
        "scope": "Product contains SME and sector is Energy",
        "rate": 0.20,
        "justification": "Expert adjustment for SME energy sensitivity to input cost volatility.",
    },
    {
        "name": "Data Quality Uncertainty",
        "overlay_type": "data_quality",
        "scope": "Critical data quality issue",
        "rate": 0.10,
        "justification": "Prudence where critical missing or invalid data may affect ECL reliability.",
    },
    {
        "name": "Stage 2 Prudence Overlay",
        "overlay_type": "stage",
        "scope": "Stage 2",
        "rate": 0.05,
        "justification": "Additional prudence on exposures with significant increase in credit risk.",
    },
    {
        "name": "Stage 3 Recovery Risk",
        "overlay_type": "stage",
        "scope": "Stage 3",
        "rate": 0.10,
        "justification": "Recovery uncertainty adjustment on defaulted exposures.",
    },
]


def overlay_config_to_frame(overlays: list[dict]) -> pd.DataFrame:
    """Convert overlay definitions to a display/export table."""
    return pd.DataFrame(overlays, columns=["name", "overlay_type", "scope", "rate", "justification"])


def apply_overlays(ecl_portfolio: pd.DataFrame, enabled_overlay_names: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply enabled overlays and return row-level results plus overlay summary.

    Multiple overlays may apply to one exposure. In that case the overlay
    amounts are calculated independently on pre-overlay ECL and summed into one
    total overlay amount. Exposure rows are not duplicated.
    """
    enabled_names = (
        [overlay["name"] for overlay in PREDEFINED_OVERLAYS]
        if enabled_overlay_names is None
        else enabled_overlay_names
    )
    enabled = set(enabled_names)
    active_overlays = [overlay for overlay in PREDEFINED_OVERLAYS if overlay["name"] in enabled]
    result = ecl_portfolio.copy()
    result["ecl_before_overlay"] = result["ecl"]
    result["overlay_amount"] = 0.0
    result["overlay_names"] = ""
    result["overlay_types"] = ""
    result["overlay_justifications"] = ""

    overlay_rows = []
    for overlay in active_overlays:
        mask = _overlay_mask(result, overlay)
        amount = np.where(mask, result["ecl_before_overlay"] * overlay["rate"], 0.0)
        amount_series = pd.Series(amount, index=result.index)
        result["overlay_amount"] += amount_series
        _append_overlay_text(result, mask, "overlay_names", overlay["name"])
        _append_overlay_text(result, mask, "overlay_types", overlay["overlay_type"])
        _append_overlay_text(result, mask, "overlay_justifications", overlay["justification"])

        impacted = result.loc[mask]
        overlay_amount = float(amount_series.loc[mask].sum())
        overlay_rows.append(
            {
                "overlay_name": overlay["name"],
                "overlay_type": overlay["overlay_type"],
                "scope": overlay["scope"],
                "rate": overlay["rate"],
                "impacted_exposures": int(mask.sum()),
                "impacted_ead": float(impacted["ead"].sum()),
                "ecl_before_overlay": float(impacted["ecl_before_overlay"].sum()),
                "overlay_amount": overlay_amount,
                "ecl_after_overlay": float(impacted["ecl_before_overlay"].sum() + overlay_amount),
                "justification": overlay["justification"],
            }
        )

    result["ecl_after_overlay"] = result["ecl_before_overlay"] + result["overlay_amount"]
    result["overlay_applied"] = result["overlay_amount"] > 0
    result["overlay_names"] = result["overlay_names"].replace("", "None")
    result["overlay_types"] = result["overlay_types"].replace("", "None")
    result["overlay_justifications"] = result["overlay_justifications"].replace("", "None")
    summary = pd.DataFrame(
        overlay_rows,
        columns=[
            "overlay_name",
            "overlay_type",
            "scope",
            "rate",
            "impacted_exposures",
            "impacted_ead",
            "ecl_before_overlay",
            "overlay_amount",
            "ecl_after_overlay",
            "justification",
        ],
    )
    return result, summary


def _overlay_mask(portfolio: pd.DataFrame, overlay: dict) -> pd.Series:
    if overlay["name"] == "Commercial Real Estate Stress":
        return portfolio["sector"].astype(str).str.contains("Real estate", case=False, na=False)
    if overlay["name"] == "SME Energy Sensitivity":
        product_match = portfolio["product_type"].astype(str).str.contains("SME", case=False, na=False)
        sector_match = portfolio["sector"].astype(str).str.contains("Energy", case=False, na=False)
        return product_match & sector_match
    if overlay["name"] == "Data Quality Uncertainty":
        if "critical_data_missing" in portfolio:
            return portfolio["critical_data_missing"].fillna(False)
        return portfolio["data_quality_status"].eq("Issue") if "data_quality_status" in portfolio else pd.Series(False, index=portfolio.index)
    if overlay["name"] == "Stage 2 Prudence Overlay":
        return portfolio["stage"].eq("Stage 2")
    if overlay["name"] == "Stage 3 Recovery Risk":
        return portfolio["stage"].eq("Stage 3")
    if overlay.get("overlay_type") == "expert_global":
        return pd.Series(True, index=portfolio.index)
    return pd.Series(False, index=portfolio.index)


def _append_overlay_text(result: pd.DataFrame, mask: pd.Series, column: str, value: str) -> None:
    existing = result.loc[mask, column]
    result.loc[mask, column] = np.where(existing.eq(""), value, existing + "; " + value)


def build_overlay_metrics(overlay_results: pd.DataFrame, overlay_summary: pd.DataFrame) -> dict[str, float | str]:
    """Calculate executive overlay KPIs."""
    ecl_before = float(overlay_results["ecl_before_overlay"].sum())
    overlay_amount = float(overlay_results["overlay_amount"].sum())
    ecl_after = float(overlay_results["ecl_after_overlay"].sum())
    top_overlay = "None"
    if not overlay_summary.empty and overlay_summary["overlay_amount"].sum() > 0:
        top_overlay = overlay_summary.sort_values("overlay_amount", ascending=False).iloc[0]["overlay_name"]
    return {
        "ecl_before_overlay": ecl_before,
        "total_overlay_amount": overlay_amount,
        "ecl_after_overlay": ecl_after,
        "overlay_variation_amount": overlay_amount,
        "overlay_variation_pct": overlay_amount / ecl_before if ecl_before else 0.0,
        "top_overlay_contributor": top_overlay,
    }


def build_overlay_waterfall(overlay_metrics: dict[str, float | str], overlay_summary: pd.DataFrame) -> pd.DataFrame:
    """Build a simple waterfall-ready table."""
    rows = [{"step": "ECL before overlay", "amount": overlay_metrics["ecl_before_overlay"], "measure": "absolute"}]
    for _, row in overlay_summary.iterrows():
        if row["overlay_amount"] != 0:
            rows.append({"step": row["overlay_name"], "amount": row["overlay_amount"], "measure": "relative"})
    rows.append({"step": "ECL after overlay", "amount": overlay_metrics["ecl_after_overlay"], "measure": "total"})
    return pd.DataFrame(rows)


def build_overlay_insights(overlay_results: pd.DataFrame, overlay_summary: pd.DataFrame, overlay_metrics: dict[str, float | str]) -> list[str]:
    """Generate automatic management insights for overlays."""
    insights = []
    insights.append(f"Les overlays augmentent l'ECL totale de {overlay_metrics['overlay_variation_pct']:.1%}.")
    if overlay_metrics["top_overlay_contributor"] != "None":
        top = overlay_summary.sort_values("overlay_amount", ascending=False).iloc[0]
        insights.append(f"L'overlay le plus significatif est {top['overlay_name']}, avec un impact de {top['overlay_amount']:,.0f} EUR.")

    stage_overlay = overlay_results.groupby("stage", as_index=False)["overlay_amount"].sum()
    if not stage_overlay.empty and stage_overlay["overlay_amount"].sum() > 0:
        top_stage = stage_overlay.sort_values("overlay_amount", ascending=False).iloc[0]
        if top_stage["stage"] == "Stage 3" and top_stage["overlay_amount"] / stage_overlay["overlay_amount"].sum() >= 0.50:
            insights.append("Les expositions Stage 3 concentrent la majorite des overlays.")

    if overlay_metrics["total_overlay_amount"] > 0:
        insights.append("Les ajustements manageriaux refletent une approche prudente sur les segments les plus sensibles.")
    return insights
