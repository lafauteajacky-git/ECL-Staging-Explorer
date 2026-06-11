"""Reporting helpers for exports and dashboard-ready summaries."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd

from modules.calculation_utils import safe_divide

from modules.demo_config import DEMO_DISCLAIMER_FR


OUTPUT_DIR = Path("outputs")
CRITICAL_DQ_CODES = {"MISSING_RATING", "MISSING_PD", "MISSING_LGD", "INVALID_EAD"}


STAGING_RULES = [
    {
        "rule": "Stage 1 -> Stage 2",
        "threshold": "SICR: DPD >= 30, rating downgrade >= 2, PD >= 2x origination, watchlist, forbearance or macro-sector signal",
        "description": "A significant increase in credit risk triggers Stage 2.",
    },
    {
        "rule": "Stage 2 -> Stage 3",
        "threshold": "Default / credit-impaired: DPD >= 90, default, UTP, probable bankruptcy or distressed restructuring",
        "description": "Any current default or credit-impaired event triggers Stage 3.",
    },
    {
        "rule": "Stage 3 -> Stage 2",
        "threshold": "No default + cure >= 3 months",
        "description": "The exposure leaves Stage 3 after the minimum cure period but remains in Stage 2 under residual prudence.",
    },
    {
        "rule": "Stage 3 -> Stage 1",
        "threshold": "No default + no SICR + normalized payments + cure >= 12 months + strong justification",
        "description": "Exceptional direct return to Stage 1; deliberately rare in the synthetic portfolio.",
    },
    {
        "rule": "Stage 2 -> Stage 1",
        "threshold": "No SICR + DPD < 30 + no sensitive watchlist/forbearance + normalized payments + probation >= 6 months",
        "description": "The exposure returns to Stage 1 only after risk normalization and completion of probation.",
    },
    {
        "rule": "Stage 3 maintained",
        "threshold": "Default remains, cure < 3 months or exit criteria are not fully evidenced",
        "description": "Stage 3 is maintained while credit impairment persists or the documented exit criteria are incomplete.",
    },
    {
        "rule": "Stage 2 maintained",
        "threshold": "SICR remains or probation < 6 months",
        "description": "Stage 2 is maintained until SICR disappears and probation is completed.",
    },
    {
        "rule": "Stage 1 maintained",
        "threshold": "No default and no SICR",
        "description": "Performing exposures without significant deterioration remain in Stage 1.",
    },
]


ECL_ASSUMPTIONS = [
    {"stage": "Stage 1", "pd_used": "12-month PD", "formula": "ECL = PD 12M x LGD x EAD"},
    {"stage": "Stage 2", "pd_used": "Lifetime PD", "formula": "ECL = PD lifetime x LGD x EAD"},
    {"stage": "Stage 3", "pd_used": "100% PD proxy", "formula": "ECL = 100% x LGD x EAD"},
]


def aggregate_ecl_by_stage(ecl_portfolio: pd.DataFrame) -> pd.DataFrame:
    """Aggregate exposure, ECL and coverage by IFRS 9 stage."""
    summary = (
        ecl_portfolio.groupby("stage", as_index=False)
        .agg(ead=("ead", "sum"), ecl=("ecl", "sum"), exposure_count=("loan_id", "count"))
        .sort_values("stage")
        .reset_index(drop=True)
    )
    summary["coverage_ratio"] = safe_divide(summary["ecl"], summary["ead"])
    return summary


def aggregate_ecl_by_dimension(ecl_portfolio: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Aggregate ECL by a portfolio dimension such as product or sector."""
    return (
        ecl_portfolio.groupby(dimension, as_index=False)
        .agg(ead=("ead", "sum"), ecl=("ecl", "sum"), exposure_count=("loan_id", "count"))
        .sort_values("ecl", ascending=False)
        .reset_index(drop=True)
    )


def build_dashboard_metrics(
    ecl_portfolio: pd.DataFrame,
    data_quality_findings: pd.DataFrame,
) -> dict[str, float]:
    """Calculate executive KPIs for the V0.2 dashboard."""
    total_ead = float(ecl_portfolio["ead"].sum())
    total_ecl = float(ecl_portfolio["ecl"].sum())
    exposure_count = int(len(ecl_portfolio))
    review_count = int(ecl_portfolio["review_required"].sum()) if "review_required" in ecl_portfolio else 0

    return {
        "total_ead": total_ead,
        "total_ecl": total_ecl,
        "coverage_ratio": safe_divide(total_ecl, total_ead),
        "exposure_count": exposure_count,
        "stage_2_share": float((ecl_portfolio["stage"] == "Stage 2").mean()) if exposure_count else 0.0,
        "stage_3_share": float((ecl_portfolio["stage"] == "Stage 3").mean()) if exposure_count else 0.0,
        "data_quality_issue_count": int(len(data_quality_findings)),
        "review_required_count": review_count,
    }


