import pandas as pd
import pytest

from modules.ecl_calculator import calculate_ecl, calculate_portfolio_metrics, summarize_ecl


def test_calculates_stage_1_ecl_with_12m_pd():
    portfolio = pd.DataFrame([{"loan_id": "LN-1", "stage": "Stage 1", "pd_12m": 0.02, "pd_lifetime": 0.10, "lgd": 0.4, "ead": 1_000}])
    result = calculate_ecl(portfolio)
    assert result.loc[0, "ecl"] == 8


def test_calculates_stage_2_ecl_with_lifetime_pd():
    portfolio = pd.DataFrame([{"loan_id": "LN-2", "stage": "Stage 2", "pd_12m": 0.02, "pd_lifetime": 0.10, "lgd": 0.4, "ead": 1_000}])
    result = calculate_ecl(portfolio)
    assert result.loc[0, "ecl"] == pytest.approx(40)


def test_calculates_stage_3_ecl_with_full_pd():
    portfolio = pd.DataFrame([{"loan_id": "LN-3", "stage": "Stage 3", "pd_12m": 0.02, "pd_lifetime": 0.10, "lgd": 0.4, "ead": 1_000}])
    result = calculate_ecl(portfolio)
    assert result.loc[0, "ecl"] == 400


def test_summarizes_ecl_metrics_by_stage_and_portfolio():
    portfolio = pd.DataFrame(
        [
            {"loan_id": "LN-1", "stage": "Stage 1", "pd_12m": 0.02, "pd_lifetime": 0.10, "lgd": 0.4, "ead": 1_000},
            {"loan_id": "LN-2", "stage": "Stage 2", "pd_12m": 0.02, "pd_lifetime": 0.10, "lgd": 0.4, "ead": 1_000},
        ]
    )
    result = calculate_ecl(portfolio)
    summary = summarize_ecl(result)
    metrics = calculate_portfolio_metrics(result)

    assert set(summary["stage"]) == {"Stage 1", "Stage 2"}
    assert metrics["total_ead"] == 2_000
    assert metrics["total_ecl"] == pytest.approx(48)
    assert metrics["coverage_ratio"] == pytest.approx(0.024)
