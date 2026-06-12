import pandas as pd
import pytest

import modules.ecl_calculator as ecl_calculator
from modules.ead_engine import calculate_ead
from modules.ecl_calculator import calculate_ecl, calculate_portfolio_metrics, summarize_ecl
from modules.lgd_engine import calculate_lgd


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


def test_ecl_floors_negative_pd_and_lgd_and_handles_zero_ead():
    portfolio = pd.DataFrame(
        [
            {
                "loan_id": "LN-1",
                "stage": "Stage 2",
                "pd_12m": -0.10,
                "pd_lifetime": -0.20,
                "lgd": -0.40,
                "ead": 0,
            }
        ]
    )

    result = calculate_ecl(portfolio)
    summary = summarize_ecl(result)

    assert result.loc[0, "ecl"] == 0.0
    assert result.loc[0, "coverage_ratio"] == 0.0
    assert summary.loc[0, "coverage_ratio"] == 0.0


def test_stage2_uses_projected_amortising_ead_and_marginal_pd():
    portfolio = pd.DataFrame(
        [
            {
                "loan_id": "LN-2",
                "stage": "Stage 2",
                "product_type": "SME term loan",
                "current_rating": 6,
                "pd_12m": 0.10,
                "pd_lifetime": 1 - (1 - 0.10) ** 3,
                "lgd": 0.40,
                "ead": 1_000.0,
                "effective_interest_rate": 0.05,
                "residual_maturity_months": 36,
                "undrawn_commitment": 200.0,
                "ccf_base": 0.20,
                "amortisation_type": "Amortising",
            }
        ]
    )

    result = calculate_ecl(portfolio)
    static_ecl = portfolio.loc[0, "pd_lifetime"] * 0.40 * 1_000

    assert result.loc[0, "ead_at_default"] > 1_000
    assert result.loc[0, "ecl"] < static_ecl
    assert "projected EAD" in result.loc[0, "ecl_method"]


def test_dynamic_ecl_reuses_precalculated_ead(monkeypatch):
    portfolio = calculate_ead(
        pd.DataFrame(
            [
                {
                    "loan_id": "LN-1",
                    "stage": "Stage 1",
                    "product_type": "Credit card",
                    "current_rating": 4,
                    "pd_12m": 0.02,
                    "pd_lifetime": 0.08,
                    "lgd": 0.40,
                    "ead": 1_000.0,
                    "effective_interest_rate": 0.05,
                    "residual_maturity_months": 24,
                    "undrawn_commitment": 500.0,
                    "ccf_base": 0.75,
                    "amortisation_type": "Revolving",
                }
            ]
        )
    )

    def unexpected_recalculation(_portfolio):
        raise AssertionError("EAD should be reused when calculated columns exist")

    monkeypatch.setattr(ecl_calculator, "calculate_ead", unexpected_recalculation)

    result = calculate_ecl(portfolio)

    assert result.loc[0, "ecl"] > 0


def test_lifetime_projection_is_limited_to_stage2(monkeypatch):
    portfolio = pd.DataFrame(
        [
            {
                "loan_id": "LN-1",
                "stage": "Stage 1",
                "product_type": "SME term loan",
                "current_rating": 4,
                "pd_12m": 0.02,
                "pd_lifetime": 0.08,
                "lgd": 0.40,
                "ead": 1_000.0,
                "effective_interest_rate": 0.05,
                "residual_maturity_months": 36,
                "undrawn_commitment": 100.0,
                "ccf_base": 0.20,
                "amortisation_type": "Amortising",
            },
            {
                "loan_id": "LN-2",
                "stage": "Stage 2",
                "product_type": "SME term loan",
                "current_rating": 6,
                "pd_12m": 0.08,
                "pd_lifetime": 0.22,
                "lgd": 0.45,
                "ead": 2_000.0,
                "effective_interest_rate": 0.05,
                "residual_maturity_months": 36,
                "undrawn_commitment": 200.0,
                "ccf_base": 0.20,
                "amortisation_type": "Amortising",
            },
        ]
    )
    original_builder = ecl_calculator.build_ead_term_structure
    projected_stages = []

    def capture_projection(projected_portfolio):
        projected_stages.extend(projected_portfolio["stage"].unique().tolist())
        return original_builder(projected_portfolio)

    monkeypatch.setattr(
        ecl_calculator,
        "build_ead_term_structure",
        capture_projection,
    )

    calculate_ecl(portfolio)

    assert projected_stages == ["Stage 2"]


def test_dynamic_stage1_ecl_reconciles_pd_lgd_and_average_12m_ead():
    portfolio = pd.DataFrame(
        [
            {
                "loan_id": "LN-S1",
                "stage": "Stage 1",
                "product_type": "SME term loan",
                "current_rating": 4,
                "pd_12m": 0.10,
                "pd_lifetime": 0.19,
                "lgd": 0.40,
                "ead": 1_000.0,
                "effective_interest_rate": 0.05,
                "residual_maturity_months": 24,
                "undrawn_commitment": 200.0,
                "ccf_base": 0.20,
                "amortisation_type": "Amortising",
            }
        ]
    )

    result = calculate_ecl(portfolio)

    adjusted_ccf = 0.20 + 0.05  # Utilisation above 80%.
    current_ead = 1_000.0 + 200.0 * adjusted_ccf
    endpoint_12m_ead = 500.0 + 100.0 * adjusted_ccf
    expected_ead = (current_ead + endpoint_12m_ead) / 2
    expected_ecl = 0.10 * 0.40 * expected_ead

    assert result.loc[0, "ead_used_for_ecl"] == pytest.approx(expected_ead)
    assert result.loc[0, "lgd_used_for_ecl"] == pytest.approx(0.40)
    assert result.loc[0, "pd_used_for_ecl"] == pytest.approx(0.10)
    assert result.loc[0, "ecl"] == pytest.approx(expected_ecl)


