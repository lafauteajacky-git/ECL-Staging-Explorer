"""Migration analysis helpers for ratings and IFRS 9 stages."""

from __future__ import annotations

import numpy as np
import pandas as pd

from modules.data_types import coerce_boolean_series


DEFAULT_LABEL = "Defaut"
WORST_GRADE_THRESHOLD = 8


def prepare_rating_migrations(
    portfolio: pd.DataFrame,
    source_rating: str = "origination_rating",
) -> pd.DataFrame:
    """Add rating migration classifications to a staged portfolio."""
    if source_rating not in portfolio.columns:
        raise ValueError(f"Unknown source rating: {source_rating}")
    result = portfolio.copy()
    reference = pd.to_numeric(result[source_rating], errors="coerce")
    current = pd.to_numeric(result["current_rating"], errors="coerce")
    current_default = (
        coerce_boolean_series(result["default_flag"])
        | pd.to_numeric(result["days_past_due"], errors="coerce").ge(90)
        | result.get("stage", pd.Series("", index=result.index)).eq("Stage 3")
    )

    result["rating_reference_column"] = source_rating
    result["reference_rating"] = reference
    result["rating_change_notches"] = current - reference
    result["current_rating_bucket"] = current.map(_format_rating).where(~current_default, DEFAULT_LABEL)
    result["reference_rating_bucket"] = reference.map(_format_rating)
    result["rating_migration_type"] = np.select(
        [
            current_default,
            result["rating_change_notches"].eq(0),
            result["rating_change_notches"].eq(1),
            result["rating_change_notches"].ge(2),
            result["rating_change_notches"].lt(0),
        ],
        [
            "Migration vers defaut",
            "Stable",
            "Degradation 1 cran",
            "Degradation >= 2 crans",
            "Amelioration",
        ],
        default="Non classe",
    )
    result["strong_migration"] = current_default | result["rating_change_notches"].abs().ge(4)
    return result


def build_rating_transition_matrix(
    portfolio: pd.DataFrame,
    measure: str = "count",
    source_rating: str = "origination_rating",
) -> pd.DataFrame:
    """Build a row-normalized rating transition matrix in count or EAD."""
    migrations = prepare_rating_migrations(portfolio, source_rating)
    values = None if measure == "count" else pd.to_numeric(migrations["ead"], errors="coerce").fillna(0)
    matrix = pd.crosstab(
        migrations["reference_rating_bucket"],
        migrations["current_rating_bucket"],
        values=values,
        aggfunc="sum" if values is not None else None,
        normalize="index",
        dropna=False,
    ).fillna(0)
    rating_labels = [str(rating) for rating in range(1, 11)]
    matrix = matrix.reindex(index=rating_labels, columns=rating_labels + [DEFAULT_LABEL], fill_value=0)
    matrix.index.name = (
        "Note a l'octroi"
        if source_rating == "origination_rating"
        else "Note precedente"
    )
    return matrix


def build_stage_transition_matrix(
    portfolio: pd.DataFrame,
    measure: str = "count",
    stage_reasons: list[str] | None = None,
) -> pd.DataFrame:
    """Build a row-normalized prior/final stage matrix with reason filtering."""
    filtered = portfolio.copy()
    if stage_reasons is not None:
        filtered = filtered.loc[filtered["stage_reason"].isin(stage_reasons)].copy()
    source_stage = "previous_stage" if "previous_stage" in filtered.columns else "initial_stage"
    values = None if measure == "count" else pd.to_numeric(filtered["ead"], errors="coerce").fillna(0)
    matrix = pd.crosstab(
        filtered[source_stage],
        filtered["stage"],
        values=values,
        aggfunc="sum" if values is not None else None,
        normalize="index",
        dropna=False,
    ).fillna(0)
    stage_labels = ["Stage 1", "Stage 2", "Stage 3"]
    matrix = matrix.reindex(index=stage_labels, columns=stage_labels, fill_value=0)
    matrix.index.name = "Stage precedent" if source_stage == "previous_stage" else "Stage initial"
    return matrix


def calculate_rating_migration_metrics(
    portfolio: pd.DataFrame,
    source_rating: str = "origination_rating",
) -> dict[str, float | int]:
    """Calculate count- and EAD-based migration indicators."""
    migrations = prepare_rating_migrations(portfolio, source_rating)
    valid = migrations["reference_rating"].notna() & migrations["current_rating"].notna()
    migrations = migrations.loc[valid].copy()
    if migrations.empty:
        return _empty_metrics()

    ead = pd.to_numeric(migrations["ead"], errors="coerce").fillna(0).clip(lower=0)
    total_ead = float(ead.sum())
    types = migrations["rating_migration_type"]
    current = pd.to_numeric(migrations["current_rating"], errors="coerce")
    current_default = types.eq("Migration vers defaut")
    degraded = types.isin(["Degradation 1 cran", "Degradation >= 2 crans", "Migration vers defaut"])
    improved = types.eq("Amelioration")
    stable = types.eq("Stable")
    one_notch = types.eq("Degradation 1 cran")
    two_plus = types.eq("Degradation >= 2 crans")
    worst_grades = degraded & current.ge(WORST_GRADE_THRESHOLD) & ~current_default

    average_change = migrations["rating_change_notches"].where(
        ~current_default,
        11 - migrations["reference_rating"],
    )
    degradation_rate = float(degraded.mean())
    improvement_rate = float(improved.mean())

    return {
        "exposure_count": int(len(migrations)),
        "stability_rate": float(stable.mean()),
        "stability_ead_rate": _ead_rate(ead, stable, total_ead),
        "degradation_rate": degradation_rate,
        "degradation_ead_rate": _ead_rate(ead, degraded, total_ead),
        "one_notch_degradation_rate": float(one_notch.mean()),
        "two_plus_degradation_rate": float(two_plus.mean()),
        "worst_grade_degradation_rate": float(worst_grades.mean()),
        "default_migration_rate": float(current_default.mean()),
        "default_migration_ead_rate": _ead_rate(ead, current_default, total_ead),
        "improvement_rate": improvement_rate,
        "improvement_ead_rate": _ead_rate(ead, improved, total_ead),
        "net_migration_rate": degradation_rate - improvement_rate,
        "average_notch_migration": float(average_change.mean()),
        "strong_migration_count": int(migrations["strong_migration"].sum()),
    }


