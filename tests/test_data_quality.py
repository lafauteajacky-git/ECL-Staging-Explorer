import pandas as pd

from modules.data_quality import (
    build_quality_dashboard_metrics,
    build_quality_dimension_summary,
    calculate_quality_score,
    missing_required_columns,
    run_data_quality_checks,
    summarize_quality_findings,
)


def test_detects_core_quality_issues():
    portfolio = pd.DataFrame(
        [
            {
                "loan_id": "LN-1",
                "origination_rating": None,
                "current_rating": 4,
                "pd_12m": None,
                "pd_lifetime": 0.12,
                "lgd": None,
                "ead": -1,
                "residual_maturity_months": -3,
                "days_past_due": -1,
                "default_flag": False,
                "collateral_flag": False,
                "ltv": 0.8,
            },
            {
                "loan_id": "LN-2",
                "origination_rating": 3,
                "current_rating": 3,
                "pd_12m": 0.02,
                "pd_lifetime": 0.08,
                "lgd": 0.4,
                "ead": 1_000,
                "residual_maturity_months": 12,
                "days_past_due": 90,
                "default_flag": False,
                "collateral_flag": True,
                "ltv": 0.7,
            },
        ]
    )

    findings = run_data_quality_checks(portfolio)
    detected_codes = set(findings["check_code"])

    assert "MISSING_RATING" in detected_codes
    assert "MISSING_PD" in detected_codes
    assert "MISSING_LGD" in detected_codes
    assert "INVALID_EAD" in detected_codes
    assert "NEGATIVE_MATURITY" in detected_codes
    assert "NEGATIVE_DPD" in detected_codes
    assert "DEFAULT_DPD_INCONSISTENCY" in detected_codes
    assert "LTV_WITHOUT_COLLATERAL" in detected_codes


def test_summarizes_quality_findings():
    findings = pd.DataFrame(
        [
            {"loan_id": "LN-1", "check_code": "INVALID_EAD", "description": "EAD negative ou nulle"},
            {"loan_id": "LN-2", "check_code": "INVALID_EAD", "description": "EAD negative ou nulle"},
        ]
    )
    summary = summarize_quality_findings(findings)
    assert summary.loc[0, "issue_count"] == 2


def test_calculates_quality_score():
    portfolio = pd.DataFrame({"loan_id": ["LN-1", "LN-2"]})
    findings = pd.DataFrame(
        [
            {"loan_id": "LN-1", "check_code": "INVALID_EAD", "description": "EAD negative ou nulle"},
            {"loan_id": "LN-2", "check_code": "MISSING_PD", "description": "PD manquante"},
        ]
    )

    assert calculate_quality_score(portfolio, findings) == 87.5


def test_detects_missing_required_columns():
    portfolio = pd.DataFrame({"loan_id": ["LN-1"], "ead": [1_000]})
    missing = missing_required_columns(portfolio)

    assert "client_id" in missing
    assert "pd_12m" in missing
    assert "loan_id" not in missing


def test_builds_bcbs_inspired_dimension_summary():
    portfolio = pd.DataFrame(
        {
            "loan_id": ["LN-1", "LN-2"],
            "ead": [100, 200],
        }
    )
    findings = pd.DataFrame(
        [
            {"loan_id": "LN-1", "check_code": "MISSING_PD", "description": "PD manquante"},
            {
                "loan_id": "LN-2",
                "check_code": "DEFAULT_DPD_INCONSISTENCY",
                "description": "Defaut incoherent",
            },
        ]
    )

    summary = build_quality_dimension_summary(portfolio, findings)

    assert set(["Completude", "Validite", "Coherence"]).issubset(set(summary["dimension"]))
    assert "Fraicheur / ponctualite" in set(summary["dimension"])
    assert summary.loc[summary["dimension"].eq("Fraicheur / ponctualite"), "status"].iloc[0] == "Non evalue"


def test_builds_quality_dashboard_metrics_with_ead_materiality():
    portfolio = pd.DataFrame(
        {
            "loan_id": ["LN-1", "LN-2"],
            "ead": [100, 300],
        }
    )
    findings = pd.DataFrame(
        [
            {"loan_id": "LN-1", "check_code": "MISSING_PD", "description": "PD manquante"},
        ]
    )

    metrics = build_quality_dashboard_metrics(portfolio, findings)

    assert metrics["impacted_exposure_count"] == 1
    assert metrics["impacted_exposure_rate"] == 0.5
    assert metrics["critical_issue_count"] == 1
    assert metrics["impacted_ead"] == 100
    assert metrics["impacted_ead_rate"] == 0.25