def test_dynamic_stage2_ecl_reconciles_to_lifetime_pd_and_projected_ead():
    portfolio = pd.DataFrame(
        [
            {
                "loan_id": "LN-S2",
                "stage": "Stage 2",
                "product_type": "SME term loan",
                "current_rating": 6,
                "pd_12m": 0.10,
                "pd_lifetime": 0.19,
                "lgd": 0.40,
                "ead": 1_000.0,
                "effective_interest_rate": 0.05,
                "residual_maturity_months": 24,
                "undrawn_commitment": 200.0,
                "ccf_base": 0.20,
                "amortisation_type": "Amortising",
            }
        ]
    )

    result = calculate_ecl(portfolio)

    adjusted_ccf = 0.20 + 0.10 + 0.05
    year_1_ead = 750.0 + 150.0 * adjusted_ccf
    year_2_ead = 250.0 + 50.0 * adjusted_ccf
    annual_hazard = 1 - (1 - 0.19) ** 0.5
    marginal_pd_1 = annual_hazard
    marginal_pd_2 = 0.19 - annual_hazard
    expected_ecl = (
        marginal_pd_1 * 0.40 * year_1_ead / 1.05
        + marginal_pd_2 * 0.40 * year_2_ead / (1.05**2)
    )

    assert marginal_pd_1 + marginal_pd_2 == pytest.approx(0.19)
    assert result.loc[0, "pd_used_for_ecl"] == pytest.approx(0.19)
    assert result.loc[0, "lgd_used_for_ecl"] == pytest.approx(0.40)
    assert result.loc[0, "ecl"] == pytest.approx(expected_ecl)


def test_stage2_short_maturity_uses_full_lifetime_pd():
    portfolio = pd.DataFrame(
        [
            {
                "loan_id": "LN-S2-SHORT",
                "stage": "Stage 2",
                "product_type": "Corporate loan",
                "current_rating": 6,
                "pd_12m": 0.10,
                "pd_lifetime": 0.10,
                "lgd": 0.40,
                "ead": 1_000.0,
                "effective_interest_rate": 0.05,
                "residual_maturity_months": 6,
                "undrawn_commitment": 0.0,
                "ccf_base": 0.0,
                "amortisation_type": "Bullet",
            }
        ]
    )

    result = calculate_ecl(portfolio)

    expected = 0.10 * 0.40 * 1_000.0 / (1.05**0.5)
    assert result.loc[0, "pd_used_for_ecl"] == pytest.approx(0.10)
    assert result.loc[0, "ecl"] == pytest.approx(expected)


def test_dynamic_stage3_ecl_uses_full_pd_lgd_and_ccf_ead():
    portfolio = pd.DataFrame(
        [
            {
                "loan_id": "LN-S3",
                "stage": "Stage 3",
                "product_type": "SME term loan",
                "current_rating": 9,
                "pd_12m": 0.40,
                "pd_lifetime": 0.80,
                "lgd": 0.60,
                "ead": 1_000.0,
                "effective_interest_rate": 0.05,
                "residual_maturity_months": 24,
                "undrawn_commitment": 200.0,
                "ccf_base": 0.20,
                "amortisation_type": "Amortising",
            }
        ]
    )

    result = calculate_ecl(portfolio)

    adjusted_ccf = 0.20 + 0.25 + 0.10 + 0.05
    expected_ead = 1_000.0 + 200.0 * adjusted_ccf
    expected_ecl = 1.0 * 0.60 * expected_ead

    assert result.loc[0, "pd_used_for_ecl"] == pytest.approx(1.0)
    assert result.loc[0, "ead_used_for_ecl"] == pytest.approx(expected_ead)
    assert result.loc[0, "ecl"] == pytest.approx(expected_ecl)


def test_ecl_uses_recovery_based_lgd_output():
    portfolio = pd.DataFrame(
        [
            {
                "loan_id": "LN-LGD",
                "stage": "Stage 1",
                "product_type": "Mortgage",
                "current_rating": 3,
                "pd_12m": 0.02,
                "pd_lifetime": 0.08,
                "lgd": 0.40,
                "ead": 100_000.0,
                "effective_interest_rate": 0.05,
                "residual_maturity_months": 24,
                "undrawn_commitment": 0.0,
                "ccf_base": 0.0,
                "amortisation_type": "Amortising",
                "collateral_value": 125_000.0,
                "collateral_haircut": 0.20,
                "liquidation_cost_rate": 0.07,
                "unsecured_recovery_rate": 0.18,
                "recovery_delay_months": 24,
                "recovery_cost_amount": 1_000.0,
                "seniority": "Senior secured",
            }
        ]
    )
    with_lgd = calculate_lgd(portfolio, preserve_missing_lgd=False)

    result = calculate_ecl(with_lgd)

    expected = (
        result.loc[0, "pd_used_for_ecl"]
        * with_lgd.loc[0, "lgd"]
        * result.loc[0, "ead_used_for_ecl"]
    )
    assert result.loc[0, "lgd_used_for_ecl"] == pytest.approx(
        with_lgd.loc[0, "lgd"]
    )
    assert result.loc[0, "ecl"] == pytest.approx(expected)
