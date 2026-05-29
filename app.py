"""Streamlit interface for the ECL Staging Explorer MVP."""

from __future__ import annotations

from datetime import datetime

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
from modules.committee_summary import build_docx_bytes, generate_committee_summary
from modules.data_quality import missing_required_columns
from modules.data_quality import run_data_quality_checks, summarize_quality_findings
from modules.data_quality import calculate_quality_score
from modules.demo_config import APP_NAME, DEMO_DISCLAIMER_FR, EXPORT_FILE_PREFIX
from modules.ecl_calculator import calculate_ecl
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
from modules.sample_data import DEMO_PORTFOLIO_PROFILES, generate_demo_portfolio
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


st.set_page_config(page_title=APP_NAME, layout="wide")


def apply_auria_theme() -> None:
    """Apply Auria-inspired visual styling to the Streamlit shell."""
    px.defaults.template = "plotly_white"
    px.defaults.color_discrete_sequence = ["#0b2b46", "#f1a986", "#6d7885", "#102f4a", "#f7c6ae", "#14664a"]
    st.markdown(
        """
        <style>
        :root {
            --auria-navy: #0b2b46;
            --auria-navy-2: #102f4a;
            --auria-ink: #061a2d;
            --auria-peach: #f1a986;
            --auria-peach-2: #f7c6ae;
            --auria-cream: #f8f4ef;
            --auria-cream-2: #fffaf5;
            --auria-grey: #6d7885;
            --auria-line: rgba(11, 43, 70, 0.14);
            --auria-card: rgba(255, 255, 255, 0.86);
            --auria-shadow: 0 18px 44px rgba(11, 43, 70, 0.10);
        }

        html, body, [data-testid="stAppViewContainer"] {
            color: var(--auria-ink);
            font-family: "Inter", "Aptos", "Segoe UI", Arial, sans-serif;
            background:
                radial-gradient(circle at 8% 2%, rgba(241, 169, 134, 0.23), transparent 26rem),
                radial-gradient(circle at 96% 10%, rgba(11, 43, 70, 0.12), transparent 24rem),
                linear-gradient(180deg, var(--auria-cream-2), var(--auria-cream));
        }

        [data-testid="stAppViewContainer"]::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background-image:
                linear-gradient(rgba(11, 43, 70, 0.045) 1px, transparent 1px),
                linear-gradient(90deg, rgba(11, 43, 70, 0.035) 1px, transparent 1px);
            background-size: 44px 44px;
            mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.62), transparent 72%);
            z-index: 0;
        }

        [data-testid="stHeader"] {
            background: rgba(255, 250, 245, 0.86);
            border-bottom: 1px solid rgba(11, 43, 70, 0.10);
            backdrop-filter: blur(14px);
        }

        [data-testid="stSidebar"] {
            background: rgba(255, 250, 245, 0.94);
            border-right: 1px solid var(--auria-line);
        }

        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] label {
            color: var(--auria-navy);
            font-weight: 800;
        }

        .block-container {
            padding-top: 2.25rem;
            padding-bottom: 3rem;
            max-width: 1380px;
        }

        .auria-hero {
            position: relative;
            overflow: hidden;
            border-radius: 28px;
            padding: 30px 34px;
            margin-bottom: 22px;
            color: #ffffff;
            background:
                radial-gradient(circle at 88% 22%, rgba(241, 169, 134, 0.42), transparent 15rem),
                linear-gradient(135deg, #071d31, var(--auria-navy));
            box-shadow: 0 24px 60px rgba(11, 43, 70, 0.16);
        }

        .auria-hero::after {
            content: "";
            position: absolute;
            inset: auto -50px -90px auto;
            width: 260px;
            height: 260px;
            border-radius: 50%;
            background: rgba(241, 169, 134, 0.18);
        }

        .auria-kicker {
            color: var(--auria-peach-2);
            font-size: 0.78rem;
            font-weight: 900;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .auria-hero h1 {
            margin: 0;
            color: #ffffff;
            font-size: clamp(2.1rem, 4vw, 4.2rem);
            font-weight: 850;
            letter-spacing: 0;
            line-height: 1.02;
        }

        .auria-hero p {
            max-width: 780px;
            margin: 14px 0 0;
            color: rgba(255, 255, 255, 0.82);
            font-size: 1.02rem;
        }

        .auria-run {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-top: 18px;
            padding: 9px 13px;
            border: 1px solid rgba(255, 255, 255, 0.22);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
            color: rgba(255, 255, 255, 0.92);
            font-size: 0.82rem;
            font-weight: 800;
        }

        h1, h2, h3 {
            color: var(--auria-navy);
            letter-spacing: 0;
        }

        div[data-testid="stMetric"],
        [data-testid="stDataFrame"],
        div[data-testid="stPlotlyChart"] {
            border: 1px solid var(--auria-line);
            border-radius: 18px;
            background: var(--auria-card);
            box-shadow: var(--auria-shadow);
            padding: 12px;
        }

        div[data-testid="stMetric"] {
            min-height: 112px;
            padding: 18px 18px 14px;
        }

        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
            color: var(--auria-grey);
            font-size: 0.78rem;
            font-weight: 850;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        div[data-testid="stMetricValue"] {
            color: var(--auria-navy);
            font-weight: 850;
        }

        button[kind="primary"],
        div[data-testid="stDownloadButton"] button {
            border: 1px solid var(--auria-navy) !important;
            border-radius: 999px !important;
            background: var(--auria-navy) !important;
            color: #ffffff !important;
            font-weight: 850 !important;
            box-shadow: 0 12px 28px rgba(11, 43, 70, 0.16);
        }

        div[data-testid="stButton"] button {
            border-radius: 999px;
            border-color: rgba(11, 43, 70, 0.18);
            color: var(--auria-navy);
            font-weight: 800;
        }

        div[data-testid="stTabs"] button[role="tab"] {
            border-radius: 999px;
            color: var(--auria-navy);
            font-weight: 850;
            padding: 8px 16px;
        }

        div[data-testid="stTabs"] button[aria-selected="true"] {
            background: var(--auria-navy);
            color: #ffffff;
        }

        [data-testid="stAlert"] {
            border-radius: 18px;
            border: 1px solid rgba(241, 169, 134, 0.35);
            box-shadow: 0 12px 28px rgba(11, 43, 70, 0.08);
        }

        .stMultiSelect [data-baseweb="tag"],
        [data-baseweb="tag"] {
            background: rgba(241, 169, 134, 0.18) !important;
            color: var(--auria-navy) !important;
            border-radius: 999px !important;
        }

        input, textarea, [data-baseweb="select"] > div {
            border-radius: 14px !important;
        }

        hr {
            border-color: var(--auria-line);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_brand_header(run_id: str | None = None) -> None:
    """Render a compact Auria-style brand header."""
    run_line = f'<div class="auria-run">Run ID: {run_id} | Version: {APP_VERSION}</div>' if run_id else ""
    st.markdown(
        f"""
        <section class="auria-hero">
            <div class="auria-kicker">Auria Advisory</div>
            <h1>{APP_NAME}</h1>
            <p>IFRS 9 ECL & Staging Demonstrator pour transformer le provisionnement IFRS 9 en un outil de pilotage transparent, explicable et auditable.</p>
            <p><strong>{DEMO_DISCLAIMER_FR}</strong></p>
            {run_line}
        </section>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def load_synthetic_portfolio(n_exposures: int, seed: int, demo_profile: str) -> pd.DataFrame:
    """Cache synthetic generation for a smoother demo experience."""
    return generate_demo_portfolio(profile=demo_profile, n_exposures=n_exposures, seed=seed)


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    """Read a user-provided CSV or Excel file for demo purposes."""
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    return pd.read_excel(uploaded_file)


def format_currency(value: float) -> str:
    """Format monetary values for dashboard metrics."""
    return f"{value:,.0f} EUR".replace(",", " ")


def format_compact_currency(value: float) -> str:
    """Format dashboard amounts in a compact, non-truncated way."""
    abs_value = abs(float(value))
    if abs_value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f} Md EUR"
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f} M EUR"
    if abs_value >= 1_000:
        return f"{value / 1_000:.1f} k EUR"
    return format_currency(value)


