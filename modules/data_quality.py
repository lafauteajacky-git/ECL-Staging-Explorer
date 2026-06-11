"""Data quality checks for the ECL Staging Explorer MVP."""

from __future__ import annotations

import numpy as np
import pandas as pd


DATA_QUALITY_DIMENSIONS = {
    "MISSING_RATING": "Completude",
    "MISSING_PD": "Completude",
    "MISSING_LGD": "Completude",
    "INVALID_EAD": "Validite",
    "NEGATIVE_MATURITY": "Validite",
    "NEGATIVE_DPD": "Validite",
    "DEFAULT_DPD_INCONSISTENCY": "Coherence",
    "LTV_WITHOUT_COLLATERAL": "Coherence",
}

CRITICAL_QUALITY_CODES = {
    "MISSING_PD",
    "MISSING_LGD",
    "INVALID_EAD",
    "DEFAULT_DPD_INCONSISTENCY",
}

RAW_QUALITY_TEST_COLUMNS = [
    "test_id",
    "dimension",
    "control",
    "field",
    "severity",
    "population_count",
    "exception_count",
    "exception_rate",
    "threshold",
    "status",
    "recommendation",
]

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


def build_quality_dimension_summary(portfolio: pd.DataFrame, findings: pd.DataFrame) -> pd.DataFrame:
    """Summarize existing checks by BCBS 239-inspired data quality dimension."""
    check_counts = pd.Series(DATA_QUALITY_DIMENSIONS).value_counts()
    if findings.empty:
        issue_counts = pd.Series(dtype="int64")
    else:
        issue_counts = (
            findings.assign(dimension=findings["check_code"].map(DATA_QUALITY_DIMENSIONS))
            .dropna(subset=["dimension"])
            .groupby("dimension")
            .size()
        )

    rows = []
    exposure_count = len(portfolio)
    for dimension in ["Completude", "Validite", "Coherence"]:
        control_count = int(check_counts.get(dimension, 0))
        possible_checks = exposure_count * control_count
        issue_count = int(issue_counts.get(dimension, 0))
        score = 100 * (1 - issue_count / possible_checks) if possible_checks else 100.0
        rows.append(
            {
                "dimension": dimension,
                "score": round(max(0.0, score), 2),
                "issue_count": issue_count,
                "control_count": control_count,
                "status": quality_status(score),
            }
        )

    rows.extend(
        [
            {
                "dimension": "Exactitude et integrite",
                "score": calculate_quality_score(portfolio, findings),
                "issue_count": len(findings),
                "control_count": len(DATA_QUALITY_DIMENSIONS),
                "status": quality_status(calculate_quality_score(portfolio, findings)),
            },
            {
                "dimension": "Fraicheur / ponctualite",
                "score": None,
                "issue_count": None,
                "control_count": 0,
                "status": "Non evalue",
            },
        ]
    )
    return pd.DataFrame(rows)


def build_quality_dashboard_metrics(portfolio: pd.DataFrame, findings: pd.DataFrame) -> dict[str, float | int]:
    """Build executive data quality KPIs for the Streamlit dashboard."""
    exposure_count = len(portfolio)
    impacted_loans = findings["loan_id"].nunique() if not findings.empty else 0
    critical_findings = (
        findings.loc[findings["check_code"].isin(CRITICAL_QUALITY_CODES)]
        if not findings.empty
        else findings
    )
    critical_loans = critical_findings["loan_id"].nunique() if not critical_findings.empty else 0
    impacted_ids = set(findings["loan_id"]) if not findings.empty else set()
    impacted_ead = pd.to_numeric(
        portfolio.loc[portfolio["loan_id"].isin(impacted_ids), "ead"],
        errors="coerce",
    ).fillna(0).clip(lower=0).sum()
    total_ead = pd.to_numeric(portfolio["ead"], errors="coerce").fillna(0).clip(lower=0).sum()

    return {
        "quality_score": calculate_quality_score(portfolio, findings),
        "issue_count": int(len(findings)),
        "impacted_exposure_count": int(impacted_loans),
        "impacted_exposure_rate": impacted_loans / exposure_count if exposure_count else 0.0,
        "critical_issue_count": int(len(critical_findings)),
        "critical_exposure_count": int(critical_loans),
        "impacted_ead": float(impacted_ead),
        "impacted_ead_rate": float(impacted_ead / total_ead) if total_ead else 0.0,
    }


