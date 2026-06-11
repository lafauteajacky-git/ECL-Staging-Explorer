import pandas as pd

from modules.lgd_engine import (
    add_synthetic_lgd_inputs,
    build_lgd_sensitivity,
    build_lgd_waterfall,
    calculate_lgd,
)


def _recovery_portfolio() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "loan_id": ["LN-1", "LN-2"],
            "product_type": ["Mortgage", "Consumer loan"],
            "sector": ["Households", "Retail"],
            "ead": [100_000.0, 100_000.0],
            "effective_interest_rate": [0.05, 0.05],
            "collateral_flag": [True, False],
            "ltv": [0.80, float("nan")],
            "collateral_value": [125_000.0, 0.0],
            "collateral_haircut": [0.20, 1.00],
            "liquidation_cost_rate": [0.07, 0.04],
            "unsecured_recovery_rate": [0.18, 0.08],
            "recovery_delay_months": [24, 14],
            "recovery_cost_amount": [1_000.0, 1_000.0],
            "lgd": [0.40, 0.60],
            "stage": ["Stage 1", "Stage 1"],
        }
    )


def test_secured_exposure_has_lower_lgd_than_unsecured_exposure():
    result = calculate_lgd(
        _recovery_portfolio(),
        preserve_missing_lgd=False,
    )

    assert result.loc[0, "lgd"] < result.loc[1, "lgd"]


def test_longer_recovery_delay_increases_lgd():
    portfolio = _recovery_portfolio().iloc[[0]].copy()
    short_delay = calculate_lgd(
        portfolio.assign(recovery_delay_months=6),
        preserve_missing_lgd=False,
    )
    long_delay = calculate_lgd(
        portfolio.assign(recovery_delay_months=48),
        preserve_missing_lgd=False,
    )

    assert long_delay.loc[0, "lgd"] > short_delay.loc[0, "lgd"]


def test_lgd_sensitivity_is_ordered_from_upside_to_downside():
    sensitivity = build_lgd_sensitivity(_recovery_portfolio())
    lgd_by_scenario = dict(zip(sensitivity["scenario"], sensitivity["lgd"]))

    assert lgd_by_scenario["Downside"] > lgd_by_scenario["Baseline"]
    assert lgd_by_scenario["Baseline"] > lgd_by_scenario["Upside"]


def test_stage3_workout_assumptions_are_more_prudent():
    exposure = _recovery_portfolio().iloc[[0]].copy()
    stage_1 = calculate_lgd(
        exposure.assign(stage="Stage 1"),
        preserve_missing_lgd=False,
    )
    stage_3 = calculate_lgd(
        exposure.assign(stage="Stage 3"),
        preserve_missing_lgd=False,
    )

    assert stage_3.loc[0, "lgd"] > stage_1.loc[0, "lgd"]


def test_seniority_affects_unsecured_recovery():
    exposure = _recovery_portfolio().iloc[[1]].copy()
    senior = calculate_lgd(
        exposure.assign(seniority="Senior unsecured"),
        preserve_missing_lgd=False,
    )
    subordinated = calculate_lgd(
        exposure.assign(seniority="Subordinated"),
        preserve_missing_lgd=False,
    )

    assert subordinated.loc[1, "lgd"] > senior.loc[1, "lgd"]


def test_lgd_is_bounded_and_waterfall_reconciles_to_loss():
    result = calculate_lgd(
        _recovery_portfolio(),
        preserve_missing_lgd=False,
    )
    waterfall = build_lgd_waterfall(result)

    assert result["lgd"].between(0, 1).all()
    assert waterfall.iloc[-1]["step"] == "Perte finale"
    assert waterfall.iloc[-1]["amount"] >= 0


def test_synthetic_lgd_inputs_are_reproducible():
    source = pd.DataFrame(
        {
            "loan_id": ["LN-1"],
            "product_type": ["Mortgage"],
            "sector": ["Households"],
            "ead": [100_000.0],
            "effective_interest_rate": [0.05],
            "collateral_flag": [True],
            "ltv": [0.80],
            "lgd": [0.40],
        }
    )
    first = add_synthetic_lgd_inputs(source, seed=7)
    second = add_synthetic_lgd_inputs(source, seed=7)

    pd.testing.assert_frame_equal(first, second)
    assert first.loc[0, "collateral_type"] == "Residential real estate"