def render_kpi_card(label: str, value: str, caption: str = "") -> None:
    """Render a stable dashboard KPI card without Streamlit metric truncation."""
    st.markdown(
        f"""
        <div style="
            min-height: 124px;
            border: 1px solid rgba(11, 43, 70, 0.14);
            border-radius: 18px;
            background: rgba(255,255,255,0.88);
            box-shadow: 0 18px 44px rgba(11, 43, 70, 0.10);
            padding: 18px 18px 14px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        ">
            <div style="
                color: #6d7885;
                font-size: 0.78rem;
                font-weight: 850;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            ">{label}</div>
            <div style="
                color: #0b2b46;
                font-size: clamp(1.55rem, 2.3vw, 2.25rem);
                line-height: 1.05;
                font-weight: 850;
                overflow-wrap: anywhere;
            ">{value}</div>
            <div style="color:#6d7885; font-size:0.78rem; min-height: 1rem;">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    apply_auria_theme()

    with st.sidebar:
        st.header("Parametres")
        source = st.radio("Source du portefeuille", ["Generer un portefeuille synthetique", "Charger un fichier"], index=0)
        demo_profile = st.selectbox("Demo Portfolio Profile", DEMO_PORTFOLIO_PROFILES, index=0)
        st.caption(PROFILE_CONTEXT.get(demo_profile, "Profil de demonstration synthetique."))
        n_exposures = st.slider("Nombre d'expositions", min_value=100, max_value=5_000, value=1_000, step=100)
        seed = st.number_input("Seed aleatoire", min_value=1, value=42, step=1)
        generate_clicked = st.button("Generer le portefeuille synthetique", type="primary")
        uploaded_file = None
        if source == "Charger un fichier":
            uploaded_file = st.file_uploader("Fichier CSV ou Excel", type=["csv", "xlsx"])
        st.header("Scenarios macro")
        scenario_config = build_scenario_controls()
        st.header("Overlays")
        enabled_overlays = st.multiselect(
            "Overlays actifs",
            options=[overlay["name"] for overlay in PREDEFINED_OVERLAYS],
            default=[overlay["name"] for overlay in PREDEFINED_OVERLAYS],
        )

    if source == "Charger un fichier":
        if uploaded_file is None:
            portfolio = None
        try:
            if uploaded_file is not None:
                portfolio = read_uploaded_file(uploaded_file)
        except Exception as exc:
            st.error(f"Chargement impossible : {exc}")
            st.stop()
    else:
        if generate_clicked or "portfolio" not in st.session_state or st.session_state.get("demo_profile") != demo_profile:
            st.session_state["portfolio"] = load_synthetic_portfolio(n_exposures=n_exposures, seed=seed, demo_profile=demo_profile)
            st.session_state["demo_profile"] = demo_profile
            st.session_state["run_datetime"] = datetime.now()
            st.session_state["run_id"] = generate_run_id(st.session_state["run_datetime"])
        portfolio = st.session_state["portfolio"]
    active_demo_profile = st.session_state.get("demo_profile", demo_profile)

    if portfolio is None:
        render_home(None)
        st.info("Chargez un fichier CSV ou Excel, ou repassez en generation synthetique.")
        st.stop()

    missing_columns = missing_required_columns(portfolio)
    if missing_columns:
        st.error("Calcul impossible : colonnes obligatoires absentes.")
        st.write(", ".join(missing_columns))
        st.stop()

    try:
        findings = run_data_quality_checks(portfolio)
        dq_summary = summarize_quality_findings(findings)
        quality_score = calculate_quality_score(portfolio, findings)
        staged = assign_stage(portfolio)
        ecl_portfolio = calculate_ecl(staged)
        ecl_portfolio = build_review_flags(ecl_portfolio, findings)
        ecl_by_stage = aggregate_ecl_by_stage(ecl_portfolio)
        ecl_by_product = aggregate_ecl_by_dimension(ecl_portfolio, "product_type")
        ecl_by_sector = aggregate_ecl_by_dimension(ecl_portfolio, "sector")
        metrics = build_dashboard_metrics(ecl_portfolio, findings)
        scenario_parameters = scenario_config_to_frame(scenario_config)
        scenario_weights_valid = validate_scenario_weights(scenario_config)
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
    render_brand_header(run_id)

    tab_home, tab_portfolio, tab_dq, tab_business, tab_staging, tab_ecl, tab_macro, tab_overlays, tab_dashboard, tab_audit, tab_summary, tab_export = st.tabs(
        [
            "Accueil",
            "Portefeuille",
            "Data Quality",
            "Business Consistency",
            "Staging",
            "ECL Calculation",
            "Macro Scenarios",
            "Management Overlays",
            "Dashboard",
            "Audit Trail",
            "Committee Summary",
            "Export",
        ]
    )

    with tab_home:
        render_home(metrics, active_demo_profile)

    with tab_portfolio:
        st.subheader("Portefeuille synthetique")
        st.write("Vue ligne a ligne des expositions utilisees pour la demonstration.")
        st.dataframe(portfolio, width="stretch")

    with tab_dq:
        st.subheader("Controles de qualite des donnees")
        col1, col2, col3 = st.columns(3)
        col1.metric("Nombre d'anomalies", len(findings))
        col2.metric("Expositions concernees", findings["loan_id"].nunique() if not findings.empty else 0)
        col3.metric("Score qualite", f"{quality_score:.2f}/100")
        st.dataframe(dq_summary, width="stretch")
        st.dataframe(findings, width="stretch")

    with tab_business:
        render_business_consistency(business_summary, business_alerts)

    with tab_staging:
        st.subheader("Affectation des stages")
        stage_counts = staged.groupby(["stage", "stage_reason"], as_index=False).size().rename(columns={"size": "count"})
        fig_stage = px.bar(stage_counts, x="stage", y="count", color="stage_reason", title="Expositions par stage et raison")
        st.plotly_chart(fig_stage, width="stretch")
        st.dataframe(staged[["loan_id", "client_id", "initial_stage", "stage", "stage_reason", "stage_comment", "days_past_due", "origination_rating", "current_rating"]], width="stretch")

    with tab_ecl:
        st.subheader("Calcul ECL")
        st.dataframe(
            ecl_portfolio[
                [
                    "loan_id",
                    "client_id",
                    "product_type",
                    "sector",
                    "stage",
                    "stage_reason",
                    "stage_comment",
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
        )

    with tab_macro:
        render_macro_scenarios(
            scenario_parameters,
            scenario_weights_valid,
            scenario_summary,
            scenario_metrics,
            downside_by_stage,
        )

    with tab_overlays:
        render_management_overlays(overlay_parameters, overlay_summary, overlay_results, overlay_metrics, overlay_waterfall)

    with tab_dashboard:
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

        st.subheader("Regulatory & Audit View")
        audit_col1, audit_col2 = st.columns(2)
        with audit_col1:
            st.write("Regles de staging appliquees")
            st.dataframe(audit_view["staging_rules"], width="stretch")
        with audit_col2:
            st.write("Hypotheses de calcul ECL")
            st.dataframe(audit_view["ecl_assumptions"], width="stretch")
        st.write("Run summary")
        st.dataframe(audit_view["run_summary"], width="stretch")
        st.write("Scenarios macroeconomiques")
        st.dataframe(audit_view["macro_scenarios"], width="stretch")
        st.write("Resultats par scenario")
        st.dataframe(audit_view["scenario_results"], width="stretch")
        st.write("Overlays actifs")
        st.dataframe(audit_view["management_overlays"], width="stretch")
        st.write("Synthese overlays")
        st.dataframe(audit_view["overlay_summary"], width="stretch")
        st.write("Coherence metier")
        st.dataframe(audit_view["business_consistency"], width="stretch")
        st.write("Alertes de coherence metier")
        st.dataframe(audit_view["business_alerts"], width="stretch")

    with tab_audit:
        render_audit_trail(detailed_audit_trail)

    with tab_summary:
        st.subheader("Committee Summary")
        st.markdown(committee_summary)
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

    with tab_export:
        st.subheader("Export Excel")
        staging_results = staged[
            ["loan_id", "client_id", "initial_stage", "stage", "stage_reason", "stage_comment", "days_past_due", "origination_rating", "current_rating"]
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
    for scenario, defaults in DEFAULT_SCENARIOS.items():
        with st.expander(scenario, expanded=scenario == "Baseline"):
            weight = st.number_input(
                f"{scenario} weight",
                min_value=0.0,
                max_value=100.0,
                value=float(defaults["weight"] * 100),
                step=5.0,
                key=f"{scenario.lower()}_weight",
            )
            pd_multiplier = st.number_input(
                f"{scenario} PD multiplier",
                min_value=0.0,
                max_value=5.0,
                value=float(defaults["pd_multiplier"]),
                step=0.05,
                key=f"{scenario.lower()}_pd_multiplier",
            )
            lgd_multiplier = st.number_input(
                f"{scenario} LGD multiplier",
                min_value=0.0,
                max_value=5.0,
                value=float(defaults["lgd_multiplier"]),
                step=0.05,
                key=f"{scenario.lower()}_lgd_multiplier",
            )
        scenario_config[scenario] = {
            "weight": weight / 100,
            "pd_multiplier": pd_multiplier,
            "lgd_multiplier": lgd_multiplier,
        }
    return scenario_config


def render_home(metrics: dict[str, float] | None, demo_profile: str | None = None) -> None:
    """Render the client-demo landing section."""
    st.subheader("IFRS 9 ECL & Staging Demonstrator")
    st.markdown("**Transformer le provisionnement IFRS 9 en un outil de pilotage transparent, explicable et auditable.**")
    st.write(
        "Ce demonstrateur illustre de maniere simple et pedagogique la chaine IFRS 9 : qualite des donnees, "
        "staging, calcul des pertes attendues et restitution executive pour discussion client."
    )
    st.warning(DEMO_DISCLAIMER_FR)

    if demo_profile:
        st.info(f"Profil de demo selectionne : {demo_profile}. {PROFILE_CONTEXT.get(demo_profile, '')}")

    st.write("Demo Storyline")
    st.dataframe(pd.DataFrame(DEMO_STORYLINE), width="stretch", hide_index=True)

    if metrics:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("EAD totale", format_currency(metrics["total_ead"]), help="Exposure at Default : exposition utilisee dans le calcul ECL.")
        col2.metric("ECL totale", format_currency(metrics["total_ecl"]), help="Expected Credit Loss : perte de credit attendue selon les hypotheses du MVP.")
        col3.metric("Taux de couverture", f"{metrics['coverage_ratio']:.2%}", help="ECL totale divisee par l'EAD totale.")
        col4.metric("Expositions", f"{metrics['exposure_count']:,}".replace(",", " "))


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

    st.write("Parametres appliques")
    display_params = scenario_parameters.copy()
    display_params["weight"] = display_params["weight"].map(lambda value: f"{value:.0%}")
    st.dataframe(display_params, width="stretch")

    kpi_row = st.columns(4)
    kpi_row[0].metric("ECL baseline", format_currency(scenario_metrics["ecl_baseline"]))
    kpi_row[1].metric("ECL downside", format_currency(scenario_metrics["ecl_downside"]))
    kpi_row[2].metric("ECL upside", format_currency(scenario_metrics["ecl_upside"]))
    kpi_row[3].metric("ECL ponderee", format_currency(scenario_metrics["ecl_weighted"]))

    impact_row = st.columns(2)
    impact_row[0].metric(
        "Impact downside vs baseline",
        format_currency(scenario_metrics["downside_impact_amount"]),
        f"{scenario_metrics['downside_impact_pct']:.2%}",
    )
    impact_row[1].metric(
        "Impact ECL ponderee vs baseline",
        format_currency(scenario_metrics["weighted_impact_amount"]),
        f"{scenario_metrics['weighted_impact_pct']:.2%}",
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
    st.write("Regles des overlays")
    st.dataframe(overlay_parameters, width="stretch")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("ECL avant overlay", format_currency(float(overlay_metrics["ecl_before_overlay"])))
    col2.metric("Montant overlays", format_currency(float(overlay_metrics["total_overlay_amount"])))
    col3.metric("ECL apres overlay", format_currency(float(overlay_metrics["ecl_after_overlay"])))
    col4.metric("Variation", f"{overlay_metrics['overlay_variation_pct']:.2%}")
    st.metric("Top overlay contributeur", overlay_metrics["top_overlay_contributor"])

    st.write("Synthese des overlays")
    st.dataframe(overlay_summary, width="stretch")

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
        by_stage = overlay_results.groupby("stage", as_index=False)["overlay_amount"].sum()
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
        top_impacted = overlay_results.sort_values("overlay_amount", ascending=False).head(10)
        st.write("Top 10 expositions les plus impactees")
        st.dataframe(top_impacted[["loan_id", "client_id", "stage", "product_type", "sector", "ecl_before_overlay", "overlay_amount", "ecl_after_overlay", "overlay_names"]], width="stretch")

    st.write("Resultats ligne a ligne")
    st.dataframe(
        filtered[
            [
                "loan_id",
                "client_id",
                "stage",
                "product_type",
                "sector",
                "country",
                "ecl_before_overlay",
                "overlay_amount",
                "ecl_after_overlay",
                "overlay_applied",
                "overlay_names",
                "overlay_types",
                "overlay_justifications",
            ]
        ],
        width="stretch",
    )


def render_audit_trail(audit_trail: dict[str, pd.DataFrame]) -> None:
    """Render detailed audit trail sections."""
    st.subheader("Audit Trail")
    for title, table in audit_trail.items():
        st.write(title.replace("_", " ").title())
        st.dataframe(table, width="stretch")


def render_business_consistency(business_summary: dict[str, float], business_alerts: pd.DataFrame) -> None:
    """Render business consistency score and alerts."""
    st.subheader("Business Consistency")
    st.write(
        "Ces controles recherchent des incoherences metier simples entre stage, defaut, DPD, PD, LGD et ECL. "
        "Ils servent a orienter la revue, sans remplacer une validation de modele."
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Score de coherence", f"{business_summary['business_consistency_score']:.1%}")
    col2.metric("Controles passes", f"{int(business_summary['business_checks_passed']):,}".replace(",", " "))
    col3.metric("Alertes", int(business_summary["business_alert_count"]))
    col4.metric("Alertes critiques", int(business_summary["business_critical_alert_count"]))
    if business_alerts.empty:
        st.success("Aucune alerte de coherence metier detectee.")
    else:
        severity_filter = st.multiselect("Filtrer par criticite", sorted(business_alerts["severity"].unique()))
        filtered = business_alerts.copy()
        if severity_filter:
            filtered = filtered[filtered["severity"].isin(severity_filter)]
        st.dataframe(filtered, width="stretch")


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
    executive_cols = st.columns(4)
    with executive_cols[0]:
        render_kpi_card("EAD totale", format_compact_currency(metrics["total_ead"]), "Portefeuille synthetique")
    with executive_cols[1]:
        render_kpi_card("ECL modele", format_compact_currency(metrics["total_ecl"]), "Avant scenarios et overlays")
    with executive_cols[2]:
        render_kpi_card("Taux de couverture", f"{metrics['coverage_ratio']:.2%}", "ECL modele / EAD")
    with executive_cols[3]:
        render_kpi_card("Expositions", f"{metrics['exposure_count']:,}".replace(",", " "), demo_profile)

    st.markdown("#### Risque et qualite")
    risk_cols = st.columns(4)
    with risk_cols[0]:
        render_kpi_card("Stage 2", f"{metrics['stage_2_share']:.1%}", "Expositions en deterioration")
    with risk_cols[1]:
        render_kpi_card("Stage 3", f"{metrics['stage_3_share']:.1%}", "Expositions en defaut")
    with risk_cols[2]:
        render_kpi_card("Data quality", str(metrics["data_quality_issue_count"]), "Anomalies detectees")
    with risk_cols[3]:
        render_kpi_card("Coherence metier", f"{business_summary['business_consistency_score']:.1%}", f"{int(business_summary['business_alert_count'])} alerte(s)")

    st.markdown("#### Impact des overlays")
    overlay_cols = st.columns([1.2, 1.0, 1.2, 0.9])
    with overlay_cols[0]:
        render_kpi_card("ECL avant overlay", format_compact_currency(float(overlay_metrics["ecl_before_overlay"])), "Base d'ajustement")
    with overlay_cols[1]:
        render_kpi_card("Overlays", format_compact_currency(float(overlay_metrics["total_overlay_amount"])), f"{overlay_metrics['overlay_variation_pct']:.2%}")
    with overlay_cols[2]:
        render_kpi_card("ECL apres overlay", format_compact_currency(float(overlay_metrics["ecl_after_overlay"])), "ECL finale demo")
    with overlay_cols[3]:
        render_kpi_card("Top overlay", str(overlay_metrics["top_overlay_contributor"]), "Principal ajustement")

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
        migration_columns = [col for col in migration_matrix.columns if col != "Initial stage"]
        migration_fig = px.bar(
            migration_matrix,
            x="Initial stage",
            y=migration_columns,
            title="Migration Stage initial / Stage recalcule",
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