def build_migration_breakdown(
    portfolio: pd.DataFrame,
    source_rating: str = "origination_rating",
) -> pd.DataFrame:
    """Summarize migration categories in count and EAD."""
    migrations = prepare_rating_migrations(portfolio, source_rating)
    migrations["ead"] = pd.to_numeric(migrations["ead"], errors="coerce").fillna(0).clip(lower=0)
    summary = (
        migrations.groupby("rating_migration_type", as_index=False)
        .agg(exposure_count=("loan_id", "count"), ead=("ead", "sum"))
    )
    total_count = summary["exposure_count"].sum()
    total_ead = summary["ead"].sum()
    summary["exposure_share"] = summary["exposure_count"] / total_count if total_count else 0
    summary["ead_share"] = summary["ead"] / total_ead if total_ead else 0
    return summary.sort_values("exposure_count", ascending=False).reset_index(drop=True)


def build_average_migration_by_dimension(
    portfolio: pd.DataFrame,
    dimension: str = "product_type",
    source_rating: str = "origination_rating",
) -> pd.DataFrame:
    """Calculate average notch migration by portfolio dimension."""
    if dimension not in portfolio.columns:
        raise ValueError(f"Unknown migration dimension: {dimension}")
    migrations = prepare_rating_migrations(portfolio, source_rating)
    current_default = migrations["rating_migration_type"].eq("Migration vers defaut")
    migrations["migration_notches_adjusted"] = migrations["rating_change_notches"].where(
        ~current_default,
        11 - migrations["reference_rating"],
    )
    migrations["ead"] = pd.to_numeric(migrations["ead"], errors="coerce").fillna(0).clip(lower=0)

    def weighted_average(group: pd.DataFrame) -> float:
        valid = group["migration_notches_adjusted"].notna()
        values = group.loc[valid, "migration_notches_adjusted"]
        weights = group.loc[valid, "ead"]
        if values.empty:
            return 0.0
        return float(np.average(values, weights=weights)) if weights.sum() else float(values.mean())

    summary = (
        migrations.groupby(dimension, dropna=False)
        .apply(
            lambda group: pd.Series(
                {
                    "exposure_count": len(group),
                    "average_notch_migration": group["migration_notches_adjusted"].mean(),
                    "ead_weighted_notch_migration": weighted_average(group),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )
    return summary.sort_values("ead_weighted_notch_migration", ascending=False).reset_index(drop=True)


def build_top_strong_migrations(
    portfolio: pd.DataFrame,
    n: int = 10,
    source_rating: str = "origination_rating",
) -> pd.DataFrame:
    """Return the largest adverse rating migrations, prioritizing EAD."""
    migrations = prepare_rating_migrations(portfolio, source_rating)
    migrations["migration_magnitude"] = migrations["rating_change_notches"].abs()
    default_mask = migrations["rating_migration_type"].eq("Migration vers defaut")
    adverse = migrations.loc[
        default_mask | migrations["rating_change_notches"].ge(2)
    ].copy()
    adverse["migration_sort"] = np.where(
        default_mask.loc[adverse.index],
        100 + adverse["reference_rating"],
        adverse["rating_change_notches"],
    )
    columns = [
        "loan_id",
        "client_id",
        "product_type",
        "sector",
        "country",
        "ead",
        "origination_rating",
        "previous_rating",
        "reference_rating",
        "current_rating_bucket",
        "rating_change_notches",
        "rating_migration_type",
        "pd_12m",
        "pd_lifetime",
        "lgd",
        "days_past_due",
        "default_flag",
        "stage",
        "stage_reason",
    ]
    available_columns = [column for column in columns if column in adverse.columns]
    return (
        adverse.sort_values(["migration_sort", "ead"], ascending=[False, False])
        .head(n)[available_columns]
        .reset_index(drop=True)
    )


def _ead_rate(ead: pd.Series, mask: pd.Series, total_ead: float) -> float:
    return float(ead.loc[mask].sum() / total_ead) if total_ead else 0.0


def _format_rating(value: float) -> str:
    return str(int(value)) if pd.notna(value) else "Non renseigne"


def _empty_metrics() -> dict[str, float | int]:
    return {
        "exposure_count": 0,
        "stability_rate": 0.0,
        "stability_ead_rate": 0.0,
        "degradation_rate": 0.0,
        "degradation_ead_rate": 0.0,
        "one_notch_degradation_rate": 0.0,
        "two_plus_degradation_rate": 0.0,
        "worst_grade_degradation_rate": 0.0,
        "default_migration_rate": 0.0,
        "default_migration_ead_rate": 0.0,
        "improvement_rate": 0.0,
        "improvement_ead_rate": 0.0,
        "net_migration_rate": 0.0,
        "average_notch_migration": 0.0,
        "strong_migration_count": 0,
    }
