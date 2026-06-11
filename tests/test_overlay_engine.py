import pandas as pd
import pytest

from modules.overlay_engine import apply_overlays


def _portfolio():
    return pd.DataFrame(
        [
            {
                "loan_id": "LN-1",
                "client_id": "CL-1",
                "stage": "Stage 2",
                "product_type": "SME term loan",
                "sector": "Energy",
                "country": "FR",
                "ead": 1_000,
                "ecl": 100,
                "critical_data_missing": True,
                "data_quality_status": "Issue",
            },
            {
                "loan_id": "LN-2",
                "client_id": "CL-2",
                "stage": "Stage 3",
                "product_type": "Corporate loan",
                "sector": "Real estate",
                "country": "DE",
                "ead": 2_000,
                "ecl": 200,
                "critical_data_missing": False,
                "data_quality_status": "OK",
            },
            {
                "loan_id": "LN-3",
                "client_id": "CL-3",
                "stage": "Stage 1",
                "product_type": "Consumer loan",
                "sector": "Retail",
                "country": "FR",
                "ead": 3_000,
                "ecl": 30,
                "critical_data_missing": False,
                "data_quality_status": "OK",
            },
        ]
    )


def test_sector_overlay_applies_to_correct_scope():
    result, summary = apply_overlays(_portfolio(), ["Commercial Real Estate Stress"])

    assert result.loc[result["loan_id"].eq("LN-2"), "overlay_amount"].iloc[0] == pytest.approx(30)
    assert result.loc[result["loan_id"].eq("LN-1"), "overlay_amount"].iloc[0] == 0
    assert summary.loc[0, "impacted_exposures"] == 1


def test_stage_2_overlay_applies_only_to_stage_2():
    result, _ = apply_overlays(_portfolio(), ["Stage 2 Prudence Overlay"])

    assert result.loc[result["loan_id"].eq("LN-1"), "overlay_amount"].iloc[0] == pytest.approx(5)
    assert result.loc[result["loan_id"].eq("LN-2"), "overlay_amount"].iloc[0] == 0


def test_global_overlay_type_applies_to_all_exposures_when_defined():
    portfolio = _portfolio()
    # The engine supports future expert_global overlays through the generic mask path.
    from modules import overlay_engine

    original = overlay_engine.PREDEFINED_OVERLAYS
    overlay_engine.PREDEFINED_OVERLAYS = [
        {
            "name": "Expert Global",
            "overlay_type": "expert_global",
            "scope": "All exposures",
            "rate": 0.10,
            "justification": "Global expert overlay.",
        }
    ]
    try:
        result, _ = apply_overlays(portfolio, ["Expert Global"])
    finally:
        overlay_engine.PREDEFINED_OVERLAYS = original

    assert result["overlay_amount"].sum() == pytest.approx(33)
    assert result["overlay_applied"].all()


def test_multiple_overlays_apply_without_duplicate_rows():
    portfolio = _portfolio()
    result, _ = apply_overlays(portfolio, ["SME Energy Sensitivity", "Data Quality Uncertainty", "Stage 2 Prudence Overlay"])
    impacted = result.loc[result["loan_id"].eq("LN-1")].iloc[0]

    assert len(result) == len(portfolio)
    assert impacted["overlay_amount"] == pytest.approx(35)
    assert "SME Energy Sensitivity" in impacted["overlay_names"]
    assert "Data Quality Uncertainty" in impacted["overlay_names"]
    assert "Stage 2 Prudence Overlay" in impacted["overlay_names"]


def test_ecl_after_overlay_equals_before_plus_overlay_amount():
    result, _ = apply_overlays(_portfolio(), ["Stage 3 Recovery Risk"])

    assert (result["ecl_after_overlay"] == result["ecl_before_overlay"] + result["overlay_amount"]).all()


def test_empty_overlay_selection_applies_no_overlay():
    result, summary = apply_overlays(_portfolio(), [])

    assert result["overlay_amount"].sum() == 0
    assert not result["overlay_applied"].any()
    assert summary.empty
