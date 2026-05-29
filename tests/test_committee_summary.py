import pandas as pd

from modules.committee_summary import REQUIRED_SECTIONS, generate_committee_summary


def test_committee_summary_contains_required_sections_and_kpis():
    note = generate_committee_summary(
        "RUN-1",
        {
            "total_ead": 1000,
            "total_ecl": 50,
            "coverage_ratio": 0.05,
            "exposure_count": 2,
            "data_quality_issue_count": 1,
        },
        {
            "ecl_weighted": 55,
            "weighted_impact_amount": 5,
            "weighted_impact_pct": 0.10,
            "downside_impact_amount": 10,
            "downside_impact_pct": 0.20,
        },
        {
            "ecl_before_overlay": 55,
            "ecl_after_overlay": 60,
            "total_overlay_amount": 5,
            "overlay_variation_pct": 0.09,
            "top_overlay_contributor": "Stage 2 Prudence Overlay",
        },
        pd.DataFrame({"stage": ["Stage 1"], "exposure_count": [2], "ead": [1000], "ecl": [50]}),
        pd.DataFrame({"product_type": ["SME"], "ecl": [50]}),
        pd.DataFrame({"sector": ["Energy"], "ecl": [50]}),
        pd.DataFrame({"stage": ["Stage 1"], "count": [2]}),
        pd.DataFrame({"scenario": ["Baseline"], "weight": [1.0]}),
        pd.DataFrame({"scenario": ["Baseline"], "weight": [1.0], "ecl": [55]}),
        pd.DataFrame({"overlay_name": ["Stage 2 Prudence Overlay"], "overlay_amount": [5], "justification": ["Prudence"]}),
        pd.DataFrame({"check_code": ["MISSING_PD"], "issue_count": [1]}),
        1,
        pd.DataFrame({"loan_id": ["LN-1"], "ecl": [50], "stage": ["Stage 1"]}),
        ["Message cle"],
    )

    for section in REQUIRED_SECTIONS:
        assert section in note
    assert "RUN-1" in note
    assert "1 000 EUR" in note
    assert "60 EUR" in note