def build_review_flags(ecl_portfolio: pd.DataFrame, data_quality_findings: pd.DataFrame) -> pd.DataFrame:
    """Add simple review indicators for client-demo triage."""
    result = ecl_portfolio.copy()
    dq_by_loan = (
        data_quality_findings.groupby("loan_id")["check_code"].apply(lambda values: sorted(set(values))).to_dict()
        if not data_quality_findings.empty
        else {}
    )
    top_ecl_threshold = result["ecl"].quantile(0.99) if not result.empty else np.inf

    result["data_quality_status"] = result["loan_id"].map(lambda loan_id: "Issue" if loan_id in dq_by_loan else "OK")
    result["data_quality_issue_codes"] = result["loan_id"].map(lambda loan_id: ", ".join(dq_by_loan.get(loan_id, [])))
    result["critical_data_missing"] = result["loan_id"].map(
        lambda loan_id: bool(CRITICAL_DQ_CODES.intersection(dq_by_loan.get(loan_id, [])))
    )
    result["default_inconsistency"] = result["loan_id"].map(
        lambda loan_id: "DEFAULT_DPD_INCONSISTENCY" in dq_by_loan.get(loan_id, [])
    )
    result["rating_missing"] = result["loan_id"].map(lambda loan_id: "MISSING_RATING" in dq_by_loan.get(loan_id, []))
    result["dpd_near_30"] = result["days_past_due"].between(25, 29, inclusive="both")
    result["dpd_near_90"] = result["days_past_due"].between(85, 89, inclusive="both")
    result["high_ecl_contribution"] = result["ecl"] >= top_ecl_threshold
    review_columns = [
        "default_inconsistency",
        "critical_data_missing",
        "dpd_near_30",
        "dpd_near_90",
        "rating_missing",
        "high_ecl_contribution",
    ]
    result["review_required"] = result[review_columns].any(axis=1)
    result["review_reason"] = result.apply(_format_review_reason, axis=1)
    return result


def _format_review_reason(row: pd.Series) -> str:
    reasons = []
    if row["default_inconsistency"]:
        reasons.append("Default inconsistency")
    if row["critical_data_missing"]:
        reasons.append("Critical data issue")
    if row["dpd_near_30"]:
        reasons.append("DPD close to Stage 2 threshold")
    if row["dpd_near_90"]:
        reasons.append("DPD close to Stage 3 threshold")
    if row["rating_missing"]:
        reasons.append("Rating missing")
    if row["high_ecl_contribution"]:
        reasons.append("High ECL contribution")
    return "; ".join(reasons) if reasons else "No review trigger"


def build_migration_matrix(ecl_portfolio: pd.DataFrame) -> pd.DataFrame:
    """Build a previous-stage / recalculated-stage migration matrix."""
    source_column = "previous_stage" if "previous_stage" in ecl_portfolio else "initial_stage"
    source_label = "Previous stage" if source_column == "previous_stage" else "Initial stage"
    return pd.crosstab(
        ecl_portfolio[source_column],
        ecl_portfolio["stage"],
        rownames=[source_label],
        colnames=["Recalculated stage"],
        dropna=False,
    ).reset_index()