def quality_status(score: float) -> str:
    """Return a simple committee-friendly status for a quality score."""
    if score >= 99:
        return "Maitrise"
    if score >= 97:
        return "A surveiller"
    return "Revue requise"


def run_raw_data_quality_tests(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Execute a BCBS 239-inspired test catalogue on the raw portfolio.

    The tests measure observable data properties. Accuracy against an external
    golden source and timeliness against source-system cut-offs remain outside
    the scope of the synthetic MVP.
    """
    if portfolio.empty:
        return pd.DataFrame(columns=RAW_QUALITY_TEST_COLUMNS)

    tests: list[dict] = []
    row_count = len(portfolio)

    def add_test(
        test_id: str,
        dimension: str,
        control: str,
        field: str,
        exception_mask: pd.Series,
        threshold: float = 0.0,
        severity: str = "Warning",
        population_mask: pd.Series | None = None,
        recommendation: str = "Analyser les exceptions et corriger la source avant calcul.",
    ) -> None:
        population = population_mask.fillna(False) if population_mask is not None else pd.Series(True, index=portfolio.index)
        exceptions = exception_mask.fillna(False) & population
        population_count = int(population.sum())
        exception_count = int(exceptions.sum())
        exception_rate = exception_count / population_count if population_count else 0.0
        tests.append(
            {
                "test_id": test_id,
                "dimension": dimension,
                "control": control,
                "field": field,
                "severity": severity,
                "population_count": population_count,
                "exception_count": exception_count,
                "exception_rate": exception_rate,
                "threshold": threshold,
                "status": _test_status(exception_rate, threshold),
                "recommendation": recommendation,
            }
        )

    critical_fields = [
        "loan_id",
        "client_id",
        "product_type",
        "sector",
        "country",
        "ead",
        "origination_rating",
        "current_rating",
        "pd_12m",
        "pd_lifetime",
        "lgd",
        "days_past_due",
        "default_flag",
    ]
    for field in critical_fields:
        add_test(
            f"COMP_{field.upper()}",
            "Completude",
            f"{field} renseigne",
            field,
            portfolio[field].isna(),
            threshold=0.0,
            severity="Critical" if field in {"loan_id", "ead", "pd_12m", "pd_lifetime", "lgd"} else "Warning",
        )

    add_test(
        "UNIQ_LOAN_ID",
        "Unicite",
        "Identifiant de pret unique",
        "loan_id",
        portfolio["loan_id"].duplicated(keep=False),
        severity="Critical",
        recommendation="Garantir une cle primaire unique pour eviter tout double comptage.",
    )
    add_test(
        "UNIQ_FULL_ROW",
        "Unicite",
        "Absence de lignes strictement dupliquees",
        "Toutes colonnes",
        portfolio.duplicated(keep=False),
        severity="Critical",
        recommendation="Identifier la cause du doublon et conserver une seule observation source.",
    )
    add_test(
        "VALID_EAD",
        "Validite",
        "EAD strictement positive",
        "ead",
        pd.to_numeric(portfolio["ead"], errors="coerce").le(0) | pd.to_numeric(portfolio["ead"], errors="coerce").isna(),
        severity="Critical",
    )
    add_test(
        "VALID_PD_12M",
        "Validite",
        "PD 12M comprise entre 0% et 100%",
        "pd_12m",
        ~pd.to_numeric(portfolio["pd_12m"], errors="coerce").between(0, 1, inclusive="both"),
        severity="Critical",
    )
    add_test(
        "VALID_PD_LIFETIME",
        "Validite",
        "PD lifetime comprise entre 0% et 100%",
        "pd_lifetime",
        ~pd.to_numeric(portfolio["pd_lifetime"], errors="coerce").between(0, 1, inclusive="both"),
        severity="Critical",
    )
    add_test(
        "VALID_LGD",
        "Validite",
        "LGD comprise entre 0% et 100%",
        "lgd",
        ~pd.to_numeric(portfolio["lgd"], errors="coerce").between(0, 1, inclusive="both"),
        severity="Critical",
    )
    add_test(
        "VALID_RATING_ORIGINATION",
        "Validite",
        "Rating initial compris entre 1 et 10",
        "origination_rating",
        ~pd.to_numeric(portfolio["origination_rating"], errors="coerce").between(1, 10, inclusive="both"),
    )
    add_test(
        "VALID_RATING_CURRENT",
        "Validite",
        "Rating actuel compris entre 1 et 10",
        "current_rating",
        ~pd.to_numeric(portfolio["current_rating"], errors="coerce").between(1, 10, inclusive="both"),
    )
    add_test(
        "VALID_DPD",
        "Validite",
        "DPD positif ou nul",
        "days_past_due",
        pd.to_numeric(portfolio["days_past_due"], errors="coerce").lt(0),
        severity="Critical",
    )
    add_test(
        "VALID_MATURITY",
        "Validite",
        "Maturite residuelle positive ou nulle",
        "residual_maturity_months",
        pd.to_numeric(portfolio["residual_maturity_months"], errors="coerce").lt(0),
    )
    add_test(
        "VALID_EFFECTIVE_RATE",
        "Validite",
        "Taux d'interet effectif compris entre 0% et 100%",
        "effective_interest_rate",
        ~pd.to_numeric(portfolio["effective_interest_rate"], errors="coerce").between(0, 1, inclusive="both"),
    )
    add_test(
        "VALID_LTV",
        "Validite",
        "LTV comprise entre 0% et 200% lorsqu'elle est renseignee",
        "ltv",
        portfolio["ltv"].notna()
        & ~pd.to_numeric(portfolio["ltv"], errors="coerce").between(0, 2, inclusive="both"),
    )
    add_test(
        "VALID_PRODUCT_DOMAIN",
        "Validite",
        "Type de produit appartenant au referentiel de demonstration",
        "product_type",
        ~portfolio["product_type"].isin(
            ["Mortgage", "SME term loan", "Corporate loan", "Consumer loan", "Credit card"]
        ),
    )
    add_test(
        "VALID_SECTOR_DOMAIN",
        "Validite",
        "Secteur appartenant au referentiel de demonstration",
        "sector",
        ~portfolio["sector"].isin(
            ["Households", "Manufacturing", "Retail", "Real estate", "Technology", "Energy"]
        ),
    )
    add_test(
        "VALID_COUNTRY_DOMAIN",
        "Validite",
        "Pays appartenant au perimetre de demonstration",
        "country",
        ~portfolio["country"].isin(["FR", "DE", "IT", "ES", "BE", "NL"]),
    )
    add_test(
        "VALID_STAGE_DOMAIN",
        "Validite",
        "Stage initial appartenant au referentiel IFRS 9",
        "initial_stage",
        ~portfolio["initial_stage"].isin(["Stage 1", "Stage 2", "Stage 3"]),
    )
    for flag_field in [
        "default_flag",
        "forbearance_flag",
        "watchlist_flag",
        "collateral_flag",
    ]:
        add_test(
            f"VALID_{flag_field.upper()}",
            "Validite",
            f"{flag_field} au format booleen",
            flag_field,
            ~portfolio[flag_field].isin([True, False]),
        )
    if "previous_stage" in portfolio:
        add_test(
            "VALID_PREVIOUS_STAGE",
            "Validite",
            "Stage precedent appartenant au referentiel IFRS 9",
            "previous_stage",
            ~portfolio["previous_stage"].isin(["Stage 1", "Stage 2", "Stage 3"]),
            severity="Critical",
        )
    if "previous_rating" in portfolio:
        add_test(
            "VALID_PREVIOUS_RATING",
            "Validite",
            "Note precedente comprise entre 1 et 10",
            "previous_rating",
            ~pd.to_numeric(portfolio["previous_rating"], errors="coerce").between(
                1,
                10,
                inclusive="both",
            ),
        )
    if "cure_period_months" in portfolio:
        add_test(
            "VALID_CURE_PERIOD",
            "Validite",
            "Anciennete de cure positive ou nulle",
            "cure_period_months",
            pd.to_numeric(portfolio["cure_period_months"], errors="coerce").lt(0),
        )
    if "probation_required_months" in portfolio:
        add_test(
            "VALID_PROBATION_THRESHOLD",
            "Validite",
            "Seuil de probation positif ou nul",
            "probation_required_months",
            pd.to_numeric(portfolio["probation_required_months"], errors="coerce").lt(0),
        )
    add_test(
        "CONSISTENCY_PD_TERM",
        "Coherence",
        "PD lifetime superieure ou egale a la PD 12M",
        "pd_lifetime / pd_12m",
        pd.to_numeric(portfolio["pd_lifetime"], errors="coerce")
        < pd.to_numeric(portfolio["pd_12m"], errors="coerce"),
        severity="Critical",
    )
    add_test(
        "CONSISTENCY_DEFAULT_DPD",
        "Coherence",
        "DPD >= 90 coherent avec le flag de defaut",
        "default_flag / days_past_due",
        pd.to_numeric(portfolio["days_past_due"], errors="coerce").ge(90)
        & ~portfolio["default_flag"].fillna(False).astype(bool),
        severity="Critical",
    )
    add_test(
        "CONSISTENCY_LTV_COLLATERAL",
        "Coherence",
        "LTV renseigne uniquement si collateral present",
        "ltv / collateral_flag",
        portfolio["ltv"].notna() & ~portfolio["collateral_flag"].fillna(False).astype(bool),
    )
    add_test(
        "CONSISTENCY_COLLATERAL_LTV",
        "Coherence",
        "LTV renseigne lorsque collateral present",
        "collateral_flag / ltv",
        portfolio["collateral_flag"].fillna(False).astype(bool) & portfolio["ltv"].isna(),
    )
    add_test(
        "CONSISTENCY_DEFAULT_PD",
        "Coherence",
        "Exposition en defaut avec PD lifetime significative",
        "default_flag / pd_lifetime",
        portfolio["default_flag"].fillna(False).astype(bool)
        & pd.to_numeric(portfolio["pd_lifetime"], errors="coerce").lt(0.50),
        threshold=0.02,
    )

    add_test(
        "INTEGRITY_CLIENT_LOAN_LINK",
        "Exactitude et integrite",
        "Chaque exposition est rattachee a un client",
        "loan_id / client_id",
        portfolio["loan_id"].notna() & portfolio["client_id"].isna(),
        severity="Critical",
        recommendation="Retablir le rattachement entre l'exposition et le referentiel client.",
    )
    add_test(
        "INTEGRITY_RISK_PARAMETERS",
        "Exactitude et integrite",
        "Parametres PD et LGD exploitables simultanement",
        "pd_12m / pd_lifetime / lgd",
        portfolio[["pd_12m", "pd_lifetime", "lgd"]].isna().any(axis=1),
        severity="Critical",
        recommendation="Completer les parametres de risque avant le calcul ECL.",
    )
    tests.append(
        {
            "test_id": "TIMELINESS_REFERENCE_DATE",
            "dimension": "Ponctualite",
            "control": "Fraicheur de la date de reference",
            "field": "reference_date",
            "severity": "Warning",
            "population_count": 0,
            "exception_count": 0,
            "exception_rate": np.nan,
            "threshold": np.nan,
            "status": "Non evalue",
            "recommendation": (
                "Ajouter une date de reference et une date de chargement pour mesurer le respect du cut-off."
            ),
        }
    )

    return pd.DataFrame(tests, columns=RAW_QUALITY_TEST_COLUMNS)


def build_raw_quality_dimension_summary(test_results: pd.DataFrame) -> pd.DataFrame:
    """Aggregate raw test statistics by observable BCBS 239 dimension."""
    if test_results.empty:
        return pd.DataFrame(
            columns=["dimension", "test_count", "failed_test_count", "population_count", "exception_count", "exception_rate", "score"]
        )

    evaluated = test_results.loc[test_results["status"].ne("Non evalue")].copy()
    summary = (
        evaluated.groupby("dimension", as_index=False)
        .agg(
            test_count=("test_id", "count"),
            failed_test_count=("status", lambda values: int((values == "Fail").sum())),
            population_count=("population_count", "sum"),
            exception_count=("exception_count", "sum"),
        )
    )
    summary["exception_rate"] = np.where(
        summary["population_count"] > 0,
        summary["exception_count"] / summary["population_count"],
        0.0,
    )
    summary["score"] = (1 - summary["exception_rate"]).clip(lower=0) * 100
    summary["status"] = summary["score"].map(quality_status)
    non_evaluated = test_results.loc[test_results["status"].eq("Non evalue"), "dimension"].drop_duplicates()
    if not non_evaluated.empty:
        summary = pd.concat(
            [
                summary,
                pd.DataFrame(
                    {
                        "dimension": non_evaluated,
                        "test_count": 0,
                        "failed_test_count": 0,
                        "population_count": 0,
                        "exception_count": 0,
                        "exception_rate": np.nan,
                        "score": np.nan,
                        "status": "Non evalue",
                    }
                ),
            ],
            ignore_index=True,
        )
    return summary.sort_values("score", na_position="last").reset_index(drop=True)


def build_raw_quality_metrics(portfolio: pd.DataFrame, test_results: pd.DataFrame) -> dict[str, float | int]:
    """Build KPIs from the raw-data control catalogue."""
    evaluated = test_results.loc[test_results["status"].ne("Non evalue")]
    failed = evaluated.loc[evaluated["status"].eq("Fail")]
    critical_failed = failed.loc[failed["severity"].eq("Critical")]
    test_count = len(evaluated)
    passed_count = int(evaluated["status"].eq("Pass").sum())

    return {
        "row_count": int(len(portfolio)),
        "column_count": int(len(portfolio.columns)),
        "test_count": int(test_count),
        "passed_test_count": passed_count,
        "failed_test_count": int(len(failed)),
        "critical_failed_test_count": int(len(critical_failed)),
        "test_pass_rate": passed_count / test_count if test_count else 1.0,
        "exception_count": int(failed["exception_count"].sum()),
    }


def build_raw_column_profile(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Return standard descriptive statistics for each raw portfolio field."""
    rows = []
    for column in portfolio.columns:
        series = portfolio[column]
        numeric = pd.to_numeric(series, errors="coerce")
        is_numeric = pd.api.types.is_numeric_dtype(series) or numeric.notna().sum() >= len(series) * 0.95
        row = {
            "field": column,
            "dtype": str(series.dtype),
            "row_count": len(series),
            "missing_count": int(series.isna().sum()),
            "missing_rate": float(series.isna().mean()),
            "distinct_count": int(series.nunique(dropna=True)),
            "distinct_rate": float(series.nunique(dropna=True) / len(series)) if len(series) else 0.0,
            "minimum": float(numeric.min()) if is_numeric and numeric.notna().any() else None,
            "median": float(numeric.median()) if is_numeric and numeric.notna().any() else None,
            "mean": float(numeric.mean()) if is_numeric and numeric.notna().any() else None,
            "maximum": float(numeric.max()) if is_numeric and numeric.notna().any() else None,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def _test_status(exception_rate: float, threshold: float) -> str:
    return "Pass" if exception_rate <= threshold else "Fail"
