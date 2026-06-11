from datetime import datetime

import pandas as pd

from modules.audit_trail import build_audit_trail, generate_run_id
from modules.reporting import STAGING_RULES


def test_generate_run_id_contains_timestamp():
    run_id = generate_run_id(datetime(2026, 5, 29, 10, 11, 12))
    assert run_id == "RUN-20260529-101112"


def test_build_audit_trail_returns_required_sections():
    audit = build_audit_trail(
        "RUN-1",
        datetime(2026, 5, 29, 10, 0, 0),
        {"exposure_count": 2, "total_ead": 1000, "total_ecl": 50},
        {"ecl_weighted": 55},
        {"ecl_before_overlay": 50, "total_overlay_amount": 5, "ecl_after_overlay": 55},
        pd.DataFrame({"stage": ["Stage 1"], "ead": [1000], "ecl": [50]}),
        pd.DataFrame({"scenario": ["Baseline"], "weight": [1.0]}),
        pd.DataFrame({"scenario": ["Baseline"], "ecl": [55]}),
        pd.DataFrame({"name": ["Overlay"]}),
        pd.DataFrame({"overlay_name": ["Overlay"], "overlay_amount": [5]}),
        pd.DataFrame({"loan_id": ["LN-1"]}),
        pd.DataFrame({"loan_id": ["LN-2"]}),
        pd.DataFrame({"loan_id": ["LN-1"], "ecl": [50]}),
        pd.DataFrame({"rule": ["Stage 1"]}),
        pd.DataFrame({"stage": ["Stage 1"]}),
        lgd_summary={"lgd_ead_weighted": 0.40},
        lgd_sensitivity=pd.DataFrame(
            {"scenario": ["Baseline"], "lgd": [0.40]}
        ),
    )

    assert "run_summary" in audit
    assert "scenario_parameters" in audit
    assert "overlay_summary" in audit
    assert "methodological_warnings" in audit
    assert "lgd_summary" in audit
    assert "lgd_sensitivity" in audit
    assert "run_id" in set(audit["run_summary"]["field"])


def test_staging_audit_rules_cover_minimum_transitions():
    transitions = {item["rule"] for item in STAGING_RULES}

    assert "Stage 1 -> Stage 2" in transitions
    assert "Stage 2 -> Stage 1" in transitions
    assert "Stage 2 -> Stage 3" in transitions
    assert "Stage 3 -> Stage 2" in transitions
    assert "Stage 3 -> Stage 1" in transitions