def build_top_ecl_contributors(ecl_portfolio: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Return the top ECL-contributing exposures."""
    columns = ["loan_id", "client_id", "product_type", "sector", "stage", "ead", "lgd", "pd_used_for_ecl", "ecl"]
    return ecl_portfolio.sort_values("ecl", ascending=False).head(n)[columns].reset_index(drop=True)


def build_management_insights(
    ecl_portfolio: pd.DataFrame,
    ecl_by_stage: pd.DataFrame,
    ecl_by_product: pd.DataFrame,
    data_quality_findings: pd.DataFrame,
    scenario_insights: list[str] | None = None,
    business_consistency_summary: dict[str, float] | None = None,
) -> list[str]:
    """Generate simple automatic management insights from the demo results."""
    insights = []
    total_ecl = ecl_portfolio["ecl"].sum()
    exposure_count = len(ecl_portfolio)

    if total_ecl > 0:
        stage_3_ecl = ecl_by_stage.loc[ecl_by_stage["stage"].eq("Stage 3"), "ecl"].sum()
        if stage_3_ecl / total_ecl >= 0.50:
            insights.append("La majorite de l'ECL est concentree sur le Stage 3.")

        if not ecl_by_product.empty:
            top_product = ecl_by_product.iloc[0]
            if top_product["ecl"] / total_ecl >= 0.30:
                insights.append(f"Le portefeuille {top_product['product_type']} contribue fortement a l'ECL totale.")

    if not data_quality_findings.empty:
        insights.append("Certains contrats presentent des anomalies de donnees susceptibles d'affecter le calcul.")

    stage_2_share = (ecl_portfolio["stage"] == "Stage 2").mean() if exposure_count else 0.0
    if stage_2_share >= 0.20:
        insights.append("Une part significative des expositions a migre vers le Stage 2.")

    review_share = ecl_portfolio["review_required"].mean() if "review_required" in ecl_portfolio and exposure_count else 0.0
    if review_share >= 0.05:
        insights.append("Un nombre significatif d'expositions necessite une revue metier ciblee.")

    if not insights:
        insights.append("Le portefeuille ne presente pas de concentration majeure selon les seuils de demonstration V0.2.")

    if scenario_insights:
        insights.extend(scenario_insights)
    if business_consistency_summary:
        score = business_consistency_summary.get("business_consistency_score", 1.0)
        critical_alerts = int(business_consistency_summary.get("business_critical_alert_count", 0))
        if critical_alerts:
            insights.append(f"{critical_alerts} alerte(s) critique(s) de coherence metier doivent etre revues avant usage decisionnel.")
        elif score < 0.98:
            insights.append(f"Le score de coherence metier ressort a {score:.1%}, avec des points de revue non critiques.")

    return insights


def build_audit_view(
    run_datetime: datetime,
    exposure_count: int,
    data_quality_issue_count: int,
    scenario_parameters: pd.DataFrame | None = None,
    scenario_results: pd.DataFrame | None = None,
    scenario_metrics: dict[str, float] | None = None,
    overlay_parameters: pd.DataFrame | None = None,
    overlay_summary: pd.DataFrame | None = None,
    overlay_metrics: dict[str, float | str] | None = None,
    overlay_adjusted_exposures: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Build simplified regulatory and audit tables for the Streamlit view and Excel export."""
    run_summary = pd.DataFrame(
        [
            {"item": "Run datetime", "value": run_datetime.strftime("%Y-%m-%d %H:%M:%S")},
            {"item": "Exposures processed", "value": str(exposure_count)},
            {"item": "Data quality issues detected", "value": str(data_quality_issue_count)},
            {"item": "Data source", "value": "Synthetic demo portfolio or user-loaded MVP schema file"},
        ]
    )
    audit_view = {
        "run_summary": run_summary,
        "staging_rules": pd.DataFrame(STAGING_RULES),
        "ecl_assumptions": pd.DataFrame(ECL_ASSUMPTIONS),
    }
    if scenario_parameters is not None:
        audit_view["macro_scenarios"] = scenario_parameters.copy()
    if scenario_results is not None:
        audit_view["scenario_results"] = scenario_results.copy()
    if scenario_metrics is not None:
        audit_view["scenario_metrics"] = pd.DataFrame(
            [{"metric": metric, "value": value} for metric, value in scenario_metrics.items()]
        )
    if overlay_parameters is not None:
        audit_view["management_overlays"] = overlay_parameters.copy()
    if overlay_summary is not None:
        audit_view["overlay_summary"] = overlay_summary.copy()
    if overlay_metrics is not None:
        audit_view["overlay_metrics"] = pd.DataFrame(
            [{"metric": metric, "value": value} for metric, value in overlay_metrics.items()]
        )
    if overlay_adjusted_exposures is not None:
        audit_view["overlay_adjusted_exposures"] = overlay_adjusted_exposures.copy()
    return audit_view


def build_dashboard_summary_table(metrics: dict[str, float], scenario_metrics: dict[str, float] | None = None) -> pd.DataFrame:
    """Convert dashboard metrics to a two-column export table."""
    labels = {
        "total_ead": "Total EAD",
        "total_ecl": "Total ECL",
        "coverage_ratio": "Global coverage ratio",
        "exposure_count": "Number of exposures",
        "stage_2_share": "Share of exposures in Stage 2",
        "stage_3_share": "Share of exposures in Stage 3",
        "data_quality_issue_count": "Data quality issues",
        "review_required_count": "Review required cases",
        "ecl_baseline": "Scenario ECL - Baseline",
        "ecl_downside": "Scenario ECL - Downside",
        "ecl_upside": "Scenario ECL - Upside",
        "ecl_weighted": "Weighted scenario ECL",
        "downside_impact_amount": "Downside impact vs baseline",
        "downside_impact_pct": "Downside impact vs baseline %",
        "weighted_impact_amount": "Weighted ECL impact vs baseline",
        "weighted_impact_pct": "Weighted ECL impact vs baseline %",
        "ecl_before_overlay": "ECL before overlay",
        "total_overlay_amount": "Total overlay amount",
        "ecl_after_overlay": "ECL after overlay",
        "overlay_variation_amount": "Overlay variation amount",
        "overlay_variation_pct": "Overlay variation %",
        "top_overlay_contributor": "Top overlay contributor",
        "business_checks_passed": "Business checks passed",
        "business_alert_count": "Business consistency alerts",
        "business_critical_alert_count": "Critical business consistency alerts",
        "business_consistency_score": "Business consistency score",
    }
    combined = metrics.copy()
    if scenario_metrics:
        combined.update(scenario_metrics)
    return pd.DataFrame([{"metric": labels.get(key, key), "value": value} for key, value in combined.items()])


def build_excel_export_bytes(
    portfolio: pd.DataFrame,
    data_quality_findings: pd.DataFrame,
    staging_results: pd.DataFrame,
    ecl_results: pd.DataFrame,
    dashboard_summary: pd.DataFrame,
    audit_view: dict[str, pd.DataFrame],
    macro_scenarios: pd.DataFrame | None = None,
    scenario_results: pd.DataFrame | None = None,
    management_overlays: pd.DataFrame | None = None,
    overlay_results: pd.DataFrame | None = None,
    detailed_audit_trail: dict[str, pd.DataFrame] | None = None,
    committee_summary: str | None = None,
    business_consistency: pd.DataFrame | None = None,
    demo_storyline: pd.DataFrame | None = None,
    client_discussion_points: pd.DataFrame | None = None,
    risk_parameters: pd.DataFrame | None = None,
    lifetime_pd_curve: pd.DataFrame | None = None,
    lgd_parameters: pd.DataFrame | None = None,
    lgd_sensitivity: pd.DataFrame | None = None,
) -> bytes:
    """Build the V0.3 Excel export in memory."""
    buffer = BytesIO()
    _write_excel_export(
        buffer,
        portfolio,
        data_quality_findings,
        staging_results,
        ecl_results,
        dashboard_summary,
        audit_view,
        macro_scenarios,
        scenario_results,
        management_overlays,
        overlay_results,
        detailed_audit_trail,
        committee_summary,
        business_consistency,
        demo_storyline,
        client_discussion_points,
        risk_parameters,
        lifetime_pd_curve,
        lgd_parameters,
        lgd_sensitivity,
    )
    return buffer.getvalue()


def export_results_to_excel(
    portfolio: pd.DataFrame,
    data_quality_findings: pd.DataFrame,
    staging_results: pd.DataFrame,
    ecl_results: pd.DataFrame,
    dashboard_summary: pd.DataFrame,
    audit_view: dict[str, pd.DataFrame],
    macro_scenarios: pd.DataFrame | None = None,
    scenario_results: pd.DataFrame | None = None,
    management_overlays: pd.DataFrame | None = None,
    overlay_results: pd.DataFrame | None = None,
    detailed_audit_trail: dict[str, pd.DataFrame] | None = None,
    committee_summary: str | None = None,
    business_consistency: pd.DataFrame | None = None,
    demo_storyline: pd.DataFrame | None = None,
    client_discussion_points: pd.DataFrame | None = None,
    file_name: str = "ecl_staging_explorer_results.xlsx",
    risk_parameters: pd.DataFrame | None = None,
    lifetime_pd_curve: pd.DataFrame | None = None,
    lgd_parameters: pd.DataFrame | None = None,
    lgd_sensitivity: pd.DataFrame | None = None,
) -> Path:
    """Export MVP results to the outputs directory and return the file path."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / file_name

    _write_excel_export(
        output_path,
        portfolio,
        data_quality_findings,
        staging_results,
        ecl_results,
        dashboard_summary,
        audit_view,
        macro_scenarios,
        scenario_results,
        management_overlays,
        overlay_results,
        detailed_audit_trail,
        committee_summary,
        business_consistency,
        demo_storyline,
        client_discussion_points,
        risk_parameters,
        lifetime_pd_curve,
        lgd_parameters,
        lgd_sensitivity,
    )

    return output_path


def _write_excel_export(
    target,
    portfolio: pd.DataFrame,
    data_quality_findings: pd.DataFrame,
    staging_results: pd.DataFrame,
    ecl_results: pd.DataFrame,
    dashboard_summary: pd.DataFrame,
    audit_view: dict[str, pd.DataFrame],
    macro_scenarios: pd.DataFrame | None = None,
    scenario_results: pd.DataFrame | None = None,
    management_overlays: pd.DataFrame | None = None,
    overlay_results: pd.DataFrame | None = None,
    detailed_audit_trail: dict[str, pd.DataFrame] | None = None,
    committee_summary: str | None = None,
    business_consistency: pd.DataFrame | None = None,
    demo_storyline: pd.DataFrame | None = None,
    client_discussion_points: pd.DataFrame | None = None,
    risk_parameters: pd.DataFrame | None = None,
    lifetime_pd_curve: pd.DataFrame | None = None,
    lgd_parameters: pd.DataFrame | None = None,
    lgd_sensitivity: pd.DataFrame | None = None,
) -> None:
    with pd.ExcelWriter(target, engine="openpyxl") as writer:
        pd.DataFrame({"disclaimer": [DEMO_DISCLAIMER_FR]}).to_excel(writer, sheet_name="Disclaimer", index=False)
        portfolio.to_excel(writer, sheet_name="Portfolio", index=False)
        data_quality_findings.to_excel(writer, sheet_name="Data Quality Issues", index=False)
        staging_results.to_excel(writer, sheet_name="Staging Results", index=False)
        ecl_results.to_excel(writer, sheet_name="ECL Results", index=False)
        dashboard_summary.to_excel(writer, sheet_name="Dashboard Summary", index=False)
        if macro_scenarios is not None:
            macro_scenarios.to_excel(writer, sheet_name="Macro Scenarios", index=False)
        if scenario_results is not None:
            scenario_results.to_excel(writer, sheet_name="Scenario Results", index=False)
        if management_overlays is not None:
            management_overlays.to_excel(writer, sheet_name="Management Overlays", index=False)
        if overlay_results is not None:
            overlay_results.to_excel(writer, sheet_name="Overlay Results", index=False)
        if business_consistency is not None:
            business_consistency.to_excel(writer, sheet_name="Business Consistency", index=False)
        if risk_parameters is not None:
            risk_parameters.to_excel(writer, sheet_name="Risk Parameters", index=False)
        if lifetime_pd_curve is not None:
            lifetime_pd_curve.to_excel(writer, sheet_name="Lifetime PD Curve", index=False)
        if lgd_parameters is not None:
            lgd_parameters.to_excel(writer, sheet_name="LGD Parameters", index=False)
        if lgd_sensitivity is not None:
            lgd_sensitivity.to_excel(writer, sheet_name="LGD Sensitivity", index=False)
        if demo_storyline is not None:
            demo_storyline.to_excel(writer, sheet_name="Demo Storyline", index=False)
        if client_discussion_points is not None:
            client_discussion_points.to_excel(writer, sheet_name="Client Discussion Points", index=False)
        if detailed_audit_trail is not None:
            _write_sectioned_sheet(writer, "Audit Trail", detailed_audit_trail)
        if committee_summary is not None:
            pd.DataFrame({"committee_summary": committee_summary.splitlines()}).to_excel(
                writer, sheet_name="Committee Summary", index=False
            )

        _write_sectioned_sheet(writer, "Audit View", audit_view)


def _write_sectioned_sheet(writer: pd.ExcelWriter, sheet_name: str, sections: dict[str, pd.DataFrame]) -> None:
    start_row = 0
    for title, table in sections.items():
        pd.DataFrame({"section": [title]}).to_excel(writer, sheet_name=sheet_name, startrow=start_row, index=False)
        table.to_excel(writer, sheet_name=sheet_name, startrow=start_row + 2, index=False)
        start_row += len(table) + 5
