import pandas as pd

from modules.business_checks import (
    build_client_discussion_points,
    run_business_consistency_checks,
    summarize_business_consistency,
)


def test_business_checks_detect_stage_and_parameter_alerts():
    portfolio = pd.DataFrame(
        [
            {
                "loan_id": "LN-1",
                "stage": "Stage 1",
                "stage_reason": "No trigger",
                "default_flag": True,
                "days_past_due": 95,
                "forbearance_flag": False,
                "watchlist_flag": False,
                "origination_rating": 4,
                "current_rating": 4,
                "pd_12m": 0.02,
                "pd_lifetime": 0.03,
                "lgd": 0.4,
                "ead": 100,
                "ecl": 2,
            },
            {
                "loan_id": "LN-2",
                "stage": "Stage 2",
                "stage_reason": "Manual override",
                "default_flag": False,
                "days_past_due": 0,
                "forbearance_flag": False,
                "watchlist_flag": False,
                "origination_rating": 5,
                "current_rating": 4,
                "pd_12m": 0.05,
                "pd_lifetime": 0.04,
                "lgd": 1.2,
                "ead": 100,
                "ecl": 60,
            },
        ]
    )

    alerts = run_business_consistency_checks(portfolio)

    assert "STAGE1_DEFAULT_OR_90DPD" in set(alerts["check_code"])
    assert "LIFETIME_PD_BELOW_12M_PD" in set(alerts["check_code"])
    assert "INVALID_LGD_RANGE" in set(alerts["check_code"])
    assert "HIGH_ECL_TO_EAD" in set(alerts["check_code"])


def test_business_consistency_score_counts_alerts_and_critical_alerts():
    alerts = pd.DataFrame(
        [
            {"severity": "Critical", "check_code": "A"},
            {"severity": "Warning", "check_code": "B"},
        ]
    )

    summary = summarize_business_consistency(alerts, exposure_count=2, check_count=10)

    assert summary["business_checks_passed"] == 18
    assert summary["business_alert_count"] == 2
    assert summary["business_critical_alert_count"] == 1
    assert summary["business_consistency_score"] == 0.9


def test_client_discussion_points_are_profile_aware_and_fixed_length():
    points = build_client_discussion_points(
        "CRE Stress Portfolio",
        {"business_consistency_score": 0.97},
        {"coverage_ratio": 0.05},
        {"weighted_impact_pct": 0.02},
        {"overlay_variation_pct": 0.04, "top_overlay_contributor": "CRE Stress"},
    )

    assert len(points) == 5
    assert "immobilier commercial" in points[0]
