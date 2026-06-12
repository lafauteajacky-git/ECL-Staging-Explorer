"""Simplified IFRS 9 staging and cure-transition engine."""

from __future__ import annotations

import numpy as np
import pandas as pd

from modules.data_types import coerce_boolean_series


STAGE_3_TO_2_CURE_MONTHS = 3
STAGE_2_TO_1_CURE_MONTHS = 6
STAGE_3_TO_1_CURE_MONTHS = 12
SICR_PD_RATIO_THRESHOLD = 2.0


def assign_stage(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Assign IFRS 9 stages using current triggers and prior-stage cure rules."""
    staged = portfolio.copy()
    index = staged.index

    origination_rating = pd.to_numeric(staged["origination_rating"], errors="coerce")
    current_rating = pd.to_numeric(staged["current_rating"], errors="coerce")
    days_past_due = pd.to_numeric(staged["days_past_due"], errors="coerce").fillna(0)
    rating_downgrade = current_rating - origination_rating

    default_flag = _boolean_series(staged, "default_flag")
    credit_impaired = _boolean_series(staged, "credit_impaired_flag")
    unlikely_to_pay = _boolean_series(staged, "unlikely_to_pay_flag")
    bankruptcy = _boolean_series(staged, "bankruptcy_flag")
    distressed_restructuring = _boolean_series(staged, "distressed_restructuring_flag")
    forbearance = _boolean_series(staged, "forbearance_flag")
    watchlist = _boolean_series(staged, "watchlist_flag")
    macro_sector_stress = _boolean_series(staged, "macro_sector_stress_flag")

    current_default = (
        default_flag
        | credit_impaired
        | days_past_due.ge(90)
        | unlikely_to_pay
        | bankruptcy
        | distressed_restructuring
    )

    origination_pd = pd.to_numeric(
        staged.get("origination_pd_12m", pd.Series(np.nan, index=index)),
        errors="coerce",
    )
    current_pd = pd.to_numeric(
        staged.get("pd_12m", pd.Series(np.nan, index=index)),
        errors="coerce",
    )
    pd_ratio_trigger = (current_pd / origination_pd.replace(0, np.nan)).ge(
        SICR_PD_RATIO_THRESHOLD
    )
    explicit_sicr = _boolean_series(staged, "sicr_flag")
    sicr = (
        explicit_sicr
        | days_past_due.ge(30)
        | rating_downgrade.ge(2)
        | pd_ratio_trigger
        | forbearance
        | watchlist
        | macro_sector_stress
    ) & ~current_default

    previous_stage = staged.get(
        "previous_stage",
        staged.get("initial_stage", pd.Series("Stage 1", index=index)),
    ).fillna("Stage 1")
    cure_months = pd.to_numeric(
        staged.get("cure_period_months", pd.Series(0, index=index)),
        errors="coerce",
    ).fillna(0)
    payment_normalized = _boolean_series(staged, "payment_normalized_flag")
    if "payment_normalized_flag" not in staged:
        payment_normalized = (
            days_past_due.lt(30)
            & ~current_default
            & ~watchlist
            & ~forbearance
        )
    strong_stage_3_to_1 = _boolean_series(
        staged,
        "strong_stage_3_to_1_justification_flag",
    )

    from_stage_3 = previous_stage.eq("Stage 3")
    from_stage_2 = previous_stage.eq("Stage 2")
    from_stage_1 = ~from_stage_3 & ~from_stage_2

    stage_3_to_1 = (
        from_stage_3
        & ~current_default
        & ~sicr
        & payment_normalized
        & strong_stage_3_to_1
        & cure_months.ge(STAGE_3_TO_1_CURE_MONTHS)
    )
    stage_3_to_2 = (
        from_stage_3
        & ~current_default
        & ~stage_3_to_1
        & sicr
        & cure_months.ge(STAGE_3_TO_2_CURE_MONTHS)
    )
    stage_2_to_1 = (
        from_stage_2
        & ~current_default
        & ~sicr
        & payment_normalized
        & cure_months.ge(STAGE_2_TO_1_CURE_MONTHS)
    )

    final_stage = np.select(
        [
            current_default,
            stage_3_to_1,
            stage_3_to_2,
            from_stage_3,
            stage_2_to_1,
            from_stage_2,
            from_stage_1 & sicr,
        ],
        [
            "Stage 3",
            "Stage 1",
            "Stage 2",
            "Stage 3",
            "Stage 1",
            "Stage 2",
            "Stage 2",
        ],
        default="Stage 1",
    )
    staged["previous_stage"] = previous_stage
    staged["current_default_trigger"] = current_default
    staged["current_sicr_trigger"] = sicr
    staged["stage"] = final_stage

    default_reason = np.select(
        [
            bankruptcy,
            distressed_restructuring,
            unlikely_to_pay,
            default_flag,
            credit_impaired,
            days_past_due.ge(90),
        ],
        [
            "Probable bankruptcy",
            "Distressed restructuring",
            "Unlikely to pay",
            "Default flag",
            "Credit-impaired indicator",
            "DPD >= 90",
        ],
        default="Credit-impaired event",
    )
    sicr_reason = np.select(
        [
            days_past_due.ge(30),
            rating_downgrade.ge(2),
            pd_ratio_trigger,
            forbearance,
            watchlist,
            macro_sector_stress,
        ],
        [
            "DPD >= 30",
            "Rating downgrade >= 2 notches",
            "PD increase >= 2x origination",
            "Forbearance",
            "Watchlist",
            "Macro-sector signal",
        ],
        default="SICR indicator",
    )
    staged["stage_reason"] = np.select(
        [
            current_default,
            stage_3_to_1,
            stage_3_to_2,
            from_stage_3,
            stage_2_to_1,
            from_stage_2 & sicr,
            from_stage_2,
            from_stage_1 & sicr,
        ],
        [
            default_reason,
            "Exceptional Stage 3 cure to Stage 1",
            "Stage 3 cure completed - residual risk",
            "Stage 3 exit criteria not met",
            "Stage 2 cure completed",
            sicr_reason,
            "Stage 2 probation period not completed",
            sicr_reason,
        ],
        default="No significant increase in credit risk",
    )
    staged["transition_rule"] = np.select(
        [
            current_default & from_stage_2,
            current_default & from_stage_1,
            current_default & from_stage_3,
            stage_3_to_1,
            stage_3_to_2,
            from_stage_3,
            stage_2_to_1,
            from_stage_2,
            from_stage_1 & sicr,
        ],
        [
            "Stage 2 -> Stage 3",
            "Stage 1 -> Stage 3",
            "Stage 3 maintained",
            "Stage 3 -> Stage 1",
            "Stage 3 -> Stage 2",
            "Stage 3 maintained during cure",
            "Stage 2 -> Stage 1",
            "Stage 2 maintained during probation",
            "Stage 1 -> Stage 2",
        ],
        default="Stage 1 maintained",
    )
    staged["probation_status"] = np.select(
        [
            current_default,
            from_stage_3 & cure_months.lt(STAGE_3_TO_2_CURE_MONTHS),
            stage_3_to_2,
            stage_3_to_1,
            from_stage_3 & ~current_default,
            from_stage_2 & ~stage_2_to_1,
            stage_2_to_1,
        ],
        [
            "Default / credit-impaired",
            "Stage 3 cure in progress",
            "Stage 3 cure completed",
            "Exceptional full cure completed",
            "Stage 3 prudential maintenance",
            "Stage 2 probation in progress",
            "Stage 2 probation completed",
        ],
        default="No probation",
    )
    staged["returned_to_stage_1_flag"] = stage_2_to_1 | stage_3_to_1
    cure_related = (
        staged["stage_reason"]
        .fillna("")
        .astype(str)
        .str.contains("cure|probation", case=False, regex=True)
    )
    base_comment = (
        staged["transition_rule"].astype(str)
        + ": "
        + staged["stage_reason"].astype(str)
        + "."
    )
    cure_comment = (
        staged["transition_rule"].astype(str)
        + ": "
        + staged["stage_reason"].astype(str)
        + ". Cure/probation observee sur "
        + cure_months.round().astype(int).astype(str)
        + " mois selon les seuils pedagogiques du demonstrateur."
    )
    staged["stage_comment"] = np.where(
        cure_related,
        cure_comment,
        base_comment,
    )
    return staged


def _boolean_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(False, index=frame.index)
    return coerce_boolean_series(frame[column])


def _build_stage_comment(row: pd.Series) -> str:
    transition = row["transition_rule"]
    reason = row["stage_reason"]
    cure_value = pd.to_numeric(pd.Series([row.get("cure_period_months", 0)]), errors="coerce").iloc[0]
    cure_months = int(cure_value) if pd.notna(cure_value) else 0
    if "cure" in reason.lower() or "probation" in reason.lower():
        return (
            f"{transition}: {reason}. Cure/probation observee sur {cure_months} mois "
            "selon les seuils pedagogiques du demonstrateur."
        )
    return f"{transition}: {reason}."
