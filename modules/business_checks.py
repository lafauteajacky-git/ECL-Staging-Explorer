"""Business consistency checks for the ECL Staging Explorer demo.

These checks are simple plausibility controls designed for committee discussion.
They do not replace model validation, accounting policy controls or production
IFRS 9 governance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


CHECK_COUNT = 10
CRITICAL_SEVERITY = "Critical"
WARNING_SEVERITY = "Warning"
INFO_SEVERITY = "Info"


DEMO_STORYLINE = [
    {"step": 1, "title": "Portefeuille synthetique", "description": "Choisir un profil de demo et generer un portefeuille 100% fictif."},
    {"step": 2, "title": "Data quality", "description": "Identifier les anomalies susceptibles de fragiliser le calcul."},
    {"step": 3, "title": "Staging IFRS 9", "description": "Appliquer des regles simples, explicables et auditables Stage 1 / Stage 2 / Stage 3."},
    {"step": 4, "title": "Calcul ECL", "description": "Calculer les pertes attendues selon une formule pedagogique par stage."},
    {"step": 5, "title": "Scenarios macro et overlays", "description": "Simuler l'impact des hypotheses macro et des ajustements manageriaux."},
    {"step": 6, "title": "Audit trail et note comite", "description": "Restituer les hypotheses, alertes, messages clefs et exports de gouvernance."},
]


PROFILE_CONTEXT = {
    "Balanced Portfolio": "Profil equilibre pour illustrer le parcours de bout en bout.",
    "Low Risk Portfolio": "Profil prudent avec faible migration et taux de couverture limite.",
    "Deteriorated Portfolio": "Profil degrade pour illustrer migration Stage 2/3, hausse ECL et concentration des risques.",
    "Data Quality Issues Portfolio": "Profil oriente controles, anomalies et prudence methodologique.",
    "CRE Stress Portfolio": "Profil concentre immobilier commercial pour illustrer stress sectoriel et overlays.",
}


def run_business_consistency_checks(ecl_portfolio: pd.DataFrame) -> pd.DataFrame:
    """Run simple business plausibility checks on calculated results."""
    alerts: list[dict] = []

    _append_alerts(
        alerts,
        ecl_portfolio,
        _stage(ecl_portfolio, "Stage 1") & (_bool_col(ecl_portfolio, "default_flag") | (_num_col(ecl_portfolio, "days_past_due") >= 90)),
        CRITICAL_SEVERITY,
        "STAGE1_DEFAULT_OR_90DPD",
        "Stage 1 avec defaut ou DPD >= 90",
        "Revoir le staging et les indicateurs de defaut.",
        "Risque de sous-estimation de l'ECL et de classification incorrecte.",
    )
    _append_alerts(
        alerts,
        ecl_portfolio,
        _stage(ecl_portfolio, "Stage 1") & _bool_col(ecl_portfolio, "forbearance_flag"),
        WARNING_SEVERITY,
        "STAGE1_FORBEARANCE",
        "Stage 1 avec forbearance actif",
        "Verifier si un transfert Stage 2 est requis par la politique SICR.",
        "Risque de sous-estimation de l'augmentation significative du risque de credit.",
    )
    _append_alerts(
        alerts,
        ecl_portfolio,
        _stage(ecl_portfolio, "Stage 1") & _bool_col(ecl_portfolio, "watchlist_flag"),
        WARNING_SEVERITY,
        "STAGE1_WATCHLIST",
        "Stage 1 avec watchlist actif",
        "Verifier la coherence entre watchlist et staging.",
        "Signal de risque potentiellement non reflete dans le stage.",
    )
    _append_alerts(
        alerts,
        ecl_portfolio,
        _stage(ecl_portfolio, "Stage 2") & ~_has_stage2_trigger(ecl_portfolio),
        WARNING_SEVERITY,
        "STAGE2_WITHOUT_CLEAR_TRIGGER",
        "Stage 2 sans justification claire",
        "Revoir la regle declenchante et le commentaire metier.",
        "Risque de manque d'explicabilite en comite ou audit.",
    )
    _append_alerts(
        alerts,
        ecl_portfolio,
        _stage(ecl_portfolio, "Stage 3") & ~(_bool_col(ecl_portfolio, "default_flag") | (_num_col(ecl_portfolio, "days_past_due") >= 90)),
        CRITICAL_SEVERITY,
        "STAGE3_WITHOUT_DEFAULT_TRIGGER",
        "Stage 3 sans defaut, DPD >= 90 ou indicateur de depreciation",
        "Confirmer l'existence d'un indicateur de defaut ou de depreciation.",
        "Risque de surclassement Stage 3 ou de documentation insuffisante.",
    )
    _append_alerts(
        alerts,
        ecl_portfolio,
        _num_col(ecl_portfolio, "pd_lifetime") < _num_col(ecl_portfolio, "pd_12m"),
        WARNING_SEVERITY,
        "LIFETIME_PD_BELOW_12M_PD",
        "PD lifetime inferieure a la PD 12M",
        "Verifier la coherence de la courbe de probabilite de defaut.",
        "Risque de sous-estimation de l'ECL Stage 2.",
    )
    _append_alerts(
        alerts,
        ecl_portfolio,
        (_num_col(ecl_portfolio, "lgd") < 0) | (_num_col(ecl_portfolio, "lgd") > 1),
        CRITICAL_SEVERITY,
        "INVALID_LGD_RANGE",
        "LGD superieure a 100% ou negative",
        "Corriger ou justifier la LGD avant usage des resultats.",
        "Parametre de risque invalide pouvant fausser l'ECL.",
    )
    _append_alerts(
        alerts,
        ecl_portfolio,
        (_num_col(ecl_portfolio, "pd_12m") < 0)
        | (_num_col(ecl_portfolio, "pd_12m") > 1)
        | (_num_col(ecl_portfolio, "pd_lifetime") < 0)
        | (_num_col(ecl_portfolio, "pd_lifetime") > 1),
        CRITICAL_SEVERITY,
        "INVALID_PD_RANGE",
        "PD superieure a 100% ou negative",
        "Corriger ou justifier les PD avant usage des resultats.",
        "Parametre de risque invalide pouvant fausser l'ECL.",
    )
    _append_alerts(
        alerts,
        ecl_portfolio,
        _num_col(ecl_portfolio, "ecl") < 0,
        CRITICAL_SEVERITY,
        "NEGATIVE_ECL",
        "ECL negative",
        "Verifier les inputs EAD, PD, LGD et les formules de calcul.",
        "Resultat economiquement incoherent.",
    )
    _append_alerts(
        alerts,
        ecl_portfolio,
        (_num_col(ecl_portfolio, "ead") > 0) & ((_num_col(ecl_portfolio, "ecl") / _num_col(ecl_portfolio, "ead")) > 0.50),
        WARNING_SEVERITY,
        "HIGH_ECL_TO_EAD",
        "ECL tres elevee par rapport a l'EAD",
        "Revoir les expositions a fort taux de couverture.",
        "Risque de concentration ou de parametre tres conservateur.",
    )
    _append_alerts(
        alerts,
        ecl_portfolio,
        (_num_col(ecl_portfolio, "current_rating") < _num_col(ecl_portfolio, "origination_rating"))
        & ecl_portfolio.get("stage", pd.Series("", index=ecl_portfolio.index)).isin(["Stage 2", "Stage 3"]),
        INFO_SEVERITY,
        "IMPROVED_RATING_WITH_STAGE2_OR_3",
        "Rating actuel meilleur que le rating initial avec Stage 2 ou Stage 3",
        "Verifier si d'autres indicateurs justifient le stage.",
        "Point d'explicabilite pour le comite.",
    )

    columns = ["loan_id", "severity", "check_code", "rule", "recommendation", "potential_impact"]
    return pd.DataFrame(alerts, columns=columns)


def summarize_business_consistency(alerts: pd.DataFrame, exposure_count: int, check_count: int = CHECK_COUNT) -> dict[str, float]:
    """Build a simple business consistency score."""
    total_possible_checks = int(exposure_count * check_count)
    alert_count = int(len(alerts))
    critical_count = int((alerts["severity"] == CRITICAL_SEVERITY).sum()) if not alerts.empty else 0
    passed_checks = max(total_possible_checks - alert_count, 0)
    score = passed_checks / total_possible_checks if total_possible_checks else 1.0
    return {
        "business_checks_passed": passed_checks,
        "business_alert_count": alert_count,
        "business_critical_alert_count": critical_count,
        "business_consistency_score": score,
    }


def build_client_discussion_points(
    demo_profile: str,
    business_summary: dict[str, float],
    metrics: dict[str, float],
    scenario_metrics: dict[str, float],
    overlay_metrics: dict[str, float | str],
) -> list[str]:
    """Generate five client discussion points adapted to the selected demo profile."""
    profile_point = {
        "Low Risk Portfolio": "Le faible taux de couverture observe est-il coherent avec l'appetit au risque et la politique SICR ?",
        "Deteriorated Portfolio": "Les migrations Stage 2/3 et la concentration des risques correspondent-elles aux signaux de deterioration attendus ?",
        "Data Quality Issues Portfolio": "Les anomalies de donnees ont-elles un impact materiel sur les provisions et le pilotage comite ?",
        "CRE Stress Portfolio": "La concentration immobilier commercial justifie-t-elle un suivi sectoriel ou un overlay dedie ?",
    }.get(demo_profile, "Les seuils SICR actuels refletent-ils bien la politique de risque du portefeuille ?")

    score_pct = business_summary.get("business_consistency_score", 1.0)
    overlay_pct = overlay_metrics.get("overlay_variation_pct", 0.0)
    weighted_pct = scenario_metrics.get("weighted_impact_pct", 0.0)

    return [
        profile_point,
        "Les overlays appliques sont-ils suffisamment documentes, gouvernes et rattaches a une justification metier ?",
        f"Le score de coherence metier de {score_pct:.1%} est-il acceptable pour une restitution comite ?",
        f"L'impact des scenarios macro ({weighted_pct:.2%}) et des overlays ({overlay_pct:.2%}) est-il suffisamment explique ?",
        "Les resultats sont-ils suffisamment transparents pour un comite provisionnement, les risques, la finance et l'audit interne ?",
    ]


def build_profile_insights(demo_profile: str, metrics: dict[str, float], overlay_metrics: dict[str, float | str]) -> list[str]:
    """Build profile-specific management insights for the demo narrative."""
    if demo_profile == "Low Risk Portfolio":
        return [
            "Profil Low Risk : le portefeuille illustre une faible migration Stage 2/3 et un taux de couverture limite.",
            "Le cas de demonstration permet de discuter la sensibilite des seuils SICR sur un portefeuille sain.",
        ]
    if demo_profile == "Deteriorated Portfolio":
        return [
            "Profil Deteriorated : la hausse des expositions Stage 2/3 met en evidence la migration du risque.",
            "La concentration des ECL facilite une discussion sur les segments a prioriser en revue.",
        ]
    if demo_profile == "Data Quality Issues Portfolio":
        return [
            "Profil Data Quality Issues : les anomalies renforcent le besoin de controles avant interpretation des ECL.",
            "La prudence methodologique est clef lorsque des donnees critiques sont manquantes ou incoherentes.",
        ]
    if demo_profile == "CRE Stress Portfolio":
        return [
            "Profil CRE Stress : la concentration immobilier commercial met en evidence l'interet d'un stress sectoriel.",
            f"Le top overlay contributeur est {overlay_metrics.get('top_overlay_contributor', 'non disponible')}.",
        ]
    return [PROFILE_CONTEXT.get(demo_profile, "Profil de demonstration synthetique.")]


def storyline_to_frame() -> pd.DataFrame:
    """Return the demo storyline as an export-ready table."""
    return pd.DataFrame(DEMO_STORYLINE)


def discussion_points_to_frame(points: list[str]) -> pd.DataFrame:
    """Return client discussion points as an export-ready table."""
    return pd.DataFrame({"discussion_point": points})


def _append_alerts(
    alerts: list[dict],
    df: pd.DataFrame,
    mask: pd.Series,
    severity: str,
    check_code: str,
    rule: str,
    recommendation: str,
    potential_impact: str,
) -> None:
    for _, row in df.loc[mask.fillna(False)].iterrows():
        alerts.append(
            {
                "loan_id": row.get("loan_id", ""),
                "severity": severity,
                "check_code": check_code,
                "rule": rule,
                "recommendation": recommendation,
                "potential_impact": potential_impact,
            }
        )


def _stage(df: pd.DataFrame, stage: str) -> pd.Series:
    return df.get("stage", pd.Series("", index=df.index)).eq(stage)


def _bool_col(df: pd.DataFrame, column: str) -> pd.Series:
    return df.get(column, pd.Series(False, index=df.index)).fillna(False).astype(bool)


def _num_col(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df.get(column, pd.Series(np.nan, index=df.index)), errors="coerce")


def _has_stage2_trigger(df: pd.DataFrame) -> pd.Series:
    stage_reason = df.get("stage_reason", pd.Series("", index=df.index)).fillna("").astype(str).str.lower()
    explicit_reason = stage_reason.str.contains("dpd|rating|forbearance|watchlist|30|sicr")
    calculated_reason = (
        (_num_col(df, "days_past_due") >= 30)
        | ((_num_col(df, "current_rating") - _num_col(df, "origination_rating")) >= 2)
        | _bool_col(df, "forbearance_flag")
        | _bool_col(df, "watchlist_flag")
    )
    return explicit_reason | calculated_reason
