"""Simplified IFRS 9 staging engine for demonstration purposes."""

from __future__ import annotations

import numpy as np
import pandas as pd


def assign_stage(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Assign IFRS 9 stages using transparent, simplified business rules."""
    staged = portfolio.copy()
    rating_downgrade = staged["current_rating"] - staged["origination_rating"]

    stage_3 = staged["default_flag"].fillna(False) | (staged["days_past_due"] >= 90)
    stage_2 = (
        (staged["days_past_due"] >= 30)
        | (rating_downgrade >= 2)
        | staged["forbearance_flag"].fillna(False)
        | staged["watchlist_flag"].fillna(False)
    )

    staged["stage"] = np.select([stage_3, stage_2], ["Stage 3", "Stage 2"], default="Stage 1")
    staged["stage_reason"] = np.select(
        [
            staged["default_flag"].fillna(False),
            staged["days_past_due"] >= 90,
            staged["days_past_due"] >= 30,
            rating_downgrade >= 2,
            staged["forbearance_flag"].fillna(False),
            staged["watchlist_flag"].fillna(False),
        ],
        [
            "Default flag",
            "DPD >= 90",
            "DPD >= 30",
            "Rating downgrade >= 2 notches",
            "Forbearance",
            "Watchlist",
        ],
        default="No significant increase in credit risk",
    )
    staged["stage_comment"] = np.select(
        [
            staged["default_flag"].fillna(False),
            staged["days_past_due"] >= 90,
            staged["days_past_due"] >= 30,
            rating_downgrade >= 2,
            staged["forbearance_flag"].fillna(False),
            staged["watchlist_flag"].fillna(False),
        ],
        [
            "Exposure classified in Stage 3 because a default indicator is active.",
            "Exposure classified in Stage 3 because days past due are at least 90.",
            "Exposure classified in Stage 2 because days past due are at least 30.",
            "Exposure classified in Stage 2 because the rating deteriorated by at least two notches.",
            "Exposure classified in Stage 2 because forbearance is active.",
            "Exposure classified in Stage 2 because the exposure is on the watchlist.",
        ],
        default="Exposure remains in Stage 1 under the simplified MVP rules.",
    )
    return staged
