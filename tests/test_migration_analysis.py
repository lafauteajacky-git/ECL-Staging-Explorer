import math

import pandas as pd

from modules.migration_analysis import (
    DEFAULT_LABEL,
    build_average_migration_by_dimension,
    build_rating_transition_matrix,
    build_stage_transition_matrix,
    build_top_strong_migrations,
    calculate_rating_migration_metrics,
)


def build_migration_portfolio():
    return pd.DataFrame(
        {
            "loan_id": ["L1", "L2", "L3", "L4", "L5"],
            "client_id": ["C1", "C2", "C3", "C4", "C5"],
            "product_type": ["Mortgage", "SME term loan", "Corporate loan", "Consumer loan", "Credit card"],
            "sector": ["Households", "Retail", "Energy", "Technology", "Manufacturing"],
            "country": ["FR", "FR", "DE", "ES", "IT"],
            "ead": [100.0, 200.0, 300.0, 400.0, 500.0],
            "origination_rating": [1, 2, 3, 4, 5],
            "current_rating": [1, 3, 5, 2, 7],
            "pd_12m": [0.01, 0.02, 0.05, 0.01, 0.20],
            "pd_lifetime": [0.03, 0.08, 0.15, 0.04, 0.60],
            "lgd": [0.30, 0.35, 0.40, 0.25, 0.55],
            "days_past_due": [0, 30, 45, 0, 100],
            "default_flag": [False, False, False, False, True],
            "initial_stage": ["Stage 1", "Stage 1", "Stage 1", "Stage 2", "Stage 2"],
            "stage": ["Stage 1", "Stage 2", "Stage 2", "Stage 1", "Stage 3"],
            "stage_reason": [
                "No significant increase in credit risk",
                "DPD >= 30",
                "Rating downgrade >= 2 notches",
                "No significant increase in credit risk",
                "Default flag",
            ],
        }
    )


def test_rating_matrix_is_row_normalized_and_contains_default():
    matrix = build_rating_transition_matrix(build_migration_portfolio(), measure="count")

    assert DEFAULT_LABEL in matrix.columns
    assert math.isclose(matrix.loc["5", DEFAULT_LABEL], 1.0)
    assert math.isclose(matrix.loc["1"].sum(), 1.0)


def test_rating_matrix_can_be_expressed_as_ead_share():
    matrix = build_rating_transition_matrix(build_migration_portfolio(), measure="ead")

    assert math.isclose(matrix.loc["2", "3"], 1.0)
    assert math.isclose(matrix.loc["5", DEFAULT_LABEL], 1.0)


def test_stage_matrix_filters_stage_reasons():
    portfolio = build_migration_portfolio()
    matrix = build_stage_transition_matrix(
        portfolio,
        measure="count",
        stage_reasons=["DPD >= 30", "Default flag"],
    )

    assert math.isclose(matrix.loc["Stage 1", "Stage 2"], 1.0)
    assert math.isclose(matrix.loc["Stage 2", "Stage 3"], 1.0)


def test_rating_migration_metrics_cover_count_and_ead():
    metrics = calculate_rating_migration_metrics(build_migration_portfolio())

    assert math.isclose(metrics["stability_rate"], 0.20)
    assert math.isclose(metrics["degradation_rate"], 0.60)
    assert math.isclose(metrics["improvement_rate"], 0.20)
    assert math.isclose(metrics["net_migration_rate"], 0.40)
    assert math.isclose(metrics["default_migration_rate"], 0.20)
    assert math.isclose(metrics["default_migration_ead_rate"], 500 / 1500)
    assert math.isclose(metrics["degradation_ead_rate"], 1000 / 1500)
    assert math.isclose(metrics["improvement_ead_rate"], 400 / 1500)


def test_top_strong_migrations_contains_default_and_two_notch_downgrade():
    top = build_top_strong_migrations(build_migration_portfolio())

    assert set(top["loan_id"]) == {"L3", "L5"}
    assert top.iloc[0]["rating_migration_type"] == "Migration vers defaut"


def test_average_migration_can_be_segmented_by_product():
    summary = build_average_migration_by_dimension(
        build_migration_portfolio(),
        "product_type",
    )

    assert set(summary["product_type"]) == {
        "Mortgage",
        "SME term loan",
        "Corporate loan",
        "Consumer loan",
        "Credit card",
    }
    credit_card = summary.loc[summary["product_type"].eq("Credit card")].iloc[0]
    assert credit_card["ead_weighted_notch_migration"] > 0
