import pandas as pd

from modules.reporting import (
    aggregate_ecl_by_dimension,
    aggregate_ecl_by_stage,
    build_dashboard_metrics,
    build_review_flags,
)


def test_dashboard_metrics_include_stage_shares_and_review_count():
    portfolio = pd.DataFrame(
        [
            {"loan_id": "LN-1", "stage": "Stage 1", "ead": 100, "ecl": 1, "review_required": False},
            {"loan_id": "LN-2", "stage": "Stage 2", "ead": 200, "ecl": 20, "review_required": True},
            {"loan_id": "LN-3", "stage": "Stage 3", "ead": 300, "ecl": 120, "review_required": False},
        ]
    )
    findings = pd.DataFrame([{"loan_id": "LN-2", "check_code": "MISSING_PD", "description": "PD manquante"}])

    metrics = build_dashboard_metrics(portfolio, findings)

    assert metrics["total_ead"] == 600
    assert metrics["total_ecl"] == 141
    assert metrics["stage_2_share"] == 1 / 3
    assert metrics["stage_3_share"] == 1 / 3
    assert metrics["data_quality_issue_count"] == 1
    assert metrics["review_required_count"] == 1


def test_review_flags_detect_data_quality_and_threshold_cases():
    portfolio = pd.DataFrame(
        [
            {
                "loan_id": "LN-1",
                "days_past_due": 28,
                "ecl": 10,
            },
            {
                "loan_id": "LN-2",
                "days_past_due": 0,
                "ecl": 1000,
            },
        ]
    )
    findings = pd.DataFrame(
        [{"loan_id": "LN-1", "check_code": "MISSING_RATING", "description": "Rating manquant"}]
    )

    result = build_review_flags(portfolio, findings)

    assert bool(result.loc[0, "review_required"]) is True
    assert bool(result.loc[0, "rating_missing"]) is True
    assert bool(result.loc[0, "dpd_near_30"]) is True
    assert bool(result.loc[1, "high_ecl_contribution"]) is True


def test_aggregates_ecl_by_stage_product_and_sector():
    portfolio = pd.DataFrame(
        [
            {"loan_id": "LN-1", "stage": "Stage 1", "product_type": "SME", "sector": "Retail", "ead": 100, "ecl": 2},
            {"loan_id": "LN-2", "stage": "Stage 1", "product_type": "SME", "sector": "Retail", "ead": 200, "ecl": 3},
            {"loan_id": "LN-3", "stage": "Stage 2", "product_type": "Mortgage", "sector": "Real estate", "ead": 300, "ecl": 30},
        ]
    )

    by_stage = aggregate_ecl_by_stage(portfolio)
    by_product = aggregate_ecl_by_dimension(portfolio, "product_type")
    by_sector = aggregate_ecl_by_dimension(portfolio, "sector")

    assert by_stage.loc[by_stage["stage"].eq("Stage 1"), "ecl"].iloc[0] == 5
    assert by_stage.loc[by_stage["stage"].eq("Stage 2"), "coverage_ratio"].iloc[0] == 0.1
    assert by_product.loc[by_product["product_type"].eq("SME"), "ead"].iloc[0] == 300
    assert by_sector.loc[by_sector["sector"].eq("Retail"), "exposure_count"].iloc[0] == 2
