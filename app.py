"""Streamlit interface for the ECL Staging Explorer MVP."""

from __future__ import annotations

from datetime import datetime
from html import escape
from textwrap import dedent

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.audit_trail import APP_VERSION, build_audit_trail, generate_run_id
from modules.business_checks import (
    DEMO_STORYLINE,
    PROFILE_CONTEXT,
    build_client_discussion_points,
    build_profile_insights,
    discussion_points_to_frame,
    run_business_consistency_checks,
    storyline_to_frame,
    summarize_business_consistency,
)
from modules.calculation_utils import safe_divide
from modules.committee_summary import build_docx_bytes, generate_committee_summary
from modules.data_quality import (
    build_raw_column_profile,
    build_raw_quality_dimension_summary,
    build_raw_quality_metrics,
    missing_required_columns,
    run_data_quality_checks,
    run_raw_data_quality_tests,
    summarize_quality_findings,
)
from modules.data_types import coerce_boolean_series
from modules.demo_config import APP_NAME, DEMO_DISCLAIMER_FR, EXPORT_FILE_PREFIX
from modules.ecl_calculator import calculate_ecl
from modules.lgd_engine import (
    LGD_METHOD,
    aggregate_lgd_by_dimension,
    build_lgd_sensitivity,
    build_lgd_waterfall,
    calculate_lgd,
    summarize_lgd,
)
from modules.migration_analysis import (
    build_average_migration_by_dimension,
    build_migration_breakdown,
    build_rating_transition_matrix,
    build_stage_transition_matrix,
    build_top_strong_migrations,
    calculate_rating_migration_metrics,
)
from modules.overlay_engine import (
    PREDEFINED_OVERLAYS,
    apply_overlays,
    build_overlay_insights,
    build_overlay_metrics,
    build_overlay_waterfall,
    overlay_config_to_frame,
)
from modules.reporting import (
    aggregate_ecl_by_dimension,
    aggregate_ecl_by_stage,
    build_audit_view,
    build_dashboard_metrics,
    build_dashboard_summary_table,
    build_excel_export_bytes,
    build_management_insights,
    build_migration_matrix,
    build_review_flags,
    build_top_ecl_contributors,
    export_results_to_excel,
)
from modules.risk_parameters import (
    LIFETIME_PD_METHOD,
    aggregate_lifetime_pd_curve,
    build_lifetime_pd_term_structure,
    summarize_risk_parameters,
)
from modules.sample_data import (
    DATA_QUALITY_LEVEL_DESCRIPTIONS,
    DATA_QUALITY_LEVELS,
    DEMO_PORTFOLIO_PROFILES,
    ensure_staging_transition_context,
    generate_demo_portfolio,
)
from modules.scenario_engine import (
    DEFAULT_SCENARIOS,
    build_scenario_insights,
    calculate_all_scenarios,
    calculate_downside_impact_by_stage,
    calculate_weighted_ecl_summary,
    scenario_config_to_frame,
    validate_scenario_weights,
)
from modules.staging_engine import assign_stage
from ui.branding import render_brand_header
from ui.components import (
    format_compact_currency,
    format_currency,
    render_governance_card,
    render_kpi_card,
    render_kpi_panel,
    render_light_kpi_panel,
)
from ui.theme import apply_auria_theme


st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="expanded")


@st.cache_data
def load_synthetic_portfolio(
    n_exposures: int,
    seed: int,
    demo_profile: str,
    data_quality_level: str,
) -> pd.DataFrame:
    """Cache synthetic generation for a smoother demo experience."""
    transition_schema_version = "staging-cure-v1"
    return generate_demo_portfolio(
        profile=demo_profile,
        n_exposures=n_exposures,
        seed=seed,
        data_quality_level=data_quality_level,
    ).assign(_transition_schema_version=transition_schema_version).drop(
        columns="_transition_schema_version"
    )


def default_demo_parameters() -> dict:
    """Return a fresh copy of the default demonstration settings."""
    return {
        "source": "Generer un portefeuille synthetique",
        "demo_profile": "Balanced Portfolio",
        "data_quality_level": DATA_QUALITY_LEVELS[0],
        "n_exposures": 1_000,
        "seed": 42,
        "scenario_config": {
            scenario: dict(values) for scenario, values in DEFAULT_SCENARIOS.items()
        },
        "enabled_overlays": [overlay["name"] for overlay in PREDEFINED_OVERLAYS],
    }


def get_persisted_demo_parameters() -> dict:
    """Return settings stored independently from temporary Streamlit widgets."""
    if "persisted_demo_parameters" not in st.session_state:
        st.session_state["persisted_demo_parameters"] = default_demo_parameters()
    return st.session_state["persisted_demo_parameters"]


def restore_demo_widget_state(parameters: dict) -> None:
    """Restore widget keys after Streamlit removed widgets on another page."""
    widget_values = {
        "demo_profile_control": parameters["demo_profile"],
        "demo_data_quality_level": parameters["data_quality_level"],
        "demo_exposure_count": parameters["n_exposures"],
        "demo_seed": parameters["seed"],
        "demo_enabled_overlays": parameters["enabled_overlays"],
    }
    for scenario, values in parameters["scenario_config"].items():
        widget_values[f"{scenario.lower()}_weight"] = values["weight"] * 100
        widget_values[f"{scenario.lower()}_pd_multiplier"] = values["pd_multiplier"]
        widget_values[f"{scenario.lower()}_lgd_multiplier"] = values["lgd_multiplier"]
    for key, value in widget_values.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_demo_parameters() -> None:
    """Reset persisted settings and force regeneration of the default portfolio."""
    defaults = default_demo_parameters()
    st.session_state["persisted_demo_parameters"] = defaults
    widget_keys = [
        "demo_profile_control",
        "demo_data_quality_level",
        "demo_exposure_count",
        "demo_seed",
        "demo_enabled_overlays",
    ]
    for scenario in DEFAULT_SCENARIOS:
        widget_keys.extend(
            [
                f"{scenario.lower()}_weight",
                f"{scenario.lower()}_pd_multiplier",
                f"{scenario.lower()}_lgd_multiplier",
            ]
        )
    for key in widget_keys:
        st.session_state.pop(key, None)
    for key in [
        "portfolio",
        "demo_profile",
        "data_quality_level",
        "portfolio_generation_summary",
        "run_datetime",
        "run_id",
    ]:
        st.session_state.pop(key, None)


def render_demo_parameters():
    """Render all demo controls in the main home page."""
    parameters = get_persisted_demo_parameters()
    restore_demo_widget_state(parameters)

    title_col, reset_col = st.columns([4, 1])
    with title_col:
        st.markdown("### Parametres de la demonstration")
    with reset_col:
        st.button(
            "Reinitialiser",
            on_click=reset_demo_parameters,
            help="Restaurer tous les parametres et regenerer le portefeuille par defaut.",
            use_container_width=True,
        )
    st.caption("Configurez le portefeuille, les hypotheses macroeconomiques et les overlays avant d'explorer les resultats.")

    with st.expander("1. Portefeuille de demonstration", expanded=True):
        source = "Generer un portefeuille synthetique"
        st.info(
            "Source unique : portefeuille 100 % synthetique genere par le demonstrateur. "
            "L'import de donnees externes est desactive dans la V1."
        )
        portfolio_col1, portfolio_col2 = st.columns(2)
        with portfolio_col1:
            demo_profile = st.selectbox(
                "Demo Portfolio Profile",
                DEMO_PORTFOLIO_PROFILES,
                key="demo_profile_control",
            )
            st.caption(PROFILE_CONTEXT.get(demo_profile, "Profil de demonstration synthetique."))
        with portfolio_col2:
            n_exposures = st.slider(
                "Nombre d'expositions",
                min_value=100,
                max_value=5_000,
                step=100,
                key="demo_exposure_count",
            )
            seed = st.number_input("Seed aleatoire", min_value=1, step=1, key="demo_seed")

        data_quality_level = st.select_slider(
            "Niveau de qualite des donnees",
            options=DATA_QUALITY_LEVELS,
            key="demo_data_quality_level",
        )
        st.caption(DATA_QUALITY_LEVEL_DESCRIPTIONS[data_quality_level])

        generate_clicked = st.button(
            "Generer le portefeuille synthetique",
            type="primary",
        )
        generated_summary = st.session_state.get("portfolio_generation_summary", {})
        if generated_summary:
            pending_changes = (
                generated_summary.get("profile") != demo_profile
                or int(generated_summary.get("requested_exposures", 0)) != int(n_exposures)
                or int(generated_summary.get("seed", 0)) != int(seed)
                or generated_summary.get("data_quality_level") != data_quality_level
            )
            if pending_changes:
                st.warning(
                    "Les parametres affiches different du portefeuille actif. "
                    "Cliquez sur le bouton pour generer un nouveau portefeuille."
                )

    with st.expander("2. Scenarios macroeconomiques", expanded=False):
        scenario_config = build_scenario_controls()

    with st.expander("3. Overlays manageriaux", expanded=False):
        enabled_overlays = st.multiselect(
            "Overlays actifs",
            options=[overlay["name"] for overlay in PREDEFINED_OVERLAYS],
            key="demo_enabled_overlays",
        )

    st.session_state["persisted_demo_parameters"] = {
        "source": source,
        "demo_profile": demo_profile,
        "data_quality_level": data_quality_level,
        "n_exposures": int(n_exposures),
        "seed": int(seed),
        "scenario_config": {
            scenario: dict(values) for scenario, values in scenario_config.items()
        },
        "enabled_overlays": list(enabled_overlays),
    }

    return (
        source,
        demo_profile,
        data_quality_level,
        n_exposures,
        seed,
        generate_clicked,
        scenario_config,
        enabled_overlays,
    )


def load_demo_parameters_from_state():
    """Load persisted demo settings when controls are not rendered."""
    parameters = get_persisted_demo_parameters()
    source = parameters["source"]
    demo_profile = parameters["demo_profile"]
    data_quality_level = parameters["data_quality_level"]
    n_exposures = int(parameters["n_exposures"])
    seed = int(parameters["seed"])
    scenario_config = {
        scenario: dict(values)
        for scenario, values in parameters["scenario_config"].items()
    }
    enabled_overlays = list(parameters["enabled_overlays"])
    return (
        source,
        demo_profile,
        data_quality_level,
        n_exposures,
        seed,
        scenario_config,
        enabled_overlays,
    )


