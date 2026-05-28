import pandas as pd
import pytest

from modules.scenario_engine import (
    DEFAULT_SCENARIOS,
    calculate_all_scenarios,
    calculate_scenario_ecl,
    calculate_weighted_ecl_summary,
    validate_scenario_weights,
)


def _portfolio():
    return pd.DataFrame(
        [
            {"loan_id": "LN-1", "stage": "Stage 1", "pd_12m": 0.02, "pd_lifetime": 0.10, "lgd": 0.40, "ead": 1_000},
            {"loan_id": "LN-2", "stage": "Stage 2", "pd_12m": 0.02, "pd_lifetime": 0.10, "lgd": 0.40, "ead": 1_000},
            {"loan_id": "LN-3", "stage": "Stage 3", "pd_12m": 0.02, "pd_lifetime": 0.10, "lgd": 0.40, "ead": 1_000},
        ]
    )


def test_default_weights_total_100_percent():
    assert validate_scenario_weights(DEFAULT_SCENARIOS) is True


def test_calculates_baseline_ecl():
    result = calculate_scenario_ecl(_portfolio(), "Baseline", 1.0, 1.0)
    assert result["scenario_ecl"].sum() == pytest.approx(448)


def test_calculates_downside_ecl():
    result = calculate_scenario_ecl(_portfolio(), "Downside", 1.35, 1.15)
    expected = (0.02 * 1.35 * 0.40 * 1.15 * 1_000) + (0.10 * 1.35 * 0.40 * 1.15 * 1_000) + (1.0 * 0.40 * 1.15 * 1_000)
    assert result["scenario_ecl"].sum() == pytest.approx(expected)


def test_calculates_upside_ecl():
    result = calculate_scenario_ecl(_portfolio(), "Upside", 0.85, 0.95)
    expected = (0.02 * 0.85 * 0.40 * 0.95 * 1_000) + (0.10 * 0.85 * 0.40 * 0.95 * 1_000) + (1.0 * 0.40 * 0.95 * 1_000)
    assert result["scenario_ecl"].sum() == pytest.approx(expected)


def test_calculates_weighted_ecl():
    _, summary = calculate_all_scenarios(_portfolio(), DEFAULT_SCENARIOS)
    metrics = calculate_weighted_ecl_summary(summary)
    expected = (
        summary.loc[summary["scenario"].eq("Baseline"), "ecl"].iloc[0] * 0.60
        + summary.loc[summary["scenario"].eq("Downside"), "ecl"].iloc[0] * 0.30
        + summary.loc[summary["scenario"].eq("Upside"), "ecl"].iloc[0] * 0.10
    )
    assert metrics["ecl_weighted"] == pytest.approx(expected)


def test_caps_pd_and_lgd_at_100_percent():
    portfolio = pd.DataFrame(
        [{"loan_id": "LN-1", "stage": "Stage 2", "pd_12m": 0.90, "pd_lifetime": 0.90, "lgd": 0.90, "ead": 1_000}]
    )
    result = calculate_scenario_ecl(portfolio, "Stress", 2.0, 2.0)

    assert result.loc[0, "pd_lifetime_adjusted"] == 1.0
    assert result.loc[0, "lgd_adjusted"] == 1.0
    assert result.loc[0, "scenario_ecl"] == 1_000
