"""Data quality checks for the ECL Staging Explorer MVP."""

from __future__ import annotations

import pandas as pd


REQUIRED_PORTFOLIO_COLUMNS = [
    "loan_id",
    "client_id",
    "product_type",
    "sector",
    "country",
    "ead",
    "effective_interest_rate",
    "residual_maturity_months",
    "origination_rating",
    "current_rating",
    "pd_12m",
    "pd_lifetime",
    "lgd",
    "days_past_due",
    "default_flag",
    "forbearance_flag",
    "watchlist_flag",
    "collateral_flag",
    "ltv",
    "initial_stage",
]


def missing_required_columns(portfolio: pd.DataFrame) -> list[str]:
    """Return required MVP columns missing from the input portfolio."""
    return [column for column in REQUIRED_PORTFOLIO_COLUMNS if column not in portfolio.columns]


def run_data_quality_checks(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Return row-level quality findings for the input portfolio."""
    checks = [
        ("MISSING_RATING", portfolio["current_rating"].isna() | portfolio["origination_rating"].isna(), "Rating manquant"),
        ("MISSING_PD", portfolio["pd_12m"].isna() | portfolio["pd_lifetime"].isna(), "PD manquante"),
        ("MISSING_LGD", portfolio["lgd"].isna(), "LGD manquante"),
        ("INVALID_EAD", portfolio["ead"].isna() | (portfolio["ead"] <= 0), "EAD negative ou nulle"),
        ("NEGATIVE_MATURITY", portfolio["residual_maturity_months"] < 0, "Maturite negative"),
        ("NEGATIVE_DPD", portfolio["days_past_due"] < 0, "DPD negatif"),
        (
            "DEFAULT_DPD_INCONSISTENCY",
            (portfolio["days_past_due"] >= 90) & (~portfolio["default_flag"].fillna(False)),
            "Defaut incoherent avec DPD superieur ou egal a 90 jours",
        ),
        (
            "LTV_WITHOUT_COLLATERAL",
            portfolio["ltv"].notna() & (~portfolio["collateral_flag"].fillna(False)),
            "LTV renseigne sans collateral",
        ),
    ]

    findings = []
    for code, mask, description in checks:
        impacted = portfolio.loc[mask.fillna(False), ["loan_id"]].copy()
        impacted["check_code"] = code
        impacted["description"] = description
        findings.append(impacted)

    if not findings:
        return pd.DataFrame(columns=["loan_id", "check_code", "description"])

    return pd.concat(findings, ignore_index=True).sort_values(["loan_id", "check_code"]).reset_index(drop=True)


def calculate_quality_score(portfolio: pd.DataFrame, findings: pd.DataFrame) -> float:
    """Calculate a simple data quality score from 0 to 100."""
    if portfolio.empty:
        return 100.0

    total_possible_checks = len(portfolio) * 8
    score = 100 * (1 - (len(findings) / total_possible_checks))
    return round(max(0.0, score), 2)


def run_quality_assessment(portfolio: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """Return detailed findings, aggregated findings and a simple quality score."""
    findings = run_data_quality_checks(portfolio)
    summary = summarize_quality_findings(findings)
    score = calculate_quality_score(portfolio, findings)
    return findings, summary, score


def summarize_quality_findings(findings: pd.DataFrame) -> pd.DataFrame:
    """Aggregate quality findings by check code."""
    if findings.empty:
        return pd.DataFrame(columns=["check_code", "description", "issue_count"])

    return (
        findings.groupby(["check_code", "description"], as_index=False)
        .size()
        .rename(columns={"size": "issue_count"})
        .sort_values("issue_count", ascending=False)
        .reset_index(drop=True)
    )