def render_active_demo_context(
    source: str,
    demo_profile: str,
    data_quality_level: str,
    portfolio: pd.DataFrame,
) -> None:
    """Render the active demonstration context on every application page."""
    generation = st.session_state.get("portfolio_generation_summary", {})
    source_label = "Portefeuille synthetique"
    source_detail = "Generation reproductible"

    exposure_count = f"{len(portfolio):,}".replace(",", " ")
    trace_items = []
    if generation.get("generated_at"):
        trace_items.append(f"Genere le {generation['generated_at']}")
    if generation.get("seed") is not None:
        trace_items.append(f"Seed {generation['seed']}")
    if generation.get("run_id"):
        trace_items.append(str(generation["run_id"]))
    trace_line = " | ".join(trace_items) or "Contexte conserve pendant toute la session"

    st.markdown(
        f"""
        <section style="
            margin: 16px 0 24px;
            padding: 18px 20px 14px;
            border: 1px solid rgba(11,43,70,0.16);
            border-left: 5px solid #f1a986;
            border-radius: 14px;
            background: linear-gradient(105deg, rgba(11,43,70,0.98), rgba(23,72,102,0.96));
            box-shadow: 0 14px 32px rgba(11,43,70,0.10);
            color: #ffffff;
        ">
            <div style="
                margin-bottom: 12px;
                color: #f1a986;
                font-size: 0.72rem;
                font-weight: 900;
                letter-spacing: 0.09em;
                text-transform: uppercase;
            ">Contexte actif de la demonstration</div>
            <div style="
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 12px;
            ">
                <div style="padding-right:12px;border-right:1px solid rgba(255,255,255,0.16);">
                    <div style="font-size:0.68rem;color:rgba(255,255,255,0.65);text-transform:uppercase;font-weight:800;">
                        1. Source du portefeuille
                    </div>
                    <div style="margin-top:5px;font-size:1rem;font-weight:850;">{escape(source_label)}</div>
                    <div style="font-size:0.76rem;color:rgba(255,255,255,0.72);">{escape(source_detail)}</div>
                </div>
                <div style="padding-right:12px;border-right:1px solid rgba(255,255,255,0.16);">
                    <div style="font-size:0.68rem;color:rgba(255,255,255,0.65);text-transform:uppercase;font-weight:800;">
                        2. Profil du portefeuille
                    </div>
                    <div style="margin-top:5px;font-size:1rem;font-weight:850;">{escape(demo_profile)}</div>
                    <div style="font-size:0.76rem;color:rgba(255,255,255,0.72);">Profil de risque simule</div>
                </div>
                <div style="padding-right:12px;border-right:1px solid rgba(255,255,255,0.16);">
                    <div style="font-size:0.68rem;color:rgba(255,255,255,0.65);text-transform:uppercase;font-weight:800;">
                        3. Nombre d'expositions
                    </div>
                    <div style="margin-top:5px;font-size:1rem;font-weight:850;">{exposure_count}</div>
                    <div style="font-size:0.76rem;color:rgba(255,255,255,0.72);">Lignes analysees</div>
                </div>
                <div>
                    <div style="font-size:0.68rem;color:rgba(255,255,255,0.65);text-transform:uppercase;font-weight:800;">
                        4. Qualite des donnees
                    </div>
                    <div style="margin-top:5px;font-size:1rem;font-weight:850;">{escape(data_quality_level)}</div>
                    <div style="font-size:0.76rem;color:rgba(255,255,255,0.72);">Niveau synthetique selectionne</div>
                </div>
            </div>
            <div style="
                margin-top: 13px;
                padding-top: 10px;
                border-top: 1px solid rgba(255,255,255,0.14);
                color: rgba(255,255,255,0.62);
                font-size: 0.72rem;
            ">{escape(trace_line)}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    apply_auria_theme()

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-actions">
                <a href="https://ecl-explorer-demo.streamlit.app/" target="_blank" title="Ouvrir et partager l'application">Partager</a>
                <a href="https://github.com/lafauteajacky-git/ECL-Staging-Explorer" target="_blank" title="Consulter le depot GitHub">GitHub</a>
                <a href="https://auria-advisory.fr/" target="_blank" title="Consulter le site Auria Advisory">Auria</a>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.header("Navigation")
        selected_page = st.radio(
            "Navigation principale",
            [
                "Accueil",
                "Portefeuille",
                "Data Quality",
                "Parametres de risque",
                "Staging",
                "ECL Calculation",
                "Macro Scenarios",
                "Management Overlays",
                "Dashboard",
                "Audit Trail",
                "Committee Summary",
                "Export",
            ],
            label_visibility="collapsed",
            key="main_navigation",
        )
        st.caption("Selectionnez une rubrique pour afficher son contenu.")

    render_brand_header(
        st.session_state.get("run_id"),
        compact=selected_page != "Accueil",
    )

    if selected_page == "Accueil":
        render_home_introduction()
        source, demo_profile, data_quality_level, n_exposures, seed, generate_clicked, scenario_config, enabled_overlays = (
            render_demo_parameters()
        )
    else:
        source, demo_profile, data_quality_level, n_exposures, seed, scenario_config, enabled_overlays = (
            load_demo_parameters_from_state()
        )
        generate_clicked = False

    portfolio_requires_transition_upgrade = (
        "portfolio" in st.session_state
        and "previous_stage" not in st.session_state["portfolio"].columns
    )
    required_risk_parameter_columns = {
        "pd_lifetime_method",
        "lgd_method",
        "collateral_type",
        "collateral_value",
        "collateral_haircut",
        "liquidation_cost_rate",
        "unsecured_recovery_rate",
        "recovery_delay_months",
        "recovery_cost_amount",
        "seniority",
    }
    portfolio_requires_risk_upgrade = (
        "portfolio" in st.session_state
        and not required_risk_parameter_columns.issubset(
            st.session_state["portfolio"].columns
        )
    )
    if (
        generate_clicked
        or "portfolio" not in st.session_state
        or portfolio_requires_transition_upgrade
        or portfolio_requires_risk_upgrade
    ):
        generation_datetime = datetime.now()
        generated_portfolio = load_synthetic_portfolio(
            n_exposures=n_exposures,
            seed=seed,
            demo_profile=demo_profile,
            data_quality_level=data_quality_level,
        )
        st.session_state["portfolio"] = generated_portfolio
        st.session_state["demo_profile"] = demo_profile
        st.session_state["data_quality_level"] = data_quality_level
        st.session_state["run_datetime"] = generation_datetime
        st.session_state["run_id"] = generate_run_id(generation_datetime)
        st.session_state["portfolio_generation_summary"] = {
            "profile": demo_profile,
            "data_quality_level": data_quality_level,
            "requested_exposures": int(n_exposures),
            "generated_exposures": int(len(generated_portfolio)),
            "seed": int(seed),
            "generated_at": generation_datetime.strftime("%d/%m/%Y %H:%M:%S"),
            "run_id": st.session_state["run_id"],
            "manual_generation": bool(generate_clicked),
        }
    portfolio = st.session_state["portfolio"]
    active_demo_profile = st.session_state.get("demo_profile", demo_profile)

    if portfolio is None:
        if selected_page == "Accueil":
            render_home(None, demo_profile, show_introduction=False)
        st.info("Generez un portefeuille synthetique pour lancer la demonstration.")
        st.stop()

    missing_columns = missing_required_columns(portfolio)
    if missing_columns:
        st.error("Calcul impossible : colonnes obligatoires absentes.")
        st.write(", ".join(missing_columns))
        st.stop()

    portfolio = ensure_staging_transition_context(portfolio, seed=seed)
    st.session_state["portfolio"] = portfolio

    render_active_demo_context(
        source,
        active_demo_profile,
        st.session_state.get("data_quality_level", data_quality_level),
        portfolio,
    )

    scenario_weights_valid = validate_scenario_weights(scenario_config)
    if not scenario_weights_valid:
        st.error(
            "Calcul impossible : les ponderations macro doivent totaliser 100 %, "
            "rester comprises entre 0 % et 100 %, et les multiplicateurs doivent "
            "etre positifs."
        )
        st.stop()

    try:
        findings = run_data_quality_checks(portfolio)
        dq_summary = summarize_quality_findings(findings)
        raw_quality_tests = run_raw_data_quality_tests(portfolio)
        raw_quality_metrics = build_raw_quality_metrics(portfolio, raw_quality_tests)
        raw_quality_dimensions = build_raw_quality_dimension_summary(raw_quality_tests)
        raw_column_profile = build_raw_column_profile(portfolio)
        staged = assign_stage(portfolio)
        staged = calculate_lgd(
            staged,
            scenario="Baseline",
            preserve_missing_lgd=True,
        )
        ecl_portfolio = calculate_ecl(staged)
        ecl_portfolio = build_review_flags(ecl_portfolio, findings)
        risk_parameter_summary = summarize_risk_parameters(ecl_portfolio)
        lgd_summary = summarize_lgd(ecl_portfolio)
        lgd_by_stage = aggregate_lgd_by_dimension(ecl_portfolio, "stage")
        lgd_by_product = aggregate_lgd_by_dimension(ecl_portfolio, "product_type")
        lgd_by_collateral = aggregate_lgd_by_dimension(
            ecl_portfolio,
            "collateral_type",
        )
        lgd_sensitivity = build_lgd_sensitivity(ecl_portfolio)
        lgd_waterfall = build_lgd_waterfall(ecl_portfolio)
        lifetime_pd_term_structure = build_lifetime_pd_term_structure(ecl_portfolio)
        lifetime_pd_curve = aggregate_lifetime_pd_curve(
            lifetime_pd_term_structure,
            "stage",
        )
        ecl_by_stage = aggregate_ecl_by_stage(ecl_portfolio)
        ecl_by_product = aggregate_ecl_by_dimension(ecl_portfolio, "product_type")
        ecl_by_sector = aggregate_ecl_by_dimension(ecl_portfolio, "sector")
        metrics = build_dashboard_metrics(ecl_portfolio, findings)
        scenario_parameters = scenario_config_to_frame(scenario_config)
        scenario_line_items, scenario_summary = calculate_all_scenarios(ecl_portfolio, scenario_config)
        scenario_metrics = calculate_weighted_ecl_summary(scenario_summary)
        downside_by_stage = calculate_downside_impact_by_stage(scenario_line_items)
        scenario_insights = build_scenario_insights(scenario_metrics, downside_by_stage, scenario_summary)
        overlay_results, overlay_summary = apply_overlays(ecl_portfolio, enabled_overlays)
        overlay_parameters = overlay_config_to_frame([overlay for overlay in PREDEFINED_OVERLAYS if overlay["name"] in enabled_overlays])
        overlay_metrics = build_overlay_metrics(overlay_results, overlay_summary)
        overlay_waterfall = build_overlay_waterfall(overlay_metrics, overlay_summary)
        overlay_insights = build_overlay_insights(overlay_results, overlay_summary, overlay_metrics)
        business_alerts = run_business_consistency_checks(ecl_portfolio)
        business_summary = summarize_business_consistency(business_alerts, len(ecl_portfolio))
        client_discussion_points = build_client_discussion_points(
            active_demo_profile,
            business_summary,
            metrics,
            scenario_metrics,
            overlay_metrics,
        )
        migration_matrix = build_migration_matrix(ecl_portfolio)
        top_contributors = build_top_ecl_contributors(ecl_portfolio)
        insights = build_management_insights(
            ecl_portfolio,
            ecl_by_stage,
            ecl_by_product,
            findings,
            scenario_insights + overlay_insights + build_profile_insights(active_demo_profile, metrics, overlay_metrics),
            business_summary,
        )
        run_datetime = st.session_state.get("run_datetime", datetime.now())
        run_id = st.session_state.get("run_id", generate_run_id(run_datetime))
        review_cases = ecl_portfolio.loc[ecl_portfolio["review_required"]].copy()
        audit_view = build_audit_view(
            run_datetime,
            len(ecl_portfolio),
            len(findings),
            scenario_parameters,
            scenario_summary,
            scenario_metrics,
            overlay_parameters,
            overlay_summary,
            overlay_metrics,
            overlay_results.loc[overlay_results["overlay_applied"]],
        )
        audit_view["business_consistency"] = pd.DataFrame(
            [{"metric": metric, "value": value} for metric, value in business_summary.items()]
        )
        audit_view["business_alerts"] = business_alerts
        audit_view["risk_parameter_summary"] = pd.DataFrame(
            [
                {"metric": metric, "value": value}
                for metric, value in risk_parameter_summary.items()
            ]
        )
        audit_view["lifetime_pd_curve"] = lifetime_pd_curve
        audit_view["lgd_summary"] = pd.DataFrame(
            [
                {"metric": metric, "value": value}
                for metric, value in lgd_summary.items()
            ]
        )
        audit_view["lgd_sensitivity"] = lgd_sensitivity
        staging_transition_summary = (
            staged.groupby(
                ["previous_stage", "stage", "transition_rule", "probation_status"],
                as_index=False,
            )
            .agg(
                exposure_count=("loan_id", "count"),
                ead=("ead", "sum"),
            )
            .sort_values(["previous_stage", "stage", "exposure_count"], ascending=[True, True, False])
        )
        audit_view["staging_transitions"] = staging_transition_summary
        dashboard_summary = build_dashboard_summary_table(metrics, scenario_metrics | overlay_metrics | business_summary)
        detailed_audit_trail = build_audit_trail(
            run_id,
            run_datetime,
            metrics,
            scenario_metrics,
            overlay_metrics,
            ecl_by_stage,
            scenario_parameters,
            scenario_summary,
            overlay_parameters,
            overlay_summary,
            findings,
            review_cases,
            top_contributors,
            audit_view["staging_rules"],
            audit_view["ecl_assumptions"],
            business_summary,
            business_alerts,
            client_discussion_points,
            active_demo_profile,
            staging_transition_summary=staging_transition_summary,
            risk_parameter_summary=risk_parameter_summary,
            lifetime_pd_curve=lifetime_pd_curve,
            lgd_summary=lgd_summary,
            lgd_sensitivity=lgd_sensitivity,
        )
        committee_summary = generate_committee_summary(
            run_id,
            metrics,
            scenario_metrics,
            overlay_metrics,
            ecl_by_stage,
            ecl_by_product,
            ecl_by_sector,
            staged.groupby("stage", as_index=False).size().rename(columns={"size": "count"}),
            scenario_parameters,
            scenario_summary,
            overlay_summary,
            dq_summary,
            len(review_cases),
            top_contributors,
            insights,
            business_summary,
            client_discussion_points,
            active_demo_profile,
        )
    except Exception as exc:
        st.error(f"Calcul impossible : {exc}")
        st.stop()
    if selected_page == "Accueil":
        render_home(metrics, active_demo_profile, portfolio=portfolio, show_introduction=False)

    elif selected_page == "Portefeuille":
        render_portfolio_dashboard(portfolio, metrics)

    elif selected_page == "Data Quality":
        render_raw_data_quality_dashboard(
            portfolio,
            findings,
            dq_summary,
            raw_quality_tests,
            raw_quality_metrics,
            raw_quality_dimensions,
            raw_column_profile,
        )

    elif selected_page == "Parametres de risque":
        render_risk_parameters(
            ecl_portfolio,
            risk_parameter_summary,
            lifetime_pd_term_structure,
            lifetime_pd_curve,
            lgd_summary,
            lgd_by_stage,
            lgd_by_product,
            lgd_by_collateral,
            lgd_sensitivity,
            lgd_waterfall,
        )

    elif selected_page == "Staging":
        render_staging_migration_analysis(staged)

    elif selected_page == "ECL Calculation":
        render_ecl_calculation_dashboard(ecl_portfolio)

    elif selected_page == "Macro Scenarios":
        render_macro_scenarios(
            scenario_parameters,
            scenario_weights_valid,
            scenario_summary,
            scenario_metrics,
            downside_by_stage,
        )

    elif selected_page == "Management Overlays":
        render_management_overlays(overlay_parameters, overlay_summary, overlay_results, overlay_metrics, overlay_waterfall)

    elif selected_page == "Dashboard":
        st.subheader("Dashboard executif")
        render_dashboard(
            metrics,
            ecl_by_stage,
            ecl_by_product,
            ecl_by_sector,
            ecl_portfolio,
            migration_matrix,
            top_contributors,
            overlay_metrics,
            business_summary,
            client_discussion_points,
            active_demo_profile,
        )

        st.subheader("Management Insights")
        for insight in insights:
            st.info(insight)

        render_regulatory_audit_view(audit_view)

    elif selected_page == "Audit Trail":
        render_audit_trail(detailed_audit_trail)

    elif selected_page == "Committee Summary":
        st.subheader("Committee Summary")
        render_committee_summary_visual(
            committee_summary,
            metrics,
            scenario_metrics,
            overlay_metrics,
            ecl_by_stage,
            ecl_by_product,
            ecl_by_sector,
            scenario_summary,
            overlay_summary,
            business_summary,
            top_contributors,
            client_discussion_points,
            active_demo_profile,
            run_id,
        )
        st.download_button(
            "Telecharger la note Markdown",
            data=committee_summary.encode("utf-8"),
            file_name=f"{run_id}_committee_summary.md",
            mime="text/markdown",
        )
        try:
            docx_bytes = build_docx_bytes(committee_summary)
            st.download_button(
                "Telecharger la note Word",
                data=docx_bytes,
                file_name=f"{run_id}_committee_summary.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        except Exception as exc:
            st.warning(f"Export Word indisponible : {exc}")

    elif selected_page == "Export":
        st.subheader("Export Excel")
        staging_results = staged[
            [
                "loan_id",
                "client_id",
                "initial_stage",
                "previous_stage",
                "stage",
                "transition_rule",
                "probation_status",
                "cure_period_months",
                "probation_required_months",
                "stage_reason",
                "stage_comment",
                "days_past_due",
                "origination_rating",
                "previous_rating",
                "current_rating",
                "origination_pd_12m",
                "pd_12m",
                "pd_lifetime",
                "pd_lifetime_multiplier",
                "pd_lifetime_method",
                "sicr_flag",
                "credit_impaired_flag",
                "unlikely_to_pay_flag",
                "bankruptcy_flag",
                "distressed_restructuring_flag",
                "payment_normalized_flag",
            ]
        ]
        risk_parameter_export = ecl_portfolio[
            [
                "loan_id",
                "client_id",
                "stage",
                "product_type",
                "sector",
                "country",
                "ead",
                "residual_maturity_months",
                "current_rating",
                "pd_12m",
                "pd_lifetime",
                "pd_lifetime_multiplier",
                "lgd",
                "pd_lifetime_method",
            ]
        ]
        lgd_parameter_columns = [
            "loan_id",
            "client_id",
            "stage",
            "product_type",
            "sector",
            "country",
            "ead",
            "collateral_flag",
            "collateral_type",
            "collateral_value",
            "seniority",
            "collateral_haircut",
            "liquidation_cost_rate",
            "unsecured_recovery_rate",
            "recovery_delay_months",
            "recovery_cost_amount",
            "secured_recovery_amount",
            "unsecured_recovery_amount",
            "discounted_recovery_amount",
            "lgd_seniority_multiplier",
            "lgd",
            "lgd_method",
        ]
        lgd_parameter_export = ecl_portfolio[
            [
                column
                for column in lgd_parameter_columns
                if column in ecl_portfolio.columns
            ]
        ]
        export_bytes = build_excel_export_bytes(
            portfolio,
            findings,
            staging_results,
            ecl_portfolio,
            dashboard_summary,
            audit_view,
            scenario_parameters,
            scenario_summary,
            overlay_parameters,
            overlay_results,
            detailed_audit_trail,
            committee_summary,
            business_alerts,
            storyline_to_frame(),
            discussion_points_to_frame(client_discussion_points),
            risk_parameters=risk_parameter_export,
            lifetime_pd_curve=lifetime_pd_curve,
            lgd_parameters=lgd_parameter_export,
            lgd_sensitivity=lgd_sensitivity,
        )
        if st.button("Exporter dans le dossier outputs"):
            try:
                export_file_name = f"{EXPORT_FILE_PREFIX}_{run_id}.xlsx"
                output_path = export_results_to_excel(
                    portfolio,
                    findings,
                    staging_results,
                    ecl_portfolio,
                    dashboard_summary,
                    audit_view,
                    scenario_parameters,
                    scenario_summary,
                    overlay_parameters,
                    overlay_results,
                    detailed_audit_trail,
                    committee_summary,
                    business_alerts,
                    storyline_to_frame(),
                    discussion_points_to_frame(client_discussion_points),
                    file_name=export_file_name,
                    risk_parameters=risk_parameter_export,
                    lifetime_pd_curve=lifetime_pd_curve,
                    lgd_parameters=lgd_parameter_export,
                    lgd_sensitivity=lgd_sensitivity,
                )
                st.success(f"Export cree : {output_path}")
            except Exception as exc:
                st.error(f"Export impossible : {exc}")
        st.download_button(
            "Telecharger les resultats Excel",
            data=export_bytes,
            file_name=f"{EXPORT_FILE_PREFIX}_{run_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def build_scenario_controls() -> dict[str, dict[str, float]]:
    """Render sidebar scenario controls and return the selected configuration."""
    scenario_config = {}
    for scenario in DEFAULT_SCENARIOS:
        with st.expander(scenario, expanded=scenario == "Baseline"):
            weight = st.number_input(
                f"{scenario} weight",
                min_value=0.0,
                max_value=100.0,
                step=5.0,
                key=f"{scenario.lower()}_weight",
            )
            pd_multiplier = st.number_input(
                f"{scenario} PD multiplier",
                min_value=0.0,
                max_value=5.0,
                step=0.05,
                key=f"{scenario.lower()}_pd_multiplier",
            )
            lgd_multiplier = st.number_input(
                f"{scenario} LGD multiplier",
                min_value=0.0,
                max_value=5.0,
                step=0.05,
                key=f"{scenario.lower()}_lgd_multiplier",
            )
        scenario_config[scenario] = {
            "weight": weight / 100,
            "pd_multiplier": pd_multiplier,
            "lgd_multiplier": lgd_multiplier,
        }
    return scenario_config


def render_home_introduction() -> None:
    """Render the commercial introduction shown before the demo settings."""
    st.subheader("IFRS 9 ECL & Staging Demonstrator")
    st.markdown("**Transformer le provisionnement IFRS 9 en un outil de pilotage transparent, explicable et auditable.**")
    st.write(
        "Ce demonstrateur illustre de maniere simple et pedagogique la chaine IFRS 9 : qualite des donnees, "
        "staging, calcul des pertes attendues et restitution executive pour discussion client."
    )
    st.warning(DEMO_DISCLAIMER_FR)


def render_home(
    metrics: dict[str, float] | None,
    demo_profile: str | None = None,
    portfolio: pd.DataFrame | None = None,
    show_introduction: bool = True,
) -> None:
    """Render the client-demo landing section."""
    if show_introduction:
        render_home_introduction()

    if demo_profile:
        render_portfolio_summary(demo_profile, portfolio, metrics)

    render_demo_storyline()

    render_contact_block()


def render_demo_storyline() -> None:
    """Render the demo journey as a styled sequence rather than a data table."""
    storyline_icons = ["01", "02", "03", "04", "05", "06"]
    cards = []
    for icon, item in zip(storyline_icons, DEMO_STORYLINE):
        cards.append(
            dedent(
                f"""
                <article class="storyline-card">
                    <div class="storyline-number">{icon}</div>
                    <div>
                        <div class="storyline-title">{item["title"]}</div>
                        <div class="storyline-description">{item["description"]}</div>
                    </div>
                </article>
                """
            ).strip()
        )

    st.markdown(
        dedent(
            f"""
            <section class="storyline-section">
                <div class="storyline-kicker">Parcours de demonstration</div>
                <h3 class="storyline-heading">De la donnee synthetique a la decision comite</h3>
                <p class="storyline-intro">
                    Un parcours en six etapes pour illustrer les controles, les calculs,
                    les ajustements et la gouvernance IFRS 9.
                </p>
                <div class="storyline-grid">{''.join(cards)}</div>
            </section>
            """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_portfolio_summary(
    demo_profile: str,
    portfolio: pd.DataFrame | None,
    metrics: dict[str, float] | None,
) -> None:
    """Render an exhaustive description of the active synthetic portfolio."""
    if portfolio is None or portfolio.empty:
        st.info(f"Profil selectionne : {demo_profile}. {PROFILE_CONTEXT.get(demo_profile, '')}")
        return

    total_ead = float(pd.to_numeric(portfolio.get("ead"), errors="coerce").fillna(0).sum())
    total_ecl = float(metrics.get("total_ecl", 0.0)) if metrics else 0.0
    coverage_ratio = float(metrics.get("coverage_ratio", 0.0)) if metrics else 0.0
    default_rate = float(
        coerce_boolean_series(
            portfolio.get("default_flag", pd.Series(False, index=portfolio.index))
        ).mean()
    )
    forbearance_rate = float(
        coerce_boolean_series(
            portfolio.get("forbearance_flag", pd.Series(False, index=portfolio.index))
        ).mean()
    )
    watchlist_rate = float(
        coerce_boolean_series(
            portfolio.get("watchlist_flag", pd.Series(False, index=portfolio.index))
        ).mean()
    )
    collateral_rate = float(
        coerce_boolean_series(
            portfolio.get("collateral_flag", pd.Series(False, index=portfolio.index))
        ).mean()
    )
    exposure_label = f"{len(portfolio):,}".replace(",", " ")
    profile_focus = {
        "Balanced Portfolio": "Portefeuille diversifie servant de cas central, avec une combinaison equilibree de stages, produits et secteurs.",
        "Low Risk Portfolio": "Portefeuille majoritairement sain, avec faibles PD, peu de retards et une migration Stage 2/3 limitee.",
        "Deteriorated Portfolio": "Portefeuille degrade : ratings plus faibles, DPD plus frequents, flags de risque renforces et ECL plus concentree.",
        "Data Quality Issues Portfolio": "Portefeuille volontairement altere pour tester ratings/PD/LGD manquants, EAD invalides, DPD negatifs et incoherences de collateral.",
        "CRE Stress Portfolio": "Portefeuille concentre sur l'immobilier commercial, avec EAD, PD, LGD et signaux watchlist renforces sur ce secteur.",
    }.get(demo_profile, PROFILE_CONTEXT.get(demo_profile, "Profil synthetique de demonstration."))

    st.markdown(
        f"""
        <section style="
            margin: 18px 0 26px;
            padding: 24px 26px;
            border: 1px solid rgba(11, 43, 70, 0.18);
            border-radius: 18px;
            color: #ffffff;
            background: linear-gradient(135deg, #0b2b46, #174866);
            box-shadow: 0 18px 44px rgba(11, 43, 70, 0.12);
        ">
            <div style="color:#f1a986; font-size:0.76rem; font-weight:900; letter-spacing:0.1em; text-transform:uppercase;">
                Portefeuille simule actif
            </div>
            <h3 style="margin:8px 0 10px; color:#ffffff; font-size:1.55rem;">{demo_profile}</h3>
            <p style="margin:0 0 18px; color:rgba(255,255,255,0.88); line-height:1.65;">{profile_focus}</p>
            <div class="portfolio-summary-grid" style="
                display:grid;
                grid-template-columns:repeat(4, minmax(0, 1fr));
                gap:10px;
                margin-bottom:20px;
            ">
                <div><strong>{exposure_label}</strong><br><span>expositions</span></div>
                <div><strong>{format_compact_currency(total_ead)}</strong><br><span>EAD totale</span></div>
                <div><strong>{format_compact_currency(total_ecl)}</strong><br><span>ECL totale</span></div>
                <div><strong>{coverage_ratio:.2%}</strong><br><span>taux de couverture</span></div>
            </div>
            <div class="portfolio-summary-grid" style="
                display:grid;
                grid-template-columns:repeat(4, minmax(0, 1fr));
                gap:10px;
                padding-top:16px;
                border-top:1px solid rgba(255,255,255,0.16);
            ">
                <div><strong>{default_rate:.1%}</strong><br><span>defaut synthetique</span></div>
                <div><strong>{forbearance_rate:.1%}</strong><br><span>forbearance</span></div>
                <div><strong>{watchlist_rate:.1%}</strong><br><span>watchlist</span></div>
                <div><strong>{collateral_rate:.1%}</strong><br><span>avec collateral</span></div>
            </div>
            <p style="margin:20px 0 0; color:rgba(255,255,255,0.76); font-size:0.82rem; line-height:1.55;">
                Le jeu simule des ratings de 1 a 10, PD 12 mois et lifetime, LGD, EAD, maturites,
                jours de retard, defaut, forbearance, watchlist, collateral et LTV. Les distributions
                sont pedagogiques, reproductibles par seed et non calibrees sur une banque reelle.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_portfolio_dashboard(portfolio: pd.DataFrame, metrics: dict[str, float]) -> None:
    """Render a visual description of the synthetic portfolio."""
    auria_chart_colors = [
        "#0B2B46",
        "#F1A986",
        "#6D7885",
        "#14664A",
        "#F7C6AE",
        "#8298AA",
    ]

    st.subheader("Vue d'ensemble du portefeuille")
    st.write(
        "Lecture synthetique de la composition du portefeuille, des concentrations "
        "et de la repartition de l'exposition au defaut."
    )

    country_labels = {
        "FR": "France",
        "DE": "Allemagne",
        "IT": "Italie",
        "ES": "Espagne",
        "BE": "Belgique",
        "NL": "Pays-Bas",
    }
    display = portfolio.copy()
    display["country_name"] = display["country"].map(country_labels).fillna(display["country"])

    total_ead = float(pd.to_numeric(display["ead"], errors="coerce").fillna(0).sum())
    total_ecl = float(metrics["total_ecl"])
    coverage_ratio = float(metrics["coverage_ratio"])

    render_kpi_panel(
        "Lecture synthetique du portefeuille",
        [
            ("Expositions", f"{len(display):,}".replace(",", " "), "Contrats synthetiques"),
            ("EAD totale", format_compact_currency(total_ead), "Exposure at Default"),
            ("ECL totale", format_compact_currency(total_ecl), "Expected Credit Loss"),
            ("Taux de couverture", f"{coverage_ratio:.2%}", "ECL totale / EAD totale"),
        ],
    )

    st.markdown("#### Composition du portefeuille")
    product_mix = (
        display.groupby("product_type", as_index=False)
        .agg(exposure_count=("loan_id", "count"), ead=("ead", "sum"))
        .sort_values("exposure_count", ascending=False)
    )
    sector_mix = (
        display.groupby("sector", as_index=False)
        .agg(exposure_count=("loan_id", "count"), ead=("ead", "sum"))
        .sort_values("exposure_count", ascending=False)
    )
    country_mix = (
        display.groupby("country_name", as_index=False)
        .agg(exposure_count=("loan_id", "count"), ead=("ead", "sum"))
        .sort_values("exposure_count", ascending=False)
    )

    pie_cols = st.columns(3)
    pie_specs = [
        (pie_cols[0], product_mix, "product_type", "Repartition par produit"),
        (pie_cols[1], sector_mix, "sector", "Repartition par secteur"),
        (pie_cols[2], country_mix, "country_name", "Repartition par pays"),
    ]
    for container, data, label_column, title in pie_specs:
        with container:
            figure = px.pie(
                data,
                names=label_column,
                values="exposure_count",
                title=title,
                hole=0.38,
                color_discrete_sequence=auria_chart_colors,
            )
            figure.update_traces(
                textposition="inside",
                textinfo="percent",
                textfont=dict(size=13, color="#FFFFFF"),
                marker=dict(line=dict(color="#FFFAF5", width=2)),
                hovertemplate="<b>%{label}</b><br>Expositions : %{value}<br>Part : %{percent}<extra></extra>",
            )
            figure.update_layout(
                height=390,
                margin=dict(l=8, r=8, t=60, b=16),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, Aptos, Segoe UI, Arial", color="#0B2B46"),
                title=dict(
                    x=0.02,
                    xanchor="left",
                    font=dict(size=17, color="#0B2B46"),
                ),
                legend_title_text="",
                legend=dict(
                    orientation="h",
                    y=-0.10,
                    x=0.5,
                    xanchor="center",
                    font=dict(size=11, color="#536575"),
                    bgcolor="rgba(0,0,0,0)",
                ),
            )
            st.plotly_chart(figure, width="stretch")

    st.markdown("#### Exposition au defaut")
    ead_left, ead_right = st.columns([1.15, 0.85])
    with ead_left:
        ead_by_product = product_mix.sort_values("ead", ascending=True)
        product_figure = px.bar(
            ead_by_product,
            x="ead",
            y="product_type",
            orientation="h",
            title="EAD totale par type de produit",
            text_auto=".3s",
        )
        product_figure.update_layout(
            height=410,
            xaxis_title="EAD",
            yaxis_title="",
            margin=dict(l=10, r=20, t=55, b=25),
        )
        st.plotly_chart(product_figure, width="stretch")

    with ead_right:
        ead_by_country = country_mix.sort_values("ead", ascending=False)
        country_figure = px.bar(
            ead_by_country,
            x="country_name",
            y="ead",
            title="EAD totale par pays",
            text_auto=".3s",
        )
        country_figure.update_layout(
            height=410,
            xaxis_title="",
            yaxis_title="EAD",
            margin=dict(l=10, r=10, t=55, b=25),
        )
        st.plotly_chart(country_figure, width="stretch")

    st.markdown("#### Profil des expositions")
    profile_left, profile_right = st.columns(2)
    with profile_left:
        ead_distribution = px.histogram(
            display,
            x="ead",
            nbins=30,
            title="Distribution des montants EAD",
            labels={"ead": "EAD par exposition", "count": "Nombre d'expositions"},
        )
        ead_distribution.update_layout(height=360, yaxis_title="Nombre d'expositions")
        st.plotly_chart(ead_distribution, width="stretch")
    with profile_right:
        maturity_distribution = px.histogram(
            display,
            x="residual_maturity_months",
            nbins=20,
            title="Distribution des maturites residuelles",
            labels={
                "residual_maturity_months": "Maturite residuelle (mois)",
                "count": "Nombre d'expositions",
            },
        )
        maturity_distribution.update_layout(height=360, yaxis_title="Nombre d'expositions")
        st.plotly_chart(maturity_distribution, width="stretch")


def render_ecl_calculation_dashboard(ecl_portfolio: pd.DataFrame) -> None:
    """Render a filtered visual analysis of model ECL results."""
    st.subheader("Calcul ECL")
    st.write(
        "Analyse des pertes de credit attendues avant scenarios macroeconomiques et overlays. "
        "Les filtres permettent d'isoler un produit puis les secteurs disponibles sur ce perimetre."
    )

    product_options = ["Tous les produits"] + sorted(
        ecl_portfolio["product_type"].dropna().astype(str).unique().tolist()
    )
    if st.session_state.get("ecl_product_filter") not in product_options:
        st.session_state["ecl_product_filter"] = product_options[0]

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        selected_product = st.selectbox(
            "Type de produit",
            options=product_options,
            key="ecl_product_filter",
        )

    product_scope = ecl_portfolio.copy()
    if selected_product != "Tous les produits":
        product_scope = product_scope.loc[product_scope["product_type"].eq(selected_product)].copy()

    sector_options = ["Tous les secteurs"] + sorted(
        product_scope["sector"].dropna().astype(str).unique().tolist()
    )
    if st.session_state.get("ecl_sector_filter") not in sector_options:
        st.session_state["ecl_sector_filter"] = sector_options[0]
    with filter_col2:
        selected_sector = st.selectbox(
            "Secteur",
            options=sector_options,
            key="ecl_sector_filter",
            help="La liste des secteurs depend du type de produit selectionne.",
        )

    filtered = product_scope.copy()
    if selected_sector != "Tous les secteurs":
        filtered = filtered.loc[filtered["sector"].eq(selected_sector)].copy()

    if filtered.empty:
        st.warning("Aucune exposition ne correspond aux filtres selectionnes.")
        return

    filtered["ead"] = pd.to_numeric(filtered["ead"], errors="coerce").fillna(0)
    filtered["ecl"] = pd.to_numeric(filtered["ecl"], errors="coerce").fillna(0)
    total_ead = float(filtered["ead"].sum())
    total_ecl = float(filtered["ecl"].sum())
    coverage_ratio = safe_divide(total_ecl, total_ead)

    ecl_metrics = [
        ("Expositions", f"{len(filtered):,}".replace(",", " "), "Perimetre filtre"),
        ("EAD totale", format_compact_currency(total_ead), "Exposure at Default"),
        ("ECL totale", format_compact_currency(total_ecl), "Avant scenarios et overlays"),
        ("Taux de couverture", f"{coverage_ratio:.2%}", "ECL / EAD"),
    ]
    ecl_metric_markup = "".join(
        (
            '<div class="migration-kpi-item">'
            f'<div class="migration-kpi-label">{label}</div>'
            f'<div class="migration-kpi-value">{value}</div>'
            f'<div class="migration-kpi-caption">{caption}</div>'
            "</div>"
        )
        for label, value, caption in ecl_metrics
    )
    st.markdown(
        dedent(
            f"""
            <section class="migration-kpi-panel">
                <div class="migration-kpi-kicker">Synthese du perimetre selectionne</div>
                <div class="migration-kpi-grid ecl-kpi-grid">{ecl_metric_markup}</div>
            </section>
            """
        ).strip(),
        unsafe_allow_html=True,
    )

    stage_order = ["Stage 1", "Stage 2", "Stage 3"]
    stage_summary = (
        filtered.groupby("stage", as_index=False)
        .agg(
            exposure_count=("loan_id", "count"),
            ead=("ead", "sum"),
            ecl=("ecl", "sum"),
        )
        .set_index("stage")
        .reindex(stage_order, fill_value=0)
        .reset_index()
    )
    stage_summary["coverage_ratio"] = safe_divide(
        stage_summary["ecl"],
        stage_summary["ead"],
    )
    stage_summary["ecl_share"] = safe_divide(stage_summary["ecl"], total_ecl)

    st.markdown("#### Profil du perimetre selectionne")
    profile_left, profile_right = st.columns(2)
    with profile_left:
        count_figure = px.bar(
            stage_summary,
            x="stage",
            y="exposure_count",
            text="exposure_count",
            title="Nombre d'expositions par stage",
            color="stage",
            color_discrete_map={
                "Stage 1": "#8298AA",
                "Stage 2": "#F1A986",
                "Stage 3": "#0B2B46",
            },
        )
        count_figure.update_layout(
            height=360,
            xaxis_title="",
            yaxis_title="Nombre d'expositions",
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(count_figure, width="stretch")

    with profile_right:
        ead_figure = px.bar(
            stage_summary,
            x="stage",
            y="ead",
            text_auto=".3s",
            title="EAD par stage",
            color="stage",
            color_discrete_map={
                "Stage 1": "#8298AA",
                "Stage 2": "#F1A986",
                "Stage 3": "#0B2B46",
            },
        )
        ead_figure.update_layout(
            height=360,
            xaxis_title="",
            yaxis_title="EAD (EUR)",
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(ead_figure, width="stretch")

    st.markdown("#### ECL par stage")
    chart_left, chart_right = st.columns([1.15, 0.85])
    with chart_left:
        stage_figure = go.Figure()
        stage_figure.add_trace(
            go.Bar(
                x=stage_summary["stage"],
                y=stage_summary["ecl"],
                name="ECL",
                marker_color=["#8298AA", "#F1A986", "#0B2B46"],
                text=[format_compact_currency(value) for value in stage_summary["ecl"]],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>ECL : %{y:,.0f} EUR<extra></extra>",
            )
        )
        stage_figure.add_trace(
            go.Scatter(
                x=stage_summary["stage"],
                y=stage_summary["coverage_ratio"],
                name="Taux de couverture",
                mode="lines+markers+text",
                text=[f"{value:.1%}" for value in stage_summary["coverage_ratio"]],
                textposition="top center",
                line=dict(color="#14664A", width=3),
                marker=dict(size=9),
                yaxis="y2",
                hovertemplate="<b>%{x}</b><br>Couverture : %{y:.2%}<extra></extra>",
            )
        )
        stage_figure.update_layout(
            title="Montant ECL et taux de couverture",
            height=430,
            xaxis_title="",
            yaxis=dict(title="ECL (EUR)", showgrid=True, gridcolor="rgba(11,43,70,0.08)"),
            yaxis2=dict(
                title="Taux de couverture",
                overlaying="y",
                side="right",
                tickformat=".0%",
                rangemode="tozero",
            ),
            legend=dict(orientation="h", y=1.12, x=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=80, b=35),
        )
        st.plotly_chart(stage_figure, width="stretch")

    with chart_right:
        if total_ecl:
            ecl_share_figure = px.pie(
                stage_summary.loc[stage_summary["ecl"].gt(0)],
                names="stage",
                values="ecl",
                hole=0.62,
                title="Contribution de chaque stage a l'ECL",
                color="stage",
                color_discrete_map={
                    "Stage 1": "#8298AA",
                    "Stage 2": "#F1A986",
                    "Stage 3": "#0B2B46",
                },
            )
            ecl_share_figure.update_traces(
                textposition="inside",
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>ECL : %{value:,.0f} EUR<br>Part : %{percent}<extra></extra>",
            )
            ecl_share_figure.update_layout(
                height=430,
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=70, b=25),
            )
            st.plotly_chart(ecl_share_figure, width="stretch")
        else:
            st.info("Aucune ECL positive sur le perimetre selectionne.")

    st.markdown("#### ECL par motif de staging")

    def render_stage_reason_chart(stage_name: str, color: str) -> None:
        stage_data = filtered.loc[filtered["stage"].eq(stage_name)].copy()
        if stage_data.empty:
            st.info(f"Aucune exposition {stage_name} sur le perimetre selectionne.")
            return
        reason_summary = (
            stage_data.groupby("stage_reason", as_index=False)
            .agg(ecl=("ecl", "sum"), exposure_count=("loan_id", "count"))
            .sort_values("ecl", ascending=True)
        )
        reason_figure = px.bar(
            reason_summary,
            x="ecl",
            y="stage_reason",
            orientation="h",
            text_auto=".3s",
            title=f"{stage_name} - ECL par motif",
            custom_data=["exposure_count"],
            color_discrete_sequence=[color],
        )
        reason_figure.update_traces(
            hovertemplate=(
                "<b>%{y}</b><br>ECL : %{x:,.0f} EUR"
                "<br>Expositions : %{customdata[0]}<extra></extra>"
            )
        )
        reason_figure.update_layout(
            height=max(360, 44 * len(reason_summary)),
            xaxis_title="ECL (EUR)",
            yaxis_title="",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=15, t=55, b=35),
        )
        st.plotly_chart(reason_figure, width="stretch")

    probation_columns = [
        column
        for column in [
            "returned_to_stage_1_flag",
            "probation_flag",
            "probation_status",
            "probation_period_flag",
            "cure_flag",
        ]
        if column in filtered.columns
    ]
    if probation_columns:
        probation_column = probation_columns[0]
        stage_1 = filtered.loc[filtered["stage"].eq("Stage 1")].copy()
        if not stage_1.empty:
            if probation_column == "returned_to_stage_1_flag":
                probation_mask = coerce_boolean_series(stage_1[probation_column])
            else:
                probation_values = stage_1[probation_column]
                probation_mask = probation_values.fillna(False).astype(str).str.lower().isin(
                    [
                        "true",
                        "1",
                        "yes",
                        "oui",
                        "active",
                        "probation",
                        "cured",
                        "cure",
                        "stage 2 probation completed",
                        "exceptional full cure completed",
                    ]
                )
            stage_1["stage_1_origin"] = np.where(
                probation_mask,
                "Retour en Stage 1 apres probation",
                "Stage 1 nativement sain",
            )
            probation_summary = (
                stage_1.groupby("stage_1_origin", as_index=False)
                .agg(ead=("ead", "sum"), ecl=("ecl", "sum"), exposure_count=("loan_id", "count"))
            )
            probation_figure = go.Figure()
            probation_figure.add_trace(
                go.Bar(
                    x=probation_summary["stage_1_origin"],
                    y=probation_summary["ead"],
                    name="EAD",
                    marker_color="#8298AA",
                    text=[format_compact_currency(value) for value in probation_summary["ead"]],
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>EAD : %{y:,.0f} EUR<extra></extra>",
                )
            )
            probation_figure.add_trace(
                go.Bar(
                    x=probation_summary["stage_1_origin"],
                    y=probation_summary["ecl"],
                    name="ECL",
                    marker_color="#F1A986",
                    text=[format_compact_currency(value) for value in probation_summary["ecl"]],
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>ECL : %{y:,.0f} EUR<extra></extra>",
                )
            )
            probation_figure.update_layout(
                barmode="group",
                title="Stage 1 - expositions saines et retours apres probation",
                height=420,
                xaxis_title="",
                yaxis_title="Montant (EUR)",
                legend=dict(
                    title="",
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="left",
                    x=0,
                    font=dict(color="#0B2B46"),
                ),
                showlegend=True,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=90, b=45),
            )
            st.plotly_chart(probation_figure, width="stretch")

    reason_cols = st.columns(2)
    with reason_cols[0]:
        render_stage_reason_chart("Stage 2", "#F1A986")
    with reason_cols[1]:
        render_stage_reason_chart("Stage 3", "#0B2B46")

    with st.expander("Consulter le detail des calculs ECL", expanded=False):
        st.dataframe(
            filtered[
                [
                    "loan_id",
                    "client_id",
                    "product_type",
                    "sector",
                    "stage",
                    "stage_reason",
                    "ead",
                    "pd_12m",
                    "pd_lifetime",
                    "pd_used_for_ecl",
                    "lgd",
                    "ecl",
                    "coverage_ratio",
                    "data_quality_status",
                    "review_required",
                    "review_reason",
                ]
            ],
            width="stretch",
            hide_index=True,
        )


def render_transition_heatmap(
    matrix: pd.DataFrame,
    title: str,
    x_title: str,
    y_title: str,
) -> None:
    """Render an interactive percentage transition matrix."""
    values = matrix.to_numpy(dtype=float)
    text = np.vectorize(lambda value: f"{value:.1%}")(values)
    figure = go.Figure(
        data=go.Heatmap(
            z=values,
            x=list(matrix.columns),
            y=list(matrix.index),
            text=text,
            texttemplate="%{text}",
            colorscale=[
                [0.0, "#F8F4EF"],
                [0.35, "#F7C6AE"],
                [0.70, "#F1A986"],
                [1.0, "#0B2B46"],
            ],
            zmin=0,
            zmax=max(0.01, float(np.nanmax(values))),
            colorbar=dict(title="%"),
            hovertemplate=(
                f"{y_title}: %{{y}}<br>{x_title}: %{{x}}"
                "<br>Part: %{z:.2%}<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        title=title,
        height=max(430, 38 * len(matrix.index)),
        xaxis_title=None,
        yaxis_title=y_title,
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=list(matrix.columns),
            side="top",
        ),
        yaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=list(matrix.index),
            autorange="reversed",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=30, r=20, t=82, b=30),
    )
    st.plotly_chart(
        figure,
        width="stretch",
        config={"scrollZoom": True, "displaylogo": False},
    )


def render_staging_migration_analysis(staged: pd.DataFrame) -> None:
    """Render rating and stage transition analytics."""
    st.subheader("Staging et analyse des migrations")
    st.write(
        "Analyse des mouvements entre la reference selectionnee et la date courante, "
        "en nombre d'expositions ou en EAD. Une hausse de note correspond a une "
        "deterioration sur l'echelle synthetique 1 a 10."
    )

    rating_reference_label = st.radio(
        "Reference de la matrice de notation",
        options=["Note a l'octroi vs note courante", "Note precedente vs note courante"],
        index=0,
        horizontal=True,
        key="rating_transition_reference",
        help=(
            "La note a l'octroi mesure la deterioration depuis l'origine. "
            "La note precedente mesure la migration entre deux clotures successives."
        ),
    )
    source_rating = (
        "previous_rating"
        if rating_reference_label == "Note precedente vs note courante"
        else "origination_rating"
    )
    source_rating_title = (
        "Note precedente"
        if source_rating == "previous_rating"
        else "Note a l'octroi"
    )

    metrics = calculate_rating_migration_metrics(staged, source_rating=source_rating)
    primary_metrics = [
        ("Stabilite", f"{metrics['stability_rate']:.1%}", f"{metrics['stability_ead_rate']:.1%} de l'EAD stable"),
        ("Degradation", f"{metrics['degradation_rate']:.1%}", f"{metrics['degradation_ead_rate']:.1%} de l'EAD"),
        ("Amelioration", f"{metrics['improvement_rate']:.1%}", f"{metrics['improvement_ead_rate']:.1%} de l'EAD"),
        ("Migration nette", f"{metrics['net_migration_rate']:+.1%}", "Degradation moins amelioration"),
        ("Migration moyenne", f"{metrics['average_notch_migration']:+.2f}", "Crans par exposition"),
    ]
    secondary_metrics = [
        ("Degradation 1 cran", f"{metrics['one_notch_degradation_rate']:.1%}", "Migration moderee"),
        ("Degradation >= 2 crans", f"{metrics['two_plus_degradation_rate']:.1%}", "Signal de deterioration"),
        ("Vers grades sensibles", f"{metrics['worst_grade_degradation_rate']:.1%}", "Notes courantes 8 a 10"),
        ("Vers defaut", f"{metrics['default_migration_rate']:.1%}", f"{metrics['default_migration_ead_rate']:.1%} de l'EAD"),
    ]

    def metric_markup(metric: tuple[str, str, str]) -> str:
        label, value, caption = metric
        return (
            '<div class="migration-kpi-item">'
            f'<div class="migration-kpi-label">{label}</div>'
            f'<div class="migration-kpi-value">{value}</div>'
            f'<div class="migration-kpi-caption">{caption}</div>'
            "</div>"
        )

    st.markdown(
        dedent(
            f"""
            <section class="migration-kpi-panel">
                <div class="migration-kpi-kicker">Lecture synthetique des migrations</div>
                <div class="migration-kpi-grid migration-kpi-grid-primary">
                    {''.join(metric_markup(metric) for metric in primary_metrics)}
                </div>
                <div class="migration-kpi-grid migration-kpi-grid-secondary">
                    {''.join(metric_markup(metric) for metric in secondary_metrics)}
                </div>
            </section>
            """
        ).strip(),
        unsafe_allow_html=True,
    )

    measure_label = st.radio(
        "Expression des matrices",
        options=["% des effectifs", "% de l'EAD"],
        index=0,
        horizontal=True,
        key="staging_matrix_measure",
    )
    measure = "ead" if measure_label == "% de l'EAD" else "count"

    st.markdown("#### Matrice de transition des ratings")
    st.caption(
        "La colonne Defaut regroupe les expositions avec default flag, DPD >= 90 jours "
        "ou classement final en Stage 3."
    )
    rating_matrix = build_rating_transition_matrix(
        staged,
        measure=measure,
        source_rating=source_rating,
    )
    render_transition_heatmap(
        rating_matrix,
        f"{source_rating_title} vers note courante - {measure_label}",
        "Note courante",
        source_rating_title,
    )

    st.markdown("#### Matrice de migration des stages")
    available_reasons = sorted(staged["stage_reason"].dropna().unique().tolist())
    selected_reasons = st.multiselect(
        "Zoom sur les motifs de staging",
        options=available_reasons,
        default=available_reasons,
        help="Retirez des motifs pour isoler une population et recalculer dynamiquement la matrice.",
        key="staging_reason_filter",
    )
    stage_matrix = build_stage_transition_matrix(
        staged,
        measure=measure,
        stage_reasons=selected_reasons,
    )
    render_transition_heatmap(
        stage_matrix,
        f"Stage precedent vers stage recalcule - {measure_label}",
        "Stage recalcule",
        "Stage precedent",
    )

    filtered_stages = staged.loc[staged["stage_reason"].isin(selected_reasons)].copy()
    reason_summary = (
        filtered_stages.groupby(["stage", "stage_reason"], as_index=False)
        .agg(expositions=("loan_id", "count"), ead=("ead", "sum"))
    )
    if not reason_summary.empty:
        reason_value = "ead" if measure == "ead" else "expositions"
        reason_chart = px.bar(
            reason_summary,
            x="stage",
            y=reason_value,
            color="stage_reason",
            title="Composition des stages par motif declencheur",
            color_discrete_sequence=["#0B2B46", "#F1A986", "#6D7885", "#14664A", "#8298AA"],
        )
        reason_chart.update_layout(
            height=390,
            xaxis_title="",
            yaxis_title="EAD" if measure == "ead" else "Nombre d'expositions",
            legend_title_text="Motif",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(reason_chart, width="stretch")

    st.markdown("#### Nature des migrations de rating")
    breakdown = build_migration_breakdown(staged, source_rating=source_rating)
    breakdown_long = breakdown.melt(
        id_vars=["rating_migration_type"],
        value_vars=["exposure_share", "ead_share"],
        var_name="measure",
        value_name="share",
    )
    breakdown_long["measure"] = breakdown_long["measure"].map(
        {"exposure_share": "% des effectifs", "ead_share": "% de l'EAD"}
    )
    breakdown_figure = px.bar(
        breakdown_long,
        x="rating_migration_type",
        y="share",
        color="measure",
        barmode="group",
        text_auto=".1%",
        title="Repartition des migrations",
        color_discrete_map={"% des effectifs": "#0B2B46", "% de l'EAD": "#F1A986"},
    )
    breakdown_figure.update_layout(
        height=420,
        xaxis_title="",
        yaxis_title="Part du portefeuille",
        yaxis_tickformat=".0%",
        legend_title_text="",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(breakdown_figure, width="stretch")

    product_migration = build_average_migration_by_dimension(
        staged,
        "product_type",
        source_rating=source_rating,
    )
    product_long = product_migration.melt(
        id_vars=["product_type"],
        value_vars=["average_notch_migration", "ead_weighted_notch_migration"],
        var_name="measure",
        value_name="migration",
    )
    product_long["measure"] = product_long["measure"].map(
        {
            "average_notch_migration": "Moyenne simple",
            "ead_weighted_notch_migration": "Moyenne ponderee par EAD",
        }
    )
    product_figure = px.bar(
        product_long,
        x="product_type",
        y="migration",
        color="measure",
        barmode="group",
        text_auto="+.2f",
        title="Migration moyenne par produit",
        color_discrete_map={"Moyenne simple": "#0B2B46", "Moyenne ponderee par EAD": "#F1A986"},
    )
    product_figure.add_hline(y=0, line_color="#6D7885", line_width=1)
    product_figure.update_layout(
        height=410,
        xaxis_title="",
        yaxis_title="Migration moyenne en crans",
        legend_title_text="",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(product_figure, width="stretch")
    st.caption(
        "Une valeur positive indique une deterioration moyenne du portefeuille ; "
        "une valeur negative indique une amelioration."
    )

    st.markdown("#### Migrations fortes et cliff effects")
    st.caption(
        "Top 10 des deteriorations d'au moins deux crans ou migrations vers le defaut, "
        "classees par severite puis par EAD."
    )
    top_migrations = build_top_strong_migrations(
        staged,
        source_rating=source_rating,
    )
    if top_migrations.empty:
        st.success("Aucune migration forte detectee.")
    else:
        display_top = top_migrations.copy()
        display_top["ead"] = display_top["ead"].map(format_currency)
        for column in ["pd_12m", "pd_lifetime", "lgd"]:
            display_top[column] = display_top[column].map(
                lambda value: "-" if pd.isna(value) else f"{value:.2%}"
            )
        st.dataframe(display_top, width="stretch", hide_index=True)

    with st.expander("Consulter les resultats de staging ligne a ligne", expanded=False):
        st.dataframe(
            staged[
                [
                    "loan_id",
                    "client_id",
                    "initial_stage",
                    "previous_stage",
                    "stage",
                    "transition_rule",
                    "probation_status",
                    "cure_period_months",
                    "stage_reason",
                    "stage_comment",
                    "days_past_due",
                    "origination_rating",
                    "previous_rating",
                    "current_rating",
                    "ead",
                ]
            ],
            width="stretch",
            hide_index=True,
        )


def render_data_quality_dashboard(
    portfolio: pd.DataFrame,
    findings: pd.DataFrame,
    findings_summary: pd.DataFrame,
    quality_metrics: dict[str, float | int],
    dimension_summary: pd.DataFrame,
) -> None:
    """Render a BCBS 239-inspired data quality management view."""
    st.subheader("Data Quality - vue de pilotage")
    st.write(
        "Evaluation pedagogique de la qualite des donnees selon des dimensions inspirees de BCBS 239 : "
        "completude, validite, coherence, exactitude et integrite."
    )
    st.caption(
        "Cette vue ne constitue pas une evaluation complete de conformite BCBS 239. "
        "La ponctualite, la tracabilite des sources et les controles d'agregation ne sont pas encore modelises."
    )

    render_kpi_panel(
        "Synthese de la qualite des donnees",
        [
            (
                "Score qualite global",
                f"{float(quality_metrics['quality_score']):.2f}%",
                "8 controles automatises",
            ),
            (
                "Expositions affectees",
                f"{int(quality_metrics['impacted_exposure_count']):,}".replace(",", " "),
                f"{float(quality_metrics['impacted_exposure_rate']):.1%} du portefeuille",
            ),
            (
                "Anomalies critiques",
                str(int(quality_metrics["critical_issue_count"])),
                f"{int(quality_metrics['critical_exposure_count'])} exposition(s)",
            ),
            (
                "EAD affectee",
                format_compact_currency(float(quality_metrics["impacted_ead"])),
                f"{float(quality_metrics['impacted_ead_rate']):.1%} de l'EAD",
            ),
        ],
    )

    st.markdown("#### Evaluation par dimension")
    evaluated_dimensions = dimension_summary.loc[dimension_summary["score"].notna()].copy()
    dimension_colors = {
        "Maitrise": "#14664A",
        "A surveiller": "#F1A986",
        "Revue requise": "#B44B4B",
    }
    dimension_figure = px.bar(
        evaluated_dimensions,
        x="score",
        y="dimension",
        orientation="h",
        color="status",
        color_discrete_map=dimension_colors,
        text="score",
        title="Score de qualite par dimension",
        range_x=[0, 100],
    )
    dimension_figure.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="inside",
        hovertemplate="<b>%{y}</b><br>Score : %{x:.2f}%<extra></extra>",
    )
    dimension_figure.update_layout(
        height=360,
        xaxis_title="Score",
        yaxis_title="",
        legend_title_text="",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#0B2B46"),
        margin=dict(l=10, r=20, t=55, b=25),
    )
    st.plotly_chart(dimension_figure, width="stretch")

    freshness_row = dimension_summary.loc[dimension_summary["dimension"].eq("Fraicheur / ponctualite")]
    if not freshness_row.empty:
        st.info(
            "Fraicheur / ponctualite : non evaluee dans cette version. "
            "Une implementation BCBS 239 devrait controler les dates de reference, cut-off, delais d'alimentation "
            "et respect des frequences de reporting."
        )

    st.markdown("#### Diagnostic des anomalies")
    chart_left, chart_right = st.columns([1.05, 0.95])
    with chart_left:
        if findings_summary.empty:
            st.success("Aucune anomalie detectee sur les controles actifs.")
        else:
            issue_chart = findings_summary.sort_values("issue_count", ascending=True)
            issue_figure = px.bar(
                issue_chart,
                x="issue_count",
                y="description",
                orientation="h",
                title="Anomalies par type de controle",
                text="issue_count",
                color_discrete_sequence=["#0B2B46"],
            )
            issue_figure.update_layout(
                height=410,
                xaxis_title="Nombre d'anomalies",
                yaxis_title="",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=20, t=55, b=25),
            )
            st.plotly_chart(issue_figure, width="stretch")

    with chart_right:
        if findings.empty:
            st.success("Aucune EAD affectee.")
        else:
            issue_ead = (
                findings.merge(portfolio[["loan_id", "ead"]], on="loan_id", how="left")
                .assign(ead=lambda frame: pd.to_numeric(frame["ead"], errors="coerce").fillna(0).clip(lower=0))
                .groupby("description", as_index=False)
                .agg(impacted_ead=("ead", "sum"))
                .sort_values("impacted_ead", ascending=True)
            )
            ead_figure = px.bar(
                issue_ead,
                x="impacted_ead",
                y="description",
                orientation="h",
                title="EAD affectee par type d'anomalie",
                text_auto=".3s",
                color_discrete_sequence=["#F1A986"],
            )
            ead_figure.update_layout(
                height=410,
                xaxis_title="EAD affectee",
                yaxis_title="",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=20, t=55, b=25),
            )
            st.plotly_chart(ead_figure, width="stretch")

    st.markdown("#### Principes de lecture BCBS 239")
    principle_cols = st.columns(3)
    principles = [
        (
            "Completude",
            "Disponibilite des ratings, PD et LGD necessaires au calcul et au reporting des risques.",
        ),
        (
            "Exactitude et integrite",
            "Absence de valeurs invalides, conservation de la logique economique et fiabilite des donnees critiques.",
        ),
        (
            "Coherence",
            "Alignement entre defaut et DPD, collateral et LTV, ainsi qu'entre indicateurs relies.",
        ),
    ]
    for container, (title, description) in zip(principle_cols, principles):
        with container:
            st.markdown(
                f"""
                <div style="
                    min-height:150px;
                    padding:20px;
                    border:1px solid rgba(11,43,70,0.14);
                    border-radius:14px;
                    background:rgba(255,255,255,0.84);
                ">
                    <div style="color:#F1A986;font-size:0.72rem;font-weight:900;text-transform:uppercase;letter-spacing:0.08em;">
                        Dimension
                    </div>
                    <div style="margin:7px 0;color:#0B2B46;font-size:1.05rem;font-weight:900;">{title}</div>
                    <div style="color:#6D7885;font-size:0.86rem;line-height:1.5;">{description}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if not findings.empty:
        impacted_details = (
            findings.merge(portfolio[["loan_id", "product_type", "sector", "country", "ead"]], on="loan_id", how="left")
            .groupby(["loan_id", "product_type", "sector", "country", "ead"], as_index=False)
            .agg(
                anomaly_count=("check_code", "count"),
                anomaly_types=("description", lambda values: "; ".join(sorted(set(values)))),
            )
            .sort_values(["anomaly_count", "ead"], ascending=[False, False])
        )
        with st.expander("Afficher les expositions affectees", expanded=False):
            st.dataframe(impacted_details, width="stretch", hide_index=True)


def render_raw_data_quality_dashboard(
    portfolio: pd.DataFrame,
    findings: pd.DataFrame,
    findings_summary: pd.DataFrame,
    raw_tests: pd.DataFrame,
    raw_metrics: dict[str, float | int],
    dimension_summary: pd.DataFrame,
    column_profile: pd.DataFrame,
) -> None:
    """Render raw-dataset controls and BCBS 239-inspired quality statistics."""
    st.subheader("Data Quality - controles de la base source")
    st.write(
        "Les indicateurs proviennent de tests executes directement sur le portefeuille brut. "
        "Chaque controle dispose d'une population, d'un nombre d'exceptions, d'un seuil et d'un statut."
    )
    st.caption(
        "Lecture inspiree de BCBS 239 : completude, unicite, validite, coherence, exactitude et integrite. "
        "La ponctualite reste non evaluee faute de dates de reference et de chargement."
    )

    render_kpi_panel(
        "Controle de la base source",
        [
            (
                "Base controlee",
                f"{int(raw_metrics['row_count']):,}".replace(",", " "),
                f"{int(raw_metrics['column_count'])} champs bruts",
            ),
            (
                "Tests executes",
                str(int(raw_metrics["test_count"])),
                f"{int(raw_metrics['passed_test_count'])} controles conformes",
            ),
            (
                "Taux de conformite",
                f"{float(raw_metrics['test_pass_rate']):.1%}",
                "Part des tests respectant leur seuil",
            ),
            (
                "Echecs critiques",
                str(int(raw_metrics["critical_failed_test_count"])),
                f"{int(raw_metrics['failed_test_count'])} test(s) en echec",
            ),
        ],
    )

    st.markdown("#### Lecture par dimension BCBS 239")
    evaluated_dimensions = dimension_summary.loc[dimension_summary["score"].notna()].copy()
    dimension_figure = px.bar(
        evaluated_dimensions.sort_values("score"),
        x="score",
        y="dimension",
        orientation="h",
        color="status",
        color_discrete_map={
            "Maitrise": "#14664A",
            "A surveiller": "#F1A986",
            "Revue requise": "#B44B4B",
        },
        text="score",
        custom_data=["test_count", "failed_test_count", "exception_count"],
        range_x=[0, 100],
    )
    dimension_figure.update_traces(
        texttemplate="%{text:.2f}%",
        textposition="inside",
        hovertemplate=(
            "<b>%{y}</b><br>Score : %{x:.2f}%"
            "<br>Tests : %{customdata[0]}"
            "<br>Tests en echec : %{customdata[1]}"
            "<br>Exceptions : %{customdata[2]}<extra></extra>"
        ),
    )
    dimension_figure.update_layout(
        height=390,
        xaxis_title="Taux de conformite des observations controlees",
        yaxis_title="",
        legend_title_text="",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#0B2B46"),
        margin=dict(l=10, r=20, t=25, b=35),
    )
    st.plotly_chart(dimension_figure, width="stretch")
    st.info(
        "Ponctualite : non evaluee. Une analyse BCBS 239 complete necessite une date de reference, "
        "une date de chargement, les cut-offs attendus et les delais de production."
    )

    st.markdown("#### Synthese graphique des controles")
    evaluated_tests = raw_tests.loc[raw_tests["status"].ne("Non evalue")].copy()
    status_summary = (
        raw_tests.groupby("status", as_index=False)
        .agg(test_count=("test_id", "count"))
    )
    control_by_dimension = (
        evaluated_tests.groupby(["dimension", "status"], as_index=False)
        .agg(test_count=("test_id", "count"))
    )
    summary_left, summary_right = st.columns([0.85, 1.15])
    with summary_left:
        status_figure = px.pie(
            status_summary,
            names="status",
            values="test_count",
            hole=0.62,
            title="Statut du catalogue de controles",
            color="status",
            color_discrete_map={
                "Pass": "#14664A",
                "Fail": "#B44B4B",
                "Non evalue": "#6D7885",
            },
        )
        status_figure.update_traces(
            textposition="inside",
            textinfo="value+percent",
            hovertemplate="<b>%{label}</b><br>Tests : %{value}<extra></extra>",
        )
        status_figure.update_layout(
            height=380,
            legend_title_text="",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=55, b=20),
        )
        st.plotly_chart(status_figure, width="stretch")

    with summary_right:
        control_figure = px.bar(
            control_by_dimension,
            x="dimension",
            y="test_count",
            color="status",
            barmode="stack",
            text="test_count",
            title="Tests conformes et en echec par dimension",
            color_discrete_map={"Pass": "#14664A", "Fail": "#B44B4B"},
        )
        control_figure.update_traces(
            textposition="inside",
            hovertemplate="<b>%{x}</b><br>Tests : %{y}<extra></extra>",
        )
        control_figure.update_layout(
            height=380,
            xaxis_title="",
            yaxis_title="Nombre de tests",
            legend_title_text="",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=55, b=50),
        )
        st.plotly_chart(control_figure, width="stretch")

    test_view = raw_tests.copy()
    test_view["Taux d'exception"] = test_view["exception_rate"].map(
        lambda value: "Non evalue" if pd.isna(value) else f"{value:.2%}"
    )
    test_view["Seuil"] = test_view["threshold"].map(
        lambda value: "-" if pd.isna(value) else f"{value:.2%}"
    )
    test_view = test_view.rename(
        columns={
            "dimension": "Dimension",
            "control": "Controle",
            "field": "Champ",
            "severity": "Criticite",
            "population_count": "Population",
            "exception_count": "Exceptions",
            "status": "Statut",
            "recommendation": "Action recommandee",
        }
    )
    with st.expander("Consulter le catalogue detaille des tests", expanded=False):
        st.dataframe(
            test_view[
                [
                    "Dimension",
                    "Controle",
                    "Champ",
                    "Criticite",
                    "Population",
                    "Exceptions",
                    "Taux d'exception",
                    "Seuil",
                    "Statut",
                    "Action recommandee",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

    failed_tests = raw_tests.loc[raw_tests["status"].eq("Fail")].copy()
    st.markdown("#### Statistiques usuelles de qualite")
    chart_left, chart_right = st.columns(2)
    with chart_left:
        if failed_tests.empty:
            st.success("Tous les controles evaluables respectent leur seuil.")
        else:
            exception_chart = failed_tests.sort_values("exception_rate")
            exception_figure = px.bar(
                exception_chart,
                x="exception_rate",
                y="control",
                orientation="h",
                color="severity",
                color_discrete_map={"Critical": "#B44B4B", "Warning": "#F1A986"},
                text="exception_count",
                title="Taux d'exception des tests en echec",
            )
            exception_figure.update_layout(
                height=max(360, 38 * len(exception_chart)),
                xaxis_tickformat=".1%",
                xaxis_title="Taux d'exception",
                yaxis_title="",
                legend_title_text="",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(exception_figure, width="stretch")

    with chart_right:
        missing_profile = column_profile.loc[column_profile["missing_count"].gt(0)].sort_values("missing_rate")
        if missing_profile.empty:
            st.success("Aucune valeur manquante sur les champs de la base.")
        else:
            missing_figure = px.bar(
                missing_profile,
                x="missing_rate",
                y="field",
                orientation="h",
                text="missing_count",
                title="Completude par champ",
                color_discrete_sequence=["#0B2B46"],
            )
            missing_figure.update_layout(
                height=max(360, 38 * len(missing_profile)),
                xaxis_tickformat=".1%",
                xaxis_title="Taux de valeurs manquantes",
                yaxis_title="",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(missing_figure, width="stretch")

    with st.expander("Profil statistique des champs bruts", expanded=False):
        profile_view = column_profile.copy()
        profile_view["missing_rate"] = profile_view["missing_rate"].map(lambda value: f"{value:.2%}")
        profile_view["distinct_rate"] = profile_view["distinct_rate"].map(lambda value: f"{value:.2%}")
        st.dataframe(profile_view, width="stretch", hide_index=True)

    with st.expander("Anomalies detaillees par exposition", expanded=False):
        if findings.empty:
            st.success("Aucune anomalie ligne a ligne detectee.")
        else:
            impacted_details = (
                findings.merge(
                    portfolio[["loan_id", "product_type", "sector", "country", "ead"]],
                    on="loan_id",
                    how="left",
                )
                .groupby(["loan_id", "product_type", "sector", "country", "ead"], as_index=False)
                .agg(
                    anomaly_count=("check_code", "count"),
                    anomaly_types=("description", lambda values: "; ".join(sorted(set(values)))),
                )
                .sort_values(["anomaly_count", "ead"], ascending=[False, False])
            )
            st.dataframe(impacted_details, width="stretch", hide_index=True)


def render_contact_block() -> None:
    """Render the Auria contact call-to-action at the bottom of the home page."""
    st.markdown(
        """
        <section style="
            position: relative;
            overflow: hidden;
            margin-top: 34px;
            border-radius: 28px;
            padding: 42px 48px;
            color: #ffffff;
            background:
                radial-gradient(circle at 88% 12%, rgba(241, 169, 134, 0.18), transparent 12rem),
                linear-gradient(135deg, #061d31, #0b2b46);
            box-shadow: 0 24px 60px rgba(11, 43, 70, 0.16);
        ">
            <div style="
                position:absolute;
                width: 190px;
                height: 190px;
                border: 1px solid rgba(241, 169, 134, 0.50);
                border-radius: 50%;
                right: -46px;
                top: -82px;
                opacity: 0.75;
            "></div>
            <div style="
                position: relative;
                z-index: 1;
                display: grid;
                grid-template-columns: minmax(0, 1.2fr) minmax(300px, 0.8fr);
                gap: 34px;
                align-items: center;
            ">
                <div>
                    <div style="
                        color: #f1a986;
                        font-size: 0.78rem;
                        font-weight: 900;
                        letter-spacing: 0.08em;
                        text-transform: uppercase;
                        margin-bottom: 14px;
                    ">Auria Advisory</div>
                    <div style="
                        font-family: Georgia, 'Times New Roman', serif;
                        font-size: clamp(2.4rem, 5vw, 4.2rem);
                        line-height: 0.95;
                        font-weight: 800;
                        margin-bottom: 24px;
                    ">Nous contacter</div>
                    <p style="
                        max-width: 720px;
                        margin: 0;
                        color: rgba(255,255,255,0.86);
                        font-size: 1rem;
                        line-height: 1.75;
                    ">
                        Pour structurer une trajectoire de validation reglementaire PD,
                        echanger sur vos enjeux de gouvernance modele, de backtesting
                        ou de mise en conformite, parlons de votre contexte.
                    </p>
                </div>
                <div style="
                    border: 1px solid rgba(255,255,255,0.18);
                    border-radius: 22px;
                    background: rgba(255,255,255,0.12);
                    padding: 16px;
                    backdrop-filter: blur(12px);
                ">
                    <a href="https://auria-advisory.fr/" target="_blank" style="
                        display:flex;
                        align-items:center;
                        justify-content:space-between;
                        gap:16px;
                        min-height: 44px;
                        border-radius: 999px;
                        padding: 0 18px;
                        margin-bottom: 12px;
                        color:#0b2b46;
                        background:#f4f5f6;
                        text-decoration:none;
                        font-weight:850;
                    ">
                        <span>Site internet</span>
                        <span>auria-advisory.fr</span>
                    </a>
                    <a href="https://www.linkedin.com/company/auria-advisory/" target="_blank" style="
                        display:flex;
                        align-items:center;
                        justify-content:space-between;
                        gap:16px;
                        min-height: 44px;
                        border-radius: 999px;
                        padding: 0 18px;
                        color:#0b2b46;
                        background:#f4f5f6;
                        text-decoration:none;
                        font-weight:850;
                    ">
                        <span>LinkedIn</span>
                        <span>Suivre nos actualites</span>
                    </a>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_scenario_parameter_cards(scenario_parameters: pd.DataFrame) -> None:
    """Render macro scenario assumptions using the shared Auria card style."""
    scenario_palette = {
        "Baseline": ("#0B2B46", "Scenario central"),
        "Downside": ("#F1A986", "Scenario de stress"),
        "Upside": ("#14664A", "Scenario favorable"),
    }
    scenario_columns = st.columns(max(len(scenario_parameters), 1))
    for column, (_, row) in zip(scenario_columns, scenario_parameters.iterrows(), strict=False):
        scenario_name = str(row["scenario"])
        accent_color, scenario_caption = scenario_palette.get(
            scenario_name,
            ("#6D7885", "Scenario macroeconomique"),
        )
        with column:
            st.markdown(
                f"""
                <div style="
                    min-height:154px;
                    border:1px solid rgba(11,43,70,0.14);
                    border-top:5px solid {accent_color};
                    border-radius:18px;
                    background:rgba(255,255,255,0.88);
                    box-shadow:0 18px 44px rgba(11,43,70,0.10);
                    padding:18px;
                ">
                    <div style="color:#6d7885;font-size:0.74rem;font-weight:850;
                        letter-spacing:0.07em;text-transform:uppercase;">{scenario_caption}</div>
                    <div style="color:#0b2b46;font-size:1.35rem;font-weight:850;
                        margin:4px 0 14px;">{scenario_name}</div>
                    <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
                        gap:10px;color:#0b2b46;">
                        <div><strong>{float(row["weight"]):.0%}</strong><br>
                            <span style="font-size:0.75rem;color:#6d7885;">Ponderation</span></div>
                        <div><strong>x{float(row["pd_multiplier"]):.2f}</strong><br>
                            <span style="font-size:0.75rem;color:#6d7885;">PD</span></div>
                        <div><strong>x{float(row["lgd_multiplier"]):.2f}</strong><br>
                            <span style="font-size:0.75rem;color:#6d7885;">LGD</span></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_macro_scenarios(
    scenario_parameters: pd.DataFrame,
    scenario_weights_valid: bool,
    scenario_summary: pd.DataFrame,
    scenario_metrics: dict[str, float],
    downside_by_stage: pd.DataFrame,
) -> None:
    """Render the macro scenarios tab."""
    st.subheader("Macro Scenarios")
    st.write("Les ponderations et multiplicateurs sont modifiables dans la barre laterale.")
    total_weight = scenario_parameters["weight"].sum()
    if scenario_weights_valid:
        st.success(f"Somme des ponderations : {total_weight:.0%}")
    else:
        st.error(f"Somme des ponderations : {total_weight:.0%}. La somme doit etre egale a 100%.")

    st.markdown("#### Hypotheses appliquees")
    render_scenario_parameter_cards(scenario_parameters)

    with st.expander("Voir le detail des parametres"):
        display_params = scenario_parameters.copy()
        display_params["weight"] = display_params["weight"].map(lambda value: f"{value:.0%}")
        st.dataframe(display_params, width="stretch", hide_index=True)

    st.markdown("#### Resultats ECL par scenario")
    scenario_kpis = [
        (
            "ECL baseline",
            format_compact_currency(float(scenario_metrics["ecl_baseline"])),
            "Hypothese macroeconomique centrale",
        ),
        (
            "ECL downside",
            format_compact_currency(float(scenario_metrics["ecl_downside"])),
            "Impact du scenario de stress",
        ),
        (
            "ECL upside",
            format_compact_currency(float(scenario_metrics["ecl_upside"])),
            "Impact du scenario favorable",
        ),
        (
            "ECL ponderee",
            format_compact_currency(float(scenario_metrics["ecl_weighted"])),
            "Moyenne selon les ponderations",
        ),
    ]
    impact_kpis = [
        (
            "Impact downside vs baseline",
            format_compact_currency(float(scenario_metrics["downside_impact_amount"])),
            (
                f"{'Hausse' if float(scenario_metrics['downside_impact_amount']) >= 0 else 'Baisse'} "
                f"de {abs(float(scenario_metrics['downside_impact_pct'])):.2%}"
            ),
        ),
        (
            "Impact ECL ponderee vs baseline",
            format_compact_currency(float(scenario_metrics["weighted_impact_amount"])),
            (
                f"{'Hausse' if float(scenario_metrics['weighted_impact_amount']) >= 0 else 'Baisse'} "
                f"de {abs(float(scenario_metrics['weighted_impact_pct'])):.2%}"
            ),
        ),
    ]
    render_kpi_panel(
        "Synthese des scenarios macroeconomiques",
        scenario_kpis,
        impact_kpis,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(px.bar(scenario_summary, x="scenario", y="ecl", title="ECL par scenario", text_auto=".2s"), width="stretch")
        comparison = pd.DataFrame(
            [
                {"metric": "Baseline", "ecl": scenario_metrics["ecl_baseline"]},
                {"metric": "Weighted ECL", "ecl": scenario_metrics["ecl_weighted"]},
            ]
        )
        st.plotly_chart(px.bar(comparison, x="metric", y="ecl", title="Baseline vs weighted ECL", text_auto=".2s"), width="stretch")
    with col2:
        st.plotly_chart(
            px.bar(scenario_summary, x="scenario", y="weighted_ecl_contribution", title="Contribution ponderee par scenario", text_auto=".2s"),
            width="stretch",
        )
        st.plotly_chart(
            px.bar(downside_by_stage, x="stage", y="downside_impact_amount", title="Impact downside par stage", text_auto=".2s"),
            width="stretch",
        )

    st.write("Resultats par scenario")
    st.dataframe(scenario_summary, width="stretch")


def render_overlay_rule_cards(overlay_parameters: pd.DataFrame) -> None:
    """Render active overlay rules as French Auria-style governance cards."""
    french_content = {
        "Commercial Real Estate Stress": {
            "scope": "Expositions du secteur immobilier commercial.",
            "comment": (
                "Ajustement de prudence appliqué aux actifs immobiliers commerciaux "
                "dans un contexte d'incertitude sur les valorisations."
            ),
        },
        "SME Energy Sensitivity": {
            "scope": "Financements PME appartenant au secteur de l'énergie.",
            "comment": (
                "Ajustement expert reflétant la sensibilité des PME du secteur énergétique "
                "à la volatilité des coûts et des conditions de marché."
            ),
        },
        "Data Quality Uncertainty": {
            "scope": "Expositions présentant une anomalie critique de qualité des données.",
            "comment": (
                "Marge de prudence destinée à couvrir l'incertitude liée à des données "
                "manquantes ou invalides susceptibles d'affecter la fiabilité de l'ECL."
            ),
        },
        "Stage 2 Prudence Overlay": {
            "scope": "Ensemble des expositions classées en Stage 2.",
            "comment": (
                "Prudence complémentaire sur les contrats présentant une augmentation "
                "significative du risque de crédit."
            ),
        },
        "Stage 3 Recovery Risk": {
            "scope": "Ensemble des expositions classées en Stage 3.",
            "comment": (
                "Ajustement couvrant l'incertitude sur les perspectives de recouvrement "
                "des expositions en défaut."
            ),
        },
    }
    fallback_scopes = {
        "sector": "Périmètre sectoriel défini par la règle.",
        "product_sector": "Périmètre combinant produit et secteur.",
        "country": "Périmètre géographique défini par la règle.",
        "data_quality": "Expositions présentant une incertitude de qualité des données.",
        "expert_global": "Ensemble du portefeuille.",
        "stage": "Expositions appartenant au stage ciblé.",
    }

    cards = []
    for _, overlay in overlay_parameters.iterrows():
        overlay_name = str(overlay.get("name", "Overlay"))
        translated = french_content.get(overlay_name, {})
        scope = translated.get(
            "scope",
            fallback_scopes.get(
                str(overlay.get("overlay_type", "")),
                str(overlay.get("scope", "Périmètre à préciser.")),
            ),
        )
        comment = translated.get(
            "comment",
            str(overlay.get("justification", "Justification métier à documenter.")),
        )
        rate = float(overlay.get("rate", 0))
        rate_tooltip = escape(
            f"Taux de {rate:.0%} appliqué à l'ECL avant overlay des expositions "
            f"entrant dans le périmètre de {overlay_name}.",
            quote=True,
        )
        cards.append(
            dedent(
                f"""
                <article class="overlay-rule-card">
                    <div class="overlay-rule-heading">
                        <div class="overlay-rule-name">{overlay_name}</div>
                        <div class="overlay-rule-rate" title="{rate_tooltip}">
                            {rate:.0%}<span class="overlay-rate-info" title="{rate_tooltip}">i</span>
                        </div>
                    </div>
                    <div class="overlay-rule-label">Périmètre concerné</div>
                    <div class="overlay-rule-scope">{scope}</div>
                    <div class="overlay-rule-label">Commentaire métier</div>
                    <div class="overlay-rule-comment">{comment}</div>
                </article>
                """
            ).strip()
        )

    if not cards:
        st.info("Aucun overlay n'est activé pour ce run.")
        return
    overlay_cards_html = (
        '<section class="overlay-rule-grid">'
        + "".join(cards)
        + "</section>"
    )
    st.markdown(overlay_cards_html, unsafe_allow_html=True)


def render_management_overlays(
    overlay_parameters: pd.DataFrame,
    overlay_summary: pd.DataFrame,
    overlay_results: pd.DataFrame,
    overlay_metrics: dict[str, float | str],
    overlay_waterfall: pd.DataFrame,
) -> None:
    """Render management overlay controls and results."""
    st.subheader("Management Overlays")
    st.write("Les overlays predefinis sont activables dans la barre laterale. Les impacts sont calcules sur l'ECL avant overlay.")
    st.markdown("#### Règles des overlays actifs")
    render_overlay_rule_cards(overlay_parameters)

    render_kpi_panel(
        "Synthese des ajustements manageriaux",
        [
            (
                "ECL avant overlay",
                format_compact_currency(float(overlay_metrics["ecl_before_overlay"])),
                "ECL ponderee avant ajustement",
            ),
            (
                "Montant des overlays",
                format_compact_currency(float(overlay_metrics["total_overlay_amount"])),
                "Ajustement manageriel total",
            ),
            (
                "ECL apres overlay",
                format_compact_currency(float(overlay_metrics["ecl_after_overlay"])),
                "ECL finale apres ajustement",
            ),
            (
                "Variation",
                f"{float(overlay_metrics['overlay_variation_pct']):.2%}",
                "Impact relatif sur l'ECL",
            ),
        ],
        [
            (
                "Principal overlay contributeur",
                str(overlay_metrics["top_overlay_contributor"]),
                "Overlay generant le montant d'ajustement le plus eleve",
            )
        ],
    )

    stage_filter = st.multiselect("Filtrer par stage", sorted(overlay_results["stage"].dropna().unique()))
    product_filter = st.multiselect("Filtrer par produit", sorted(overlay_results["product_type"].dropna().unique()))
    sector_filter = st.multiselect("Filtrer par secteur", sorted(overlay_results["sector"].dropna().unique()))
    country_filter = st.multiselect("Filtrer par pays", sorted(overlay_results["country"].dropna().unique()))
    filtered = overlay_results.copy()
    if stage_filter:
        filtered = filtered[filtered["stage"].isin(stage_filter)]
    if product_filter:
        filtered = filtered[filtered["product_type"].isin(product_filter)]
    if sector_filter:
        filtered = filtered[filtered["sector"].isin(sector_filter)]
    if country_filter:
        filtered = filtered[filtered["country"].isin(country_filter)]

    col_left, col_right = st.columns(2)
    with col_left:
        st.plotly_chart(
            px.bar(overlay_summary, x="overlay_type", y="overlay_amount", title="Montant d'overlay par type", text_auto=".2s"),
            width="stretch",
        )
        by_stage = filtered.groupby("stage", as_index=False)["overlay_amount"].sum()
        st.plotly_chart(px.bar(by_stage, x="stage", y="overlay_amount", title="Montant d'overlay par stage", text_auto=".2s"), width="stretch")
    with col_right:
        waterfall_fig = go.Figure(
            go.Waterfall(
                x=overlay_waterfall["step"],
                y=overlay_waterfall["amount"],
                measure=overlay_waterfall["measure"],
            )
        )
        waterfall_fig.update_layout(title="Waterfall ECL avant overlay -> ECL apres overlay")
        st.plotly_chart(
            waterfall_fig,
            width="stretch",
        )
        top_impacted = filtered.sort_values("overlay_amount", ascending=False).head(10)
        st.write("Top 10 expositions les plus impactees")
        st.dataframe(top_impacted[["loan_id", "client_id", "stage", "product_type", "sector", "ecl_before_overlay", "overlay_amount", "ecl_after_overlay", "overlay_names"]], width="stretch")


def render_audit_trail(audit_trail: dict[str, pd.DataFrame]) -> None:
    """Render detailed audit trail sections in a more user-friendly audit view."""
    st.subheader("Audit Trail")
    st.write(
        "Vue de tracabilite du run : hypotheses appliquees, parametres, alertes et principaux resultats. "
        "Les donnees detaillees restent disponibles dans l'export Excel."
    )

    run_summary = audit_trail.get("run_summary", pd.DataFrame())
    run_values = _audit_section_to_dict(run_summary, "field", "value")
    render_light_kpi_panel(
        "Identification et resultats du run",
        [
            (
                "Run ID",
                str(run_values.get("run_id", "N/A")),
                str(run_values.get("app_version", "")),
            ),
            (
                "Expositions",
                str(run_values.get("exposure_count", "N/A")),
                "Traitees dans le run",
            ),
            (
                "EAD totale",
                format_compact_currency(float(run_values.get("total_ead", 0) or 0)),
                "Portefeuille synthetique",
            ),
            (
                "ECL finale",
                format_compact_currency(float(run_values.get("final_ecl_after_overlay", 0) or 0)),
                "Apres scenarios et overlays",
            ),
        ],
    )

    st.info(str(run_values.get("demo_disclaimer", DEMO_DISCLAIMER_FR)))

    st.markdown("#### Points de controle prioritaires")
    render_kpi_panel(
        "Lecture synthetique des controles",
        [
            (
                "Anomalies data quality",
                str(run_values.get("data_quality_issue_count", 0)),
                "Exceptions detectees",
            ),
            (
                "Cas a revoir",
                str(run_values.get("review_required_count", 0)),
                "Expositions avec review required",
            ),
            (
                "Alertes metier",
                str(run_values.get("business_alert_count", 0)),
                "Controles de coherence",
            ),
            (
                "Alertes critiques",
                str(run_values.get("business_critical_alert_count", 0)),
                "Points a prioriser",
            ),
        ],
    )

    st.markdown("#### Arbre de decision du staging")
    st.caption("Les criteres de defaut priment sur les indicateurs SICR et les regles de retour vers un stage inferieur.")
    render_staging_decision_tree()

    st.markdown("#### Formules de calcul ECL")
    render_ecl_formula_view()

    risk_summary_table = audit_trail.get("risk_parameter_summary", pd.DataFrame())
    risk_values = _audit_section_to_dict(
        risk_summary_table,
        "metric",
        "value",
    )
    if risk_values:
        st.markdown("#### Parametres de risque et PD lifetime")
        render_light_kpi_panel(
            "Hypotheses de risque du run",
            [
                (
                    "PD 12 mois",
                    f"{float(risk_values.get('pd_12m_ead_weighted', 0)):.2%}",
                    "Moyenne ponderee par l'EAD",
                ),
                (
                    "PD lifetime",
                    f"{float(risk_values.get('pd_lifetime_ead_weighted', 0)):.2%}",
                    "PD cumulative ponderee",
                ),
                (
                    "LGD",
                    f"{float(risk_values.get('lgd_ead_weighted', 0)):.2%}",
                    "Moyenne ponderee par l'EAD",
                ),
                (
                    "Maturite",
                    f"{float(risk_values.get('average_residual_maturity_months', 0)):.0f} mois",
                    "Maturite residuelle moyenne",
                ),
            ],
        )
        st.latex(
            r"\mathrm{PD}_{cum}(t)=1-\left(1-\mathrm{PD}_{12m}\right)^t"
        )

    lgd_summary_table = audit_trail.get("lgd_summary", pd.DataFrame())
    lgd_values = _audit_section_to_dict(
        lgd_summary_table,
        "metric",
        "value",
    )
    if lgd_values:
        st.markdown("#### LGD, suretes et recouvrements")
        render_light_kpi_panel(
            "Hypotheses de recouvrement du run",
            [
                (
                    "LGD moyenne",
                    f"{float(lgd_values.get('lgd_ead_weighted', 0)):.1%}",
                    "Ponderee par l'EAD",
                ),
                (
                    "LGD garantie",
                    f"{float(lgd_values.get('lgd_secured_ead_weighted', 0)):.1%}",
                    "Expositions avec collateral",
                ),
                (
                    "LGD non garantie",
                    f"{float(lgd_values.get('lgd_unsecured_ead_weighted', 0)):.1%}",
                    "Expositions sans collateral",
                ),
                (
                    "Delai de recovery",
                    f"{float(lgd_values.get('average_recovery_delay_months', 0)):.0f} mois",
                    "Moyenne du portefeuille",
                ),
            ],
        )
        st.latex(
            r"\mathrm{LGD}=1-\frac{\mathrm{PV}("
            r"\mathrm{recouvrements}-\mathrm{couts})}{\mathrm{EAD}}"
        )
        lgd_sensitivity = audit_trail.get("lgd_sensitivity", pd.DataFrame())
        if (
            lgd_sensitivity is not None
            and not lgd_sensitivity.empty
            and {"scenario", "lgd"}.issubset(lgd_sensitivity.columns)
        ):
            lgd_audit_figure = px.bar(
                lgd_sensitivity,
                x="scenario",
                y="lgd",
                color="scenario",
                text_auto=".1%",
                title="Sensibilite des hypotheses de recouvrement",
                color_discrete_map={
                    "Baseline": "#8298AA",
                    "Downside": "#0B2B46",
                    "Upside": "#F1A986",
                },
            )
            lgd_audit_figure.update_layout(
                height=330,
                showlegend=False,
                yaxis_tickformat=".0%",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(lgd_audit_figure, width="stretch")

    scenario_parameters = audit_trail.get("scenario_parameters", pd.DataFrame())
    scenario_results = audit_trail.get("scenario_results", pd.DataFrame())
    st.markdown("#### Scenarios macroeconomiques")
    if scenario_parameters is not None and not scenario_parameters.empty:
        render_scenario_parameter_cards(scenario_parameters)
    else:
        st.caption("Parametres de scenarios non disponibles.")
    if (
        scenario_results is not None
        and not scenario_results.empty
        and {"scenario", "ecl"}.issubset(scenario_results.columns)
    ):
        scenario_figure = px.bar(
            scenario_results,
            x="scenario",
            y="ecl",
            color="scenario",
            text_auto=".3s",
            title="ECL par scenario",
            color_discrete_map={
                "Baseline": "#0B2B46",
                "Downside": "#F1A986",
                "Upside": "#14664A",
            },
        )
        scenario_figure.update_layout(
            height=340,
            showlegend=False,
            xaxis_title="",
            yaxis_title="ECL",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(scenario_figure, width="stretch")

    st.markdown("#### Overlays manageriaux")
    overlay_parameters = audit_trail.get("overlay_parameters", pd.DataFrame())
    overlay_summary = audit_trail.get("overlay_summary", pd.DataFrame())
    if overlay_parameters is not None and not overlay_parameters.empty:
        render_overlay_rule_cards(overlay_parameters)
    else:
        st.caption("Aucun overlay actif.")
    if (
        overlay_summary is not None
        and not overlay_summary.empty
        and {"overlay_name", "overlay_amount"}.issubset(overlay_summary.columns)
    ):
        active_overlays = overlay_summary.loc[overlay_summary["overlay_amount"] > 0].copy()
        if not active_overlays.empty:
            overlay_figure = px.bar(
                active_overlays.sort_values("overlay_amount"),
                x="overlay_amount",
                y="overlay_name",
                orientation="h",
                text_auto=".3s",
                title="Impact monetaire des overlays",
                color_discrete_sequence=["#F1A986"],
            )
            overlay_figure.update_layout(
                height=max(310, 55 * len(active_overlays)),
                xaxis_title="Montant d'overlay",
                yaxis_title="",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(overlay_figure, width="stretch")

    st.markdown("#### Transitions de stage et periodes de cure")
    transition_summary = audit_trail.get("staging_transition_summary", pd.DataFrame())
    if transition_summary is not None and not transition_summary.empty:
        stage_colors = {
            "Stage 1": "#8298AA",
            "Stage 2": "#F1A986",
            "Stage 3": "#0B2B46",
        }
        transition_tabs = st.tabs(
            [
                "Stage final 1",
                "Stage final 2",
                "Stage final 3",
            ]
        )
        for tab, final_stage in zip(
            transition_tabs,
            ["Stage 1", "Stage 2", "Stage 3"],
            strict=False,
        ):
            stage_transitions = transition_summary.loc[
                transition_summary["stage"].eq(final_stage)
            ].copy()
            with tab:
                if stage_transitions.empty:
                    st.info(f"Aucune transition vers {final_stage}.")
                    continue
                stage_transitions["transition_label"] = (
                    stage_transitions["transition_rule"]
                    .astype(str)
                    .str.replace(" maintained during ", " maintenu - ", regex=False)
                    .str.replace(" maintained", " maintenu", regex=False)
                )
                transition_chart = px.bar(
                    stage_transitions,
                    x="exposure_count",
                    y="transition_label",
                    color="probation_status",
                    orientation="h",
                    text="exposure_count",
                    custom_data=["previous_stage", "ead", "probation_status"],
                    title=f"Transitions et statuts de cure vers {final_stage}",
                    color_discrete_sequence=[
                        stage_colors[final_stage],
                        "#F1A986",
                        "#8298AA",
                        "#14664A",
                        "#6D7885",
                    ],
                )
                transition_chart.update_traces(
                    textposition="inside",
                    hovertemplate=(
                        "<b>%{y}</b><br>Expositions : %{x}<br>"
                        "Stage precedent : %{customdata[0]}<br>"
                        "EAD : %{customdata[1]:,.0f} EUR<br>"
                        "Cure / probation : %{customdata[2]}<extra></extra>"
                    ),
                    marker_line_color=stage_colors[final_stage],
                    marker_line_width=1,
                )
                transition_chart.update_layout(
                    height=max(390, 72 * stage_transitions["transition_label"].nunique()),
                    barmode="stack",
                    xaxis_title="Nombre d'expositions",
                    yaxis_title="",
                    legend=dict(
                        title_text="Cure / probation",
                        orientation="h",
                        yanchor="top",
                        y=-0.20,
                        xanchor="left",
                        x=0,
                    ),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=15, r=20, t=60, b=110),
                )
                transition_chart.update_yaxes(
                    categoryorder="total ascending",
                    automargin=True,
                )
                st.plotly_chart(transition_chart, width="stretch")
    else:
        st.caption("Synthese des transitions non disponible.")

    st.markdown("#### Alertes et contributeurs")
    alert_left, alert_right = st.columns([1.1, 0.9])
    with alert_left:
        critical_alerts = audit_trail.get("critical_business_alerts", pd.DataFrame())
        if critical_alerts is not None and not critical_alerts.empty:
            st.warning("Alertes critiques de coherence metier")
            for _, alert in critical_alerts.head(5).iterrows():
                render_governance_card(
                    f"Exposition {alert.get('loan_id', '')}",
                    str(alert.get("rule", "Alerte critique")),
                    (
                        f"Recommandation : {alert.get('recommendation', 'Revue requise.')} "
                        f"Impact potentiel : {alert.get('potential_impact', 'A evaluer.')}"
                    ),
                )
            if len(critical_alerts) > 5:
                st.caption(
                    f"{len(critical_alerts) - 5} alerte(s) critique(s) supplementaire(s) "
                    "sont disponibles dans l'export."
                )
        else:
            st.success("Aucune alerte critique de coherence metier dans ce run.")
    with alert_right:
        top_contributors = audit_trail.get("top_contributors", pd.DataFrame())
        if top_contributors is not None and not top_contributors.empty:
            display_top = top_contributors.head(5).copy()
            contributor_label = (
                "loan_id"
                if "loan_id" in display_top.columns
                else display_top.columns[0]
            )
            contributor_figure = px.bar(
                display_top.sort_values("ecl"),
                x="ecl",
                y=contributor_label,
                orientation="h",
                text_auto=".3s",
                title="Top 5 contributeurs ECL",
                color_discrete_sequence=["#0B2B46"],
            )
            contributor_figure.update_layout(
                height=350,
                xaxis_title="ECL",
                yaxis_title="",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(contributor_figure, width="stretch")


def _audit_section_to_dict(table: pd.DataFrame, key_col: str, value_col: str) -> dict:
    """Convert a two-column audit table into a dictionary."""
    if table is None or table.empty or key_col not in table or value_col not in table:
        return {}
    return dict(zip(table[key_col], table[value_col]))


def _render_audit_bullets(title: str, table: pd.DataFrame | None, columns: list[str], limit: int = 8) -> None:
    """Render an audit table as readable bullet points."""
    st.write(f"**{title}**")
    if table is None or table.empty:
        st.caption("Non disponible.")
        return
    available_columns = [column for column in columns if column in table.columns]
    if not available_columns:
        st.dataframe(table.head(limit), width="stretch", hide_index=True)
        return
    for _, row in table.head(limit).iterrows():
        parts = [f"{column}: {row[column]}" for column in available_columns if pd.notna(row[column])]
        st.write(f"- {' | '.join(parts)}")
    if len(table) > limit:
        st.caption(f"{len(table) - limit} ligne(s) supplementaire(s) disponibles dans les details auditables.")


def render_risk_parameters(
    portfolio: pd.DataFrame,
    summary: dict[str, float | str],
    term_structure: pd.DataFrame,
    curve_by_stage: pd.DataFrame,
    lgd_summary: dict[str, float | str],
    lgd_by_stage: pd.DataFrame,
    lgd_by_product: pd.DataFrame,
    lgd_by_collateral: pd.DataFrame,
    lgd_sensitivity: pd.DataFrame,
    lgd_waterfall: pd.DataFrame,
) -> None:
    """Render the methodological view of PD, recovery-based LGD and future EAD."""
    st.subheader("Parametres de risque")
    st.write(
        "Lecture methodologique des probabilites de defaut et de la LGD utilisees "
        "dans le calcul ECL. La V2 introduit une courbe de PD lifetime cumulative "
        "derivee de la PD 12 mois et de la maturite residuelle."
    )
    render_kpi_panel(
        "Synthese des parametres de risque",
        [
            (
                "PD 12 mois",
                f"{float(summary['pd_12m_ead_weighted']):.2%}",
                "Moyenne ponderee par l'EAD",
            ),
            (
                "PD lifetime",
                f"{float(summary['pd_lifetime_ead_weighted']):.2%}",
                "Moyenne cumulative ponderee par l'EAD",
            ),
            (
                "Multiplicateur lifetime",
                f"x{float(summary['pd_lifetime_multiplier']):.2f}",
                "PD lifetime / PD 12 mois",
            ),
            (
                "LGD",
                f"{float(summary['lgd_ead_weighted']):.2%}",
                "Moyenne ponderee par l'EAD",
            ),
        ],
        [
            (
                "Maturite residuelle moyenne",
                f"{float(summary['average_residual_maturity_months']):.0f} mois",
                "Horizon contractuel synthetique",
            ),
            (
                "Methode PD lifetime",
                "Taux de hasard constant",
                "Approche transparente et pedagogique",
            ),
        ],
    )

    with st.container(border=True):
        st.markdown("#### Construction de la PD lifetime")
        st.latex(
            r"\mathrm{PD}_{cum}(t)=1-\left(1-\mathrm{PD}_{12m}\right)^t"
        )
        st.caption(
            "t correspond a la maturite residuelle exprimee en annees. "
            "La PD marginale de chaque periode est la variation de PD cumulative. "
            "Un horizon minimal d'un an est retenu dans cette version pedagogique."
        )

    st.markdown("#### Courbe de PD lifetime par stage")
    if curve_by_stage.empty:
        st.info("Courbe de PD lifetime indisponible pour le perimetre selectionne.")
    else:
        curve_figure = px.line(
            curve_by_stage,
            x="year",
            y="cumulative_pd",
            color="stage",
            markers=True,
            labels={
                "year": "Horizon (annees)",
                "cumulative_pd": "PD cumulative",
                "stage": "Stage",
            },
            color_discrete_map={
                "Stage 1": "#8298AA",
                "Stage 2": "#F1A986",
                "Stage 3": "#0B2B46",
            },
        )
        curve_figure.update_layout(
            height=430,
            yaxis_tickformat=".1%",
            legend_title_text="",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=25, b=20),
        )
        st.plotly_chart(curve_figure, width="stretch")

    rating_data = portfolio.copy()
    for column in ["current_rating", "pd_12m", "pd_lifetime", "lgd", "ead"]:
        rating_data[column] = pd.to_numeric(rating_data[column], errors="coerce")
    rating_data = rating_data.dropna(
        subset=["current_rating", "pd_12m", "pd_lifetime"]
    )
    rating_records = []
    for rating, group in rating_data.groupby("current_rating"):
        ead = group["ead"].clip(lower=0).fillna(0.0)
        rating_records.append(
            {
                "current_rating": int(rating),
                "pd_12m": safe_divide(
                    float((group["pd_12m"] * ead).sum()),
                    float(ead.sum()),
                ),
                "pd_lifetime": safe_divide(
                    float((group["pd_lifetime"] * ead).sum()),
                    float(ead.sum()),
                ),
            }
        )
    rating_summary = pd.DataFrame(rating_records)

    left, right = st.columns(2)
    with left:
        if not rating_summary.empty:
            rating_long = rating_summary.melt(
                id_vars="current_rating",
                value_vars=["pd_12m", "pd_lifetime"],
                var_name="parameter",
                value_name="pd",
            )
            rating_figure = px.bar(
                rating_long,
                x="current_rating",
                y="pd",
                color="parameter",
                barmode="group",
                labels={
                    "current_rating": "Rating courant",
                    "pd": "Probabilite de defaut",
                    "parameter": "Parametre",
                },
                color_discrete_map={
                    "pd_12m": "#8298AA",
                    "pd_lifetime": "#0B2B46",
                },
                title="PD 12 mois et lifetime par rating",
            )
            rating_figure.update_layout(
                height=390,
                yaxis_tickformat=".1%",
                legend_title_text="",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(rating_figure, width="stretch")
    with right:
        distribution_figure = px.box(
            rating_data,
            x="stage",
            y="pd_lifetime",
            color="stage",
            points=False,
            title="Distribution des PD lifetime par stage",
            labels={"stage": "Stage", "pd_lifetime": "PD lifetime"},
            color_discrete_map={
                "Stage 1": "#8298AA",
                "Stage 2": "#F1A986",
                "Stage 3": "#0B2B46",
            },
        )
        distribution_figure.update_layout(
            height=390,
            showlegend=False,
            yaxis_tickformat=".1%",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(distribution_figure, width="stretch")

    st.markdown("#### PD marginales et exposition au risque")
    if not term_structure.empty:
        marginal_by_year = (
            term_structure.groupby("year", as_index=False)
            .agg(marginal_pd=("marginal_pd", "mean"), active_ead=("ead", "sum"))
        )
        marginal_figure = px.bar(
            marginal_by_year,
            x="year",
            y="marginal_pd",
            text_auto=".2%",
            labels={"year": "Annee", "marginal_pd": "PD marginale moyenne"},
            color_discrete_sequence=["#F1A986"],
        )
        marginal_figure.update_layout(
            height=350,
            yaxis_tickformat=".1%",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(marginal_figure, width="stretch")

    st.markdown("### LGD fondee sur les recouvrements")
    st.write(
        "La LGD est estimee a partir des garanties, des haircuts, des couts et "
        "delais de recouvrement, puis actualisee au taux d'interet effectif. "
        "Les expositions Stage 3 integrent des hypotheses de workout plus prudentes."
    )
    render_kpi_panel(
        "Synthese LGD et recouvrements",
        [
            (
                "LGD moyenne",
                f"{float(lgd_summary['lgd_ead_weighted']):.1%}",
                "Moyenne ponderee par l'EAD",
            ),
            (
                "LGD garantie",
                f"{float(lgd_summary['lgd_secured_ead_weighted']):.1%}",
                "Expositions avec collateral",
            ),
            (
                "LGD non garantie",
                f"{float(lgd_summary['lgd_unsecured_ead_weighted']):.1%}",
                "Expositions sans collateral",
            ),
            (
                "LGD Stage 3",
                f"{float(lgd_summary['lgd_stage3_ead_weighted']):.1%}",
                "Hypotheses de workout",
            ),
        ],
        [
            (
                "Recouvrements actualises",
                format_compact_currency(
                    float(lgd_summary["discounted_recovery_amount"])
                ),
                "Apres couts et actualisation",
            ),
            (
                "Taux de recouvrement",
                f"{float(lgd_summary['recovery_rate_ead_weighted']):.1%}",
                "Recouvrements actualises / EAD",
            ),
            (
                "Delai moyen",
                f"{float(lgd_summary['average_recovery_delay_months']):.0f} mois",
                "Horizon moyen de recouvrement",
            ),
        ],
    )

    with st.container(border=True):
        st.markdown("#### Formule pedagogique de la LGD")
        st.latex(
            r"\mathrm{LGD}=1-\frac{\mathrm{PV}("
            r"\mathrm{recouvrements\ garantis}+\mathrm{recouvrements\ non\ garantis}"
            r"-\mathrm{couts})}{\mathrm{EAD}}"
        )
        st.caption(
            "Les recouvrements sont plafonnes a l'EAD. Les haircuts, couts de "
            "liquidation, delais de recovery et taux de recouvrement non garanti "
            "sont des hypotheses synthetiques explicites."
        )

    lgd_left, lgd_right = st.columns(2)
    with lgd_left:
        if not lgd_by_stage.empty:
            stage_figure = px.bar(
                lgd_by_stage,
                x="stage",
                y="lgd",
                color="stage",
                text_auto=".1%",
                title="LGD moyenne par stage",
                labels={"stage": "Stage", "lgd": "LGD"},
                color_discrete_map={
                    "Stage 1": "#8298AA",
                    "Stage 2": "#F1A986",
                    "Stage 3": "#0B2B46",
                },
            )
            stage_figure.update_layout(
                height=390,
                showlegend=False,
                yaxis_tickformat=".0%",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(stage_figure, width="stretch")
    with lgd_right:
        if not lgd_by_collateral.empty:
            collateral_figure = px.bar(
                lgd_by_collateral.sort_values("lgd"),
                x="lgd",
                y="collateral_type",
                orientation="h",
                text_auto=".1%",
                title="LGD par type de surete",
                labels={
                    "collateral_type": "Type de surete",
                    "lgd": "LGD",
                },
                color_discrete_sequence=["#F1A986"],
            )
            collateral_figure.update_layout(
                height=390,
                xaxis_tickformat=".0%",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=45, b=20),
            )
            st.plotly_chart(collateral_figure, width="stretch")

    product_left, product_right = st.columns(2)
    with product_left:
        if not lgd_by_product.empty:
            product_figure = px.bar(
                lgd_by_product.sort_values("lgd"),
                x="product_type",
                y="lgd",
                text_auto=".1%",
                title="LGD par produit",
                labels={"product_type": "Produit", "lgd": "LGD"},
                color_discrete_sequence=["#0B2B46"],
            )
            product_figure.update_layout(
                height=390,
                yaxis_tickformat=".0%",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(product_figure, width="stretch")
    with product_right:
        if not lgd_sensitivity.empty:
            sensitivity_figure = px.bar(
                lgd_sensitivity,
                x="scenario",
                y="lgd",
                color="scenario",
                text_auto=".1%",
                title="Sensibilite de la LGD aux hypotheses de recovery",
                labels={"scenario": "Scenario", "lgd": "LGD"},
                color_discrete_map={
                    "Baseline": "#8298AA",
                    "Downside": "#0B2B46",
                    "Upside": "#F1A986",
                },
            )
            sensitivity_figure.update_layout(
                height=390,
                showlegend=False,
                yaxis_tickformat=".0%",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(sensitivity_figure, width="stretch")

    st.markdown("#### Cascade de recouvrement")
    if not lgd_waterfall.empty:
        waterfall_figure = go.Figure(
            go.Waterfall(
                x=lgd_waterfall["step"],
                y=lgd_waterfall["amount"],
                measure=lgd_waterfall["measure"],
                connector={"line": {"color": "#8298AA"}},
                increasing={"marker": {"color": "#F1A986"}},
                decreasing={"marker": {"color": "#8298AA"}},
                totals={"marker": {"color": "#0B2B46"}},
                text=[
                    format_compact_currency(float(value))
                    for value in lgd_waterfall["amount"]
                ],
                textposition="outside",
            )
        )
        waterfall_figure.update_layout(
            height=430,
            yaxis_title="Montant (EUR)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=25, b=20),
        )
        st.plotly_chart(waterfall_figure, width="stretch")

    st.markdown("#### Expositions aux LGD les plus elevees")
    top_lgd_columns = [
        "loan_id",
        "stage",
        "product_type",
        "ead",
        "collateral_type",
        "seniority",
        "collateral_value",
        "lgd_haircut_adjusted",
        "lgd_recovery_delay_adjusted",
        "discounted_recovery_amount",
        "lgd",
    ]
    available_top_lgd_columns = [
        column for column in top_lgd_columns if column in portfolio.columns
    ]
    top_lgd = portfolio.nlargest(10, "lgd")[available_top_lgd_columns].copy()
    st.dataframe(
        top_lgd,
        width="stretch",
        hide_index=True,
        column_config={
            "ead": st.column_config.NumberColumn("EAD", format="%.0f EUR"),
            "collateral_value": st.column_config.NumberColumn(
                "Valeur collateral",
                format="%.0f EUR",
            ),
            "discounted_recovery_amount": st.column_config.NumberColumn(
                "Recouvrement actualise",
                format="%.0f EUR",
            ),
            "lgd_haircut_adjusted": st.column_config.NumberColumn(
                "Haircut",
                format="%.1%%",
            ),
            "lgd": st.column_config.NumberColumn("LGD", format="%.1%%"),
            "lgd_recovery_delay_adjusted": st.column_config.NumberColumn(
                "Delai (mois)",
                format="%.0f",
            ),
        },
    )

    st.markdown("#### Hypotheses et prochaines evolutions")
    assumption_columns = st.columns(3)
    assumptions = [
        (
            "PD lifetime V2",
            LIFETIME_PD_METHOD,
            "Courbe cumulative et PD marginales derivees de la PD 12 mois.",
        ),
        (
            "LGD V2.1",
            LGD_METHOD,
            "Recouvrements garantis et non garantis, couts, delais et actualisation.",
        ),
        (
            "EAD - prochaine etape",
            "EAD constante",
            "Architecture prete pour amortissement, CCF, tirages futurs et prepayments.",
        ),
    ]
    for column, (label, value, detail) in zip(
        assumption_columns,
        assumptions,
        strict=False,
    ):
        with column:
            render_governance_card(label, value, detail)


def render_committee_summary_visual(
    committee_summary: str,
    metrics: dict[str, float],
    scenario_metrics: dict[str, float],
    overlay_metrics: dict[str, float | str],
    ecl_by_stage: pd.DataFrame,
    ecl_by_product: pd.DataFrame,
    ecl_by_sector: pd.DataFrame,
    scenario_summary: pd.DataFrame,
    overlay_summary: pd.DataFrame,
    business_summary: dict[str, float],
    top_contributors: pd.DataFrame,
    client_discussion_points: list[str],
    demo_profile: str,
    run_id: str,
) -> None:
    """Render the committee summary as a visual executive pack."""
    st.write(
        "Vue synthetique destinee a une lecture en comite : messages clefs, chiffres principaux, "
        "repartition des expositions et points de decision."
    )
    st.caption(DEMO_DISCLAIMER_FR)

    final_ecl = float(overlay_metrics["ecl_after_overlay"])
    final_coverage_ratio = safe_divide(final_ecl, float(metrics["total_ead"]))
    st.caption(f"{run_id} | {demo_profile}")
    render_kpi_panel(
        "Synthese executive du comite",
        [
            (
                "Expositions",
                f"{int(metrics['exposure_count']):,}".replace(",", " "),
                "Contrats analyses",
            ),
            (
                "EAD totale",
                format_compact_currency(metrics["total_ead"]),
                "Portefeuille synthetique",
            ),
            (
                "ECL finale",
                format_compact_currency(final_ecl),
                "Apres scenarios et overlays",
            ),
            (
                "Taux de couverture final",
                f"{final_coverage_ratio:.2%}",
                "ECL finale / EAD",
            ),
        ],
        [
            (
                "Impact scenarios",
                format_compact_currency(scenario_metrics["weighted_impact_amount"]),
                f"{scenario_metrics['weighted_impact_pct']:.2%} vs baseline",
            ),
            (
                "Impact overlays",
                format_compact_currency(float(overlay_metrics["total_overlay_amount"])),
                f"{overlay_metrics['overlay_variation_pct']:.2%} de l'ECL avant overlay",
            ),
            (
                "Score coherence",
                f"{business_summary['business_consistency_score']:.1%}",
                f"{int(business_summary['business_alert_count'])} alerte(s)",
            ),
            (
                "Cas a revoir",
                str(metrics["review_required_count"]),
                "Priorisation metier",
            ),
        ],
    )

    st.divider()
    st.markdown("#### Exposition et ECL par stage")
    stage_left, stage_right = st.columns([1.1, 0.9])
    with stage_left:
        stage_long = ecl_by_stage.melt(
            id_vars=["stage"],
            value_vars=["ead", "ecl"],
            var_name="metric",
            value_name="amount",
        )
        stage_long["metric"] = stage_long["metric"].map({"ead": "EAD", "ecl": "ECL"})
        stage_bar = px.bar(
            stage_long,
            x="stage",
            y="amount",
            color="metric",
            barmode="group",
            title="EAD et ECL par stage",
            text_auto=".2s",
            color_discrete_map={"EAD": "#0B2B46", "ECL": "#F1A986"},
        )
        stage_bar.update_layout(
            height=380,
            xaxis_title="",
            yaxis_title="Montant",
            legend_title_text="",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(stage_bar, width="stretch")
    with stage_right:
        coverage_fig = px.bar(
            ecl_by_stage,
            x="stage",
            y="coverage_ratio",
            title="Taux de couverture par stage",
            text_auto=".2%",
            color_discrete_sequence=["#0B2B46"],
        )
        coverage_fig.update_layout(
            height=380,
            xaxis_title="",
            yaxis_title="ECL / EAD",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(coverage_fig, width="stretch")

    st.markdown("#### Contributions principales")
    auria_contribution_colors = [
        "#0B2B46",
        "#F1A986",
        "#6D7885",
        "#14664A",
        "#8298AA",
        "#F7C6AE",
    ]
    contribution_left, contribution_right = st.columns(2)
    with contribution_left:
        product_share = _build_top_share_frame(ecl_by_product, "product_type", "ecl", top_n=5)
        product_fig = px.pie(
            product_share,
            names="label",
            values="amount",
            title="Part ECL par produit",
            color="label",
            color_discrete_sequence=auria_contribution_colors,
        )
        product_fig.update_traces(
            textposition="inside",
            textinfo="percent+label",
            marker=dict(line=dict(color="#FFFDF9", width=2)),
        )
        product_fig.update_layout(
            height=390,
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(product_fig, width="stretch")
    with contribution_right:
        sector_share = _build_top_share_frame(ecl_by_sector, "sector", "ecl", top_n=5)
        sector_fig = px.pie(
            sector_share,
            names="label",
            values="amount",
            title="Part ECL par secteur",
            color="label",
            color_discrete_sequence=auria_contribution_colors,
        )
        sector_fig.update_traces(
            textposition="inside",
            textinfo="percent+label",
            marker=dict(line=dict(color="#FFFDF9", width=2)),
        )
        sector_fig.update_layout(
            height=390,
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(sector_fig, width="stretch")

    top_product = _top_contribution_label(ecl_by_product, "product_type", "ecl")
    top_sector = _top_contribution_label(ecl_by_sector, "sector", "ecl")
    insight_cols = st.columns(2)
    with insight_cols[0]:
        st.info(f"Produit principal contributeur a l'ECL : {top_product}.")
    with insight_cols[1]:
        st.info(f"Secteur principal contributeur a l'ECL : {top_sector}.")

    st.markdown("#### Scenarios et overlays")
    scenario_left, scenario_right = st.columns(2)
    with scenario_left:
        scenario_fig = px.bar(
            scenario_summary,
            x="scenario",
            y="ecl",
            title="ECL par scenario macro",
            text_auto=".2s",
        )
        scenario_fig.update_layout(height=360, xaxis_title="", yaxis_title="ECL")
        st.plotly_chart(scenario_fig, width="stretch")
    with scenario_right:
        active_overlays = overlay_summary.loc[overlay_summary["overlay_amount"] > 0].copy() if not overlay_summary.empty else overlay_summary
        if active_overlays is not None and not active_overlays.empty:
            overlay_fig = px.bar(
                active_overlays.sort_values("overlay_amount", ascending=False),
                x="overlay_amount",
                y="overlay_name",
                orientation="h",
                title="Montant d'overlay par ajustement",
                text_auto=".2s",
            )
            overlay_fig.update_layout(height=360, xaxis_title="Montant overlay", yaxis_title="")
            st.plotly_chart(overlay_fig, width="stretch")
        else:
            st.info("Aucun overlay avec impact non nul.")

    st.markdown("#### Points de decision pour le comite")
    decision_left, decision_right = st.columns([1.1, 0.9])
    with decision_left:
        for point in client_discussion_points:
            st.info(point)
    with decision_right:
        display_top = top_contributors.head(5).copy()
        for column in ["ead", "ecl"]:
            if column in display_top:
                display_top[column] = display_top[column].map(format_currency)
        st.write("Top 5 expositions contributrices")
        st.dataframe(display_top, width="stretch", hide_index=True)

    with st.expander("Afficher la note de synthese complete", expanded=False):
        st.markdown(committee_summary)


def _build_top_share_frame(df: pd.DataFrame, label_col: str, value_col: str, top_n: int = 5) -> pd.DataFrame:
    """Build a compact top contributors frame with an Other bucket."""
    if df.empty:
        return pd.DataFrame({"label": ["Non disponible"], "amount": [1.0]})
    sorted_df = df.sort_values(value_col, ascending=False).copy()
    top = sorted_df.head(top_n)[[label_col, value_col]].rename(columns={label_col: "label", value_col: "amount"})
    other_amount = sorted_df.iloc[top_n:][value_col].sum()
    if other_amount > 0:
        top = pd.concat([top, pd.DataFrame([{"label": "Autres", "amount": other_amount}])], ignore_index=True)
    return top


def _top_contribution_label(df: pd.DataFrame, label_col: str, value_col: str) -> str:
    """Return the top contribution label with its share."""
    if df.empty or df[value_col].sum() == 0:
        return "non disponible"
    row = df.sort_values(value_col, ascending=False).iloc[0]
    share = safe_divide(row[value_col], df[value_col].sum())
    return f"{row[label_col]} ({share:.1%})"


def render_staging_decision_tree() -> None:
    """Render the simplified IFRS 9 staging rules as a decision tree."""
    st.markdown(
        dedent(
            """
            <section class="decision-tree">
                <div class="decision-root">Evaluation de l'exposition a la date d'arrete</div>
                <div class="decision-branches">
                    <article class="decision-node">
                        <div class="decision-stage">Stage 3</div>
                        <div class="decision-condition">Defaut ou credit-impaired ?</div>
                        <div class="decision-detail">
                            DPD >= 90 jours, default flag, UTP, faillite probable ou
                            restructuration distressed. Le Stage 3 est maintenu tant que
                            le defaut persiste ou que la cure minimale de 3 mois n'est pas respectee.
                        </div>
                    </article>
                    <article class="decision-node">
                        <div class="decision-stage">Stage 2</div>
                        <div class="decision-condition">Augmentation significative du risque de credit ?</div>
                        <div class="decision-detail">
                            DPD >= 30 jours, degradation de rating >= 2 crans, PD au moins
                            doublee, watchlist, forbearance ou signal macro-sectoriel.
                            Retour en Stage 1 apres disparition du SICR et probation minimale de 6 mois.
                        </div>
                    </article>
                    <article class="decision-node">
                        <div class="decision-stage">Stage 1</div>
                        <div class="decision-condition">Absence de defaut et de SICR</div>
                        <div class="decision-detail">
                            Exposition performante sans deterioration significative.
                            Le retour direct Stage 3 vers Stage 1 reste exceptionnel :
                            paiements normalises, cure de 12 mois et justification forte.
                        </div>
                    </article>
                </div>
            </section>
            """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_ecl_formula_view() -> None:
    """Render simplified ECL assumptions as mathematical formulas."""
    formula_columns = st.columns(3)
    formulas = [
        (
            "Stage 1",
            r"\mathrm{ECL}_{12m} = \mathrm{PD}_{12m} \times \mathrm{LGD} \times \mathrm{EAD}",
            "Pertes attendues a 12 mois pour les expositions performantes.",
        ),
        (
            "Stage 2",
            r"\mathrm{ECL}_{LT} = \mathrm{PD}_{lifetime} \times \mathrm{LGD} \times \mathrm{EAD}",
            "Pertes attendues sur la duree de vie apres augmentation significative du risque.",
        ),
        (
            "Stage 3",
            r"\mathrm{ECL}_{default} = 100\% \times \mathrm{LGD} \times \mathrm{EAD}",
            "Proxy pedagogique applique aux expositions en defaut ou credit-impaired.",
        ),
    ]
    for column, (stage, formula, description) in zip(formula_columns, formulas, strict=False):
        with column:
            with st.container(border=True):
                st.markdown(f"**{stage}**")
                st.latex(formula)
                st.caption(description)


def render_regulatory_audit_view(audit_view: dict[str, pd.DataFrame]) -> None:
    """Render regulatory assumptions and audit evidence without Excel-like tables."""
    st.subheader("Regulatory & Audit View")
    st.caption(
        "Vue pedagogique des regles, hypotheses et parametres appliques. "
        "Les donnees detaillees restent disponibles dans l'export Excel."
    )

    run_values = _audit_section_to_dict(audit_view.get("run_summary", pd.DataFrame()), "item", "value")
    render_light_kpi_panel(
        "Gouvernance du run",
        [
            ("Date du run", str(run_values.get("Run datetime", "N/A")), "Horodatage du calcul"),
            ("Expositions", str(run_values.get("Exposures processed", "N/A")), "Contrats traites"),
            (
                "Anomalies data quality",
                str(run_values.get("Data quality issues detected", "0")),
                "Exceptions identifiees",
            ),
            ("Source", "Donnees synthetiques", "Demonstrateur non destine a la production"),
        ],
    )

    st.markdown("#### Arbre de decision du staging")
    st.caption("Les declencheurs Stage 3 sont prioritaires sur les criteres SICR de Stage 2.")
    render_staging_decision_tree()

    st.markdown("#### Formules de calcul ECL")
    render_ecl_formula_view()

    scenario_parameters = audit_view.get("macro_scenarios", pd.DataFrame())
    scenario_results = audit_view.get("scenario_results", pd.DataFrame())
    if not scenario_parameters.empty:
        st.markdown("#### Parametres macroeconomiques")
        scenario_cols = st.columns(len(scenario_parameters))
        for column, (_, row) in zip(scenario_cols, scenario_parameters.iterrows(), strict=False):
            with column:
                render_governance_card(
                    str(row.get("scenario", "Scenario")),
                    f"Ponderation {float(row.get('weight', 0)):.0%}",
                    (
                        f"Multiplicateur PD x{float(row.get('pd_multiplier', 1)):.2f} | "
                        f"Multiplicateur LGD x{float(row.get('lgd_multiplier', 1)):.2f}"
                    ),
                )
    if not scenario_results.empty and {"scenario", "ecl"}.issubset(scenario_results.columns):
        scenario_figure = px.bar(
            scenario_results,
            x="scenario",
            y="ecl",
            color="scenario",
            text_auto=".3s",
            title="ECL obtenue par scenario",
            color_discrete_map={
                "Baseline": "#0B2B46",
                "Downside": "#F1A986",
                "Upside": "#14664A",
            },
        )
        scenario_figure.update_layout(
            height=340,
            showlegend=False,
            xaxis_title="",
            yaxis_title="ECL",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(scenario_figure, width="stretch")

    overlay_parameters = audit_view.get("management_overlays", pd.DataFrame())
    overlay_summary = audit_view.get("overlay_summary", pd.DataFrame())
    if not overlay_parameters.empty:
        st.markdown("#### Overlays manageriaux actifs")
        render_overlay_rule_cards(overlay_parameters)
    if not overlay_summary.empty and {"overlay_name", "overlay_amount"}.issubset(overlay_summary.columns):
        active_overlay_summary = overlay_summary.loc[overlay_summary["overlay_amount"] > 0].copy()
        if not active_overlay_summary.empty:
            overlay_figure = px.bar(
                active_overlay_summary.sort_values("overlay_amount"),
                x="overlay_amount",
                y="overlay_name",
                orientation="h",
                text_auto=".3s",
                title="Impact des overlays actifs",
                color_discrete_sequence=["#F1A986"],
            )
            overlay_figure.update_layout(
                height=max(300, 55 * len(active_overlay_summary)),
                xaxis_title="Montant d'overlay",
                yaxis_title="",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(overlay_figure, width="stretch")

    consistency_values = _audit_section_to_dict(
        audit_view.get("business_consistency", pd.DataFrame()),
        "metric",
        "value",
    )
    if consistency_values:
        st.markdown("#### Coherence metier")
        render_light_kpi_panel(
            "Resultats des controles de coherence",
            [
                (
                    "Score de coherence",
                    f"{float(consistency_values.get('business_consistency_score', 0)):.1%}",
                    "Part des controles sans alerte",
                ),
                (
                    "Controles passes",
                    f"{int(float(consistency_values.get('business_checks_passed', 0))):,}".replace(",", " "),
                    "Tests satisfaits",
                ),
                (
                    "Alertes",
                    str(int(float(consistency_values.get("business_alert_count", 0)))),
                    "Cas necessitant une revue",
                ),
                (
                    "Alertes critiques",
                    str(int(float(consistency_values.get("business_critical_alert_count", 0)))),
                    "Points a prioriser",
                ),
            ],
        )

    business_alerts = audit_view.get("business_alerts", pd.DataFrame())
    st.markdown("#### Alertes de coherence prioritaires")
    if business_alerts.empty:
        st.success("Aucune alerte de coherence metier detectee.")
    else:
        severity_order = {"Critical": 0, "Warning": 1, "Info": 2}
        alerts_to_show = (
            business_alerts.assign(
                _severity_order=business_alerts["severity"].map(severity_order).fillna(3)
            )
            .sort_values(["_severity_order", "loan_id"])
            .head(8)
        )
        alert_cols = st.columns(2)
        for index, (_, alert) in enumerate(alerts_to_show.iterrows()):
            with alert_cols[index % 2]:
                render_governance_card(
                    f"{alert.get('severity', 'Alerte')} | {alert.get('loan_id', '')}",
                    str(alert.get("rule", "Controle de coherence")),
                    (
                        f"Recommandation : {alert.get('recommendation', 'Revue requise.')} "
                        f"Impact potentiel : {alert.get('potential_impact', 'A evaluer.')}"
                    ),
                )
        if len(business_alerts) > len(alerts_to_show):
            st.caption(
                f"{len(business_alerts) - len(alerts_to_show)} alerte(s) supplementaire(s) "
                "sont disponibles dans l'export et l'Audit Trail."
            )


def render_dashboard(
    metrics: dict[str, float],
    ecl_by_stage: pd.DataFrame,
    ecl_by_product: pd.DataFrame,
    ecl_by_sector: pd.DataFrame,
    ecl_portfolio: pd.DataFrame,
    migration_matrix: pd.DataFrame,
    top_contributors: pd.DataFrame,
    overlay_metrics: dict[str, float | str],
    business_summary: dict[str, float],
    client_discussion_points: list[str],
    demo_profile: str,
) -> None:
    """Render the executive dashboard."""
    st.caption("EAD = Exposure at Default. ECL = Expected Credit Loss. Le taux de couverture correspond a ECL / EAD.")

    st.markdown("#### Vue executive")
    render_light_kpi_panel(
        "Synthese du portefeuille",
        [
            ("EAD totale", format_compact_currency(metrics["total_ead"]), "Portefeuille synthetique"),
            ("ECL modele", format_compact_currency(metrics["total_ecl"]), "Avant scenarios et overlays"),
            ("Taux de couverture", f"{metrics['coverage_ratio']:.2%}", "ECL modele / EAD"),
            ("Expositions", f"{metrics['exposure_count']:,}".replace(",", " "), demo_profile),
        ],
    )

    st.markdown("#### Risque et qualite")
    render_light_kpi_panel(
        "Indicateurs de risque et de controle",
        [
            ("Stage 2", f"{metrics['stage_2_share']:.1%}", "Expositions en deterioration"),
            ("Stage 3", f"{metrics['stage_3_share']:.1%}", "Expositions en defaut"),
            ("Data quality", str(metrics["data_quality_issue_count"]), "Anomalies detectees"),
            (
                "Coherence metier",
                f"{business_summary['business_consistency_score']:.1%}",
                f"{int(business_summary['business_alert_count'])} alerte(s)",
            ),
        ],
    )

    st.markdown("#### Impact des overlays")
    render_light_kpi_panel(
        "Effet des ajustements manageriaux",
        [
            (
                "ECL avant overlay",
                format_compact_currency(float(overlay_metrics["ecl_before_overlay"])),
                "Base d'ajustement",
            ),
            (
                "Overlays",
                format_compact_currency(float(overlay_metrics["total_overlay_amount"])),
                f"{float(overlay_metrics['overlay_variation_pct']):.2%} de l'ECL avant overlay",
            ),
            (
                "ECL apres overlay",
                format_compact_currency(float(overlay_metrics["ecl_after_overlay"])),
                "ECL finale demo",
            ),
            (
                "Top overlay",
                str(overlay_metrics["top_overlay_contributor"]),
                "Principal ajustement",
            ),
        ],
    )

    st.divider()
    st.markdown("#### Lecture du portefeuille")
    overview_left, overview_right = st.columns([1.05, 0.95])
    with overview_left:
        ead_fig = px.bar(ecl_by_stage, x="stage", y="ead", title="EAD par stage", text_auto=".2s")
        ead_fig.update_layout(height=360, yaxis_title="EAD", xaxis_title="")
        st.plotly_chart(ead_fig, width="stretch")
    with overview_right:
        ecl_fig = px.bar(ecl_by_stage, x="stage", y="ecl", title="ECL par stage", text_auto=".2s")
        ecl_fig.update_layout(height=360, yaxis_title="ECL", xaxis_title="")
        st.plotly_chart(ecl_fig, width="stretch")

    analysis_left, analysis_right = st.columns(2)
    with analysis_left:
        product_fig = px.bar(ecl_by_product.head(8), x="product_type", y="ecl", title="ECL par produit", text_auto=".2s")
        product_fig.update_layout(height=360, yaxis_title="ECL", xaxis_title="")
        st.plotly_chart(product_fig, width="stretch")
        migration_source_column = migration_matrix.columns[0]
        migration_columns = [col for col in migration_matrix.columns if col != migration_source_column]
        migration_fig = px.bar(
            migration_matrix,
            x=migration_source_column,
            y=migration_columns,
            title="Migration Stage precedent / Stage recalcule",
        )
        migration_fig.update_layout(height=360, yaxis_title="Nombre d'expositions", xaxis_title="")
        st.plotly_chart(migration_fig, width="stretch")
    with analysis_right:
        sector_fig = px.bar(ecl_by_sector.head(8), x="sector", y="ecl", title="ECL par secteur", text_auto=".2s")
        sector_fig.update_layout(height=360, yaxis_title="ECL", xaxis_title="")
        st.plotly_chart(sector_fig, width="stretch")
        rating_counts = ecl_portfolio.groupby("current_rating", as_index=False).size().rename(columns={"size": "count"})
        rating_fig = px.bar(rating_counts, x="current_rating", y="count", title="Distribution des ratings actuels")
        rating_fig.update_layout(height=360, yaxis_title="Nombre d'expositions", xaxis_title="Rating actuel")
        st.plotly_chart(rating_fig, width="stretch")

    st.markdown("#### Points de discussion client")
    for point in client_discussion_points:
        st.info(point)

    with st.expander("Top 10 des expositions contributrices a l'ECL", expanded=False):
        display_top = top_contributors.copy()
        for column in ["ead", "ecl"]:
            if column in display_top:
                display_top[column] = display_top[column].map(format_currency)
        st.dataframe(display_top, width="stretch", hide_index=True)


if __name__ == "__main__":
    main()
