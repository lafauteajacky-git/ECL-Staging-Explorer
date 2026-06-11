import numpy as np
import pandas as pd
import pytest

from modules.risk_parameters import (
    add_lifetime_pd_metrics,
    aggregate_lifetime_pd_curve,
    build_lifetime_pd_term_structure,
    calculate_lifetime_pd,
    summarize_risk_parameters,
)


def _portfolio():
    return pd.DataFrame(
        [
            {
                "loan_id": "LN-1",
                "stage": "Stage 1",
                "product_type": "Mortgage",
                "sector": "Households",
                "current_rating": 2,
                "ead": 1_000.0,
                "pd_12m": 0.02,
                "lgd": 0.30,
                "residual_maturity_months": 24,
            },
            {
                "loan_id": "LN-2",
                "stage": "Stage 2",
                "product_type": "SME term loan",
                "sector": "Energy",
                "current_rating": 6,
                "ead": 2_000.0,
                "pd_12m": 0.10,
                "lgd": 0.50,
                "residual_maturity_months": 36,
            },
        ]
    )


def test_lifetime_pd_uses_constant_hazard_formula():
    result = calculate_lifetime_pd(0.10, 36)

    assert result == pytest.approx(1 - (1 - 0.10) ** 3)


def test_lifetime_pd_is_capped_and_not_below_12m_pd():
    values = calculate_lifetime_pd(
        pd.Series([0.20, 1.20, -0.10]),
        pd.Series([6, 120, 24]),
    )

    assert values.iloc[0] == pytest.approx(0.20)
    assert values.iloc[1] == 1.0
    assert values.iloc[2] == 0.0


def test_add_lifetime_pd_metrics_adds_method_and_multiplier():
    result = add_lifetime_pd_metrics(_portfolio())

    assert "pd_lifetime" in result
    assert "pd_lifetime_multiplier" in result
    assert "pd_lifetime_method" in result
    assert (result["pd_lifetime"] >= result["pd_12m"]).all()


def test_term_structure_is_monotonic_and_marginals_reconcile():
    enriched = add_lifetime_pd_metrics(_portfolio())
    curve = build_lifetime_pd_term_structure(enriched)
    loan_curve = curve.loc[curve["loan_id"].eq("LN-2")]

    assert loan_curve["cumulative_pd"].is_monotonic_increasing
    assert loan_curve["marginal_pd"].sum() == pytest.approx(
        loan_curve["cumulative_pd"].iloc[-1]
    )


def test_term_structure_preserves_partial_final_year():
    portfolio = _portfolio().iloc[[0]].assign(residual_maturity_months=18)
    curve = build_lifetime_pd_term_structure(portfolio)

    assert curve["horizon_months"].tolist() == [12.0, 18.0]
    assert curve["cumulative_pd"].iloc[-1] == pytest.approx(
        1 - (1 - 0.02) ** 1.5
    )
    assert curve["marginal_pd"].sum() == pytest.approx(
        curve["cumulative_pd"].iloc[-1]
    )


def test_risk_parameter_summary_and_curve_are_ead_weighted():
    enriched = add_lifetime_pd_metrics(_portfolio())
    term_structure = build_lifetime_pd_term_structure(enriched)
    summary = summarize_risk_parameters(enriched)
    curve = aggregate_lifetime_pd_curve(term_structure, "stage")

    expected_pd_12m = (0.02 * 1_000 + 0.10 * 2_000) / 3_000
    assert summary["pd_12m_ead_weighted"] == pytest.approx(expected_pd_12m)
    assert set(curve["stage"]) == {"Stage 1", "Stage 2"}
    assert np.isfinite(curve["cumulative_pd"]).all()
