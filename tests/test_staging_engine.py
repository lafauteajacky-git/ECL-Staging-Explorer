import pandas as pd

from modules.staging_engine import assign_stage


def _base_row(**overrides):
    row = {
        "loan_id": "LN-1",
        "origination_rating": 3,
        "current_rating": 3,
        "days_past_due": 0,
        "default_flag": False,
        "forbearance_flag": False,
        "watchlist_flag": False,
    }
    row.update(overrides)
    return row


def test_assigns_stage_3_for_default_flag():
    result = assign_stage(pd.DataFrame([_base_row(default_flag=True)]))
    assert result.loc[0, "stage"] == "Stage 3"
    assert result.loc[0, "stage_reason"] == "Default flag"
    assert "Stage 3" in result.loc[0, "stage_comment"]


def test_assigns_stage_3_for_dpd_90_or_more():
    result = assign_stage(pd.DataFrame([_base_row(days_past_due=90)]))
    assert result.loc[0, "stage"] == "Stage 3"


def test_assigns_stage_2_for_rating_downgrade():
    result = assign_stage(pd.DataFrame([_base_row(current_rating=5)]))
    assert result.loc[0, "stage"] == "Stage 2"
    assert result.loc[0, "stage_reason"] == "Rating downgrade >= 2 notches"


def test_stage_3_takes_priority_over_stage_2():
    result = assign_stage(pd.DataFrame([_base_row(days_past_due=120, watchlist_flag=True)]))
    assert result.loc[0, "stage"] == "Stage 3"


def test_stage_3_to_stage_2_requires_completed_cure():
    completed = assign_stage(
        pd.DataFrame(
            [
                _base_row(
                    previous_stage="Stage 3",
                    cure_period_months=3,
                    payment_normalized_flag=True,
                    sicr_flag=True,
                )
            ]
        )
    )
    incomplete = assign_stage(
        pd.DataFrame(
            [
                _base_row(
                    previous_stage="Stage 3",
                    cure_period_months=2,
                    payment_normalized_flag=True,
                    sicr_flag=True,
                )
            ]
        )
    )

    assert completed.loc[0, "stage"] == "Stage 2"
    assert completed.loc[0, "transition_rule"] == "Stage 3 -> Stage 2"
    assert incomplete.loc[0, "stage"] == "Stage 3"


def test_stage_2_to_stage_1_requires_normalization_and_six_months():
    completed = assign_stage(
        pd.DataFrame(
            [
                _base_row(
                    previous_stage="Stage 2",
                    cure_period_months=6,
                    payment_normalized_flag=True,
                    sicr_flag=False,
                )
            ]
        )
    )
    incomplete = assign_stage(
        pd.DataFrame(
            [
                _base_row(
                    previous_stage="Stage 2",
                    cure_period_months=5,
                    payment_normalized_flag=True,
                    sicr_flag=False,
                )
            ]
        )
    )

    assert completed.loc[0, "stage"] == "Stage 1"
    assert completed.loc[0, "returned_to_stage_1_flag"]
    assert incomplete.loc[0, "stage"] == "Stage 2"


def test_stage_2_to_stage_3_accepts_unlikely_to_pay_trigger():
    result = assign_stage(
        pd.DataFrame(
            [
                _base_row(
                    previous_stage="Stage 2",
                    unlikely_to_pay_flag=True,
                )
            ]
        )
    )

    assert result.loc[0, "stage"] == "Stage 3"
    assert result.loc[0, "stage_reason"] == "Unlikely to pay"
    assert result.loc[0, "transition_rule"] == "Stage 2 -> Stage 3"


def test_stage_3_to_stage_1_is_exceptional_and_requires_strong_justification():
    result = assign_stage(
        pd.DataFrame(
            [
                _base_row(
                    previous_stage="Stage 3",
                    cure_period_months=12,
                    payment_normalized_flag=True,
                    sicr_flag=False,
                    strong_stage_3_to_1_justification_flag=True,
                )
            ]
        )
    )

    assert result.loc[0, "stage"] == "Stage 1"
    assert result.loc[0, "transition_rule"] == "Stage 3 -> Stage 1"


def test_stage_1_to_stage_2_accepts_pd_increase_trigger():
    result = assign_stage(
        pd.DataFrame(
            [
                _base_row(
                    previous_stage="Stage 1",
                    origination_pd_12m=0.01,
                    pd_12m=0.03,
                )
            ]
        )
    )

    assert result.loc[0, "stage"] == "Stage 2"
    assert result.loc[0, "stage_reason"] == "PD increase >= 2x origination"


def test_text_false_boolean_flags_do_not_trigger_stage_2_or_stage_3():
    result = assign_stage(
        pd.DataFrame(
            [
                _base_row(
                    default_flag="False",
                    forbearance_flag="False",
                    watchlist_flag="False",
                )
            ]
        )
    )

    assert result.loc[0, "stage"] == "Stage 1"
