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
