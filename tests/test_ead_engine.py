import pandas as pd
import pytest

from modules.ead_engine import (
    add_synthetic_ead_inputs,
    aggregate_ead_curve,
    build_ead_term_structure,
    calculate_ead,
    summarize_ead,
)


def _portfolio() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "loan_id": ["LN-1", "LN-2", "LN-3"],
            "product_type": ["Mortgage", "Corporate loan", "Credit card"],
            "stage": ["Stage 1", "Stage 2", "Stage 1"],
            "current_rating": [3, 8, 5],
            "ead": [120_000.0, 100_000.0, 20_000.0],
            "undrawn_commitment": [0.0, 50_000.0, 30_000.0],
            "ccf_base": [0.0, 0.40, 0.75],
            "amortisation_type": ["Amortising", "Bullet", "Revolving"],
            "residual_maturity_months": [60, 36, 48],
        }
    )


def test_undrawn_commitment_and_ccf_increase_ead():
    result = calculate_ead(_portfolio())

    corporate = result.loc[result["loan_id"].eq("LN-2")].iloc[0]
    assert corporate["ccf_adjusted"] > corporate["ccf_base"]
    assert corporate["ead_at_default"] > corporate["ead_accounting"]
    assert corporate["ead_off_balance"] == pytest.approx(
        corporate["undrawn_commitment"] * corporate["ccf_adjusted"]
    )


def test_amortising_ead_declines_while_revolving_ead_remains_available():
    term = build_ead_term_structure(_portfolio())
    mortgage = term.loc[term["loan_id"].eq("LN-1")]
    card = term.loc[term["loan_id"].eq("LN-3")]

    assert mortgage["ead_projected"].is_monotonic_decreasing
    assert mortgage["ead_projected"].iloc[-1] < mortgage["ead_projected"].iloc[0]
    assert card["ead_projected"].nunique() == 1


def test_ead_summary_and_curve_reconcile():
    result = calculate_ead(_portfolio())
    term = build_ead_term_structure(result)
    summary = summarize_ead(result)
    curve = aggregate_ead_curve(term, "product_type")

    assert summary["ead_at_default"] == pytest.approx(result["ead"].sum())
    assert 0 <= summary["ccf_weighted"] <= 1
    assert set(curve["product_type"]) == {
        "Mortgage",
        "Corporate loan",
        "Credit card",
    }


def test_synthetic_ead_inputs_are_reproducible():
    source = pd.DataFrame(
        {
            "loan_id": ["LN-1", "LN-2"],
            "product_type": ["SME term loan", "Credit card"],
            "ead": [100_000.0, 10_000.0],
        }
    )

    first = add_synthetic_ead_inputs(source, seed=9)
    second = add_synthetic_ead_inputs(source, seed=9)

    pd.testing.assert_frame_equal(first, second)
    assert (first["credit_limit"] >= first["ead"]).all()
    assert first["ccf_base"].between(0, 1).all()
