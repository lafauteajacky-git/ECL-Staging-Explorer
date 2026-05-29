"""Detailed audit trail helpers for ECL Staging Explorer V0.5."""

from __future__ import annotations

from datetime import datetime

import pandas as pd


APP_VERSION = "V0.5"


def generate_run_id(run_datetime: datetime | None = None) -> str:
    """Generate a readable unique run identifier."""
    timestamp = (run_datetime or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return f"RUN-{timestamp}"


def build_audit_trail(
    run_id: str,
    run_datetime: datetime,
    metrics: dict,
    scenario_metrics: dict,
    overlay_metrics: dict,
    ecl_by_stage: pd.DataFrame,
    scenario_parameters: pd.DataFrame,
    scenario_summary: pd.DataFrame,
    overlay_parameters: pd.DataFrame,
    overlay_summary: pd.DataFrame,
    data_quality_findings: pd.DataFrame,
    review_cases: pd.DataFrame,
    top_contributors: pd.DataFrame,
    staging_rules: pd.DataFrame,
    ecl_assumptions: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Build a detailed, Excel-friendly audit trail."""
    warnings = [
        "Demonstrateur pedagogique, non destine a un usage production.",
        "Donnees synthetiques uniquement.",
        "Scenarios macro appliques via multiplicateurs simples PD/LGD.",
        "Overlays appliques en pourcentage de l'ECL avant overlay.",
        "Pas de discounting des cash-flows dans le MVP.",
    ]
    run_summary = pd.DataFrame(
        [
            {"field": "run_id", "value": run_id},
            {"field": "run_datetime", "value": run_datetime.strftime("%Y-%m-%d %H:%M:%S")},
            {"field": "app_version", "value": APP_VERSION},
            {"field": "exposure_count", "value": metrics["exposure_count"]},
            {"field": "total_ead", "value": metrics["total_ead"]},
            {"field": "model_ecl_before_scenario", "value": metrics["total_ecl"]},
            {"field": "weighted_ecl_after_scenarios", "value": scenario_metrics["ecl_weighted"]},
            {"field": "ecl_before_overlay", "value": overlay_metrics["ecl_before_overlay"]},
            {"field": "total_overlay_amount", "value": overlay_metrics["total_overlay_amount"]},
            {"field": "final_ecl_after_overlay", "value": overlay_metrics["ecl_after_overlay"]},
            {"field": "data_quality_issue_count", "value": len(data_quality_findings)},
            {"field": "review_required_count", "value": len(review_cases)},
        ]
    )
    return {
        "run_summary": run_summary,
        "staging_rules": staging_rules,
        "ecl_assumptions": ecl_assumptions,
        "scenario_parameters": scenario_parameters,
        "scenario_results": scenario_summary,
        "overlay_parameters": overlay_parameters,
        "overlay_summary": overlay_summary,
        "data_quality_findings": data_quality_findings,
        "review_cases": review_cases,
        "top_contributors": top_contributors,
        "ecl_by_stage": ecl_by_stage,
        "methodological_warnings": pd.DataFrame({"warning": warnings}),
    }
