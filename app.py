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

        [data-testid="stSidebar"] [data-testid="stRadio"] > div {
            gap: 5px;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            min-height: 38px;
            padding: 8px 10px;
            border: 1px solid transparent;
            border-radius: 8px;
            transition: background 120ms ease, border-color 120ms ease;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
            border-color: rgba(11, 43, 70, 0.14);
            background: rgba(11, 43, 70, 0.05);
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
            border-color: var(--auria-navy);
            background: var(--auria-navy);
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
            color: #ffffff;
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
    st.markdown(
        f"""
        <div style="
            display:flex;
            align-items:center;
            gap:10px;
            margin: 0 0 18px;
            color:#0b2b46;
        ">
            <div
                aria-label="Auria Advisory logo mark"
                style="
                    width:46px;
                    height:46px;
                    flex:0 0 46px;
                    background-image:url('https://auria-advisory.fr/wp-content/uploads/2025/10/Logo-final-vertical-or-blanc-h.png');
                    background-repeat:no-repeat;
                    background-position:left center;
                    background-size:150px auto;
                ">
            </div>
            <div style="line-height:0.95;">
                <div style="
                    font-family:Georgia, 'Times New Roman', serif;
                    font-size:1.88rem;
                    line-height:0.95;
                    font-weight:900;
                    letter-spacing:0.055em;
                    color:#0b2b46;
                ">AURIA</div>
                <div style="
                    margin-top:4px;
                    font-size:0.78rem;
                    line-height:1;
                    font-weight:900;
                    letter-spacing:0.22em;
                    color:#0b2b46;
                ">ADVISORY</div>
            </div>
        </div>
        <section style="
            position:relative;
            overflow:hidden;
            border-radius:26px;
            padding:24px;
            margin-bottom:22px;
            color:#ffffff;
            background:linear-gradient(135deg, #061d31, #0b2b46);
            box-shadow:0 24px 60px rgba(11, 43, 70, 0.16);
        ">
            <div style="
                display:grid;
                grid-template-columns:minmax(0, 1.55fr) minmax(310px, 0.75fr);
                gap:28px;
                align-items:stretch;
            ">
                <div style="padding:2px 0 0;">
                    <div style="
                        color:#f1a986;
                        font-size:0.72rem;
                        font-weight:950;
                        letter-spacing:0.08em;
                        text-transform:uppercase;
                        margin-bottom:24px;
                    ">Auria Advisory | IFRS 9 ECL & Staging Systems</div>
                    <h1 style="
                        margin:0;
                        max-width:760px;
                        color:#ffffff;
                        font-size:clamp(2.8rem, 6vw, 5.2rem);
                        line-height:0.98;
                        font-weight:900;
                        letter-spacing:0;
                    ">{APP_NAME}</h1>
                    <p style="
                        max-width:820px;
                        margin:26px 0 18px;
                        color:rgba(255,255,255,0.88);
                        font-size:1rem;
                        line-height:1.65;
                    ">
                        Demonstrateur IFRS 9 pour explorer le staging, les ECL, la qualite des donnees,
                        les scenarios macro, les overlays manageriaux, l'audit trail et la note comite.
                    </p>
                    <p style="margin:10px 0 0; color:rgba(255,255,255,0.90); font-size:0.92rem;">
                        <strong>Contexte :</strong> portefeuille synthetique multi-profils avec controles de coherence et restitution executive.
                    </p>
                    <p style="margin:8px 0 0; color:rgba(255,255,255,0.90); font-size:0.92rem;">
                        <strong>A observer :</strong> migrations Stage 2/3, sensibilite macro, overlays et cas necessitant revue.
                    </p>
                    <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:18px;">
                        <span class="auria-pill">Donnees synthetiques</span>
                        <span class="auria-pill">Dashboard executif</span>
                        <span class="auria-pill">Audit trail</span>
                        <span class="auria-pill">Note comite</span>
                    </div>
                </div>
                <aside style="
                    border:1px solid rgba(255,255,255,0.18);
                    border-radius:20px;
                    background:rgba(255,255,255,0.12);
                    padding:22px 18px;
                    backdrop-filter:blur(12px);
                ">
                    <div style="
                        color:#f1a986;
                        font-size:0.75rem;
                        font-weight:950;
                        letter-spacing:0.12em;
                        text-transform:uppercase;
                        margin-bottom:22px;
                    ">Perimetre de demonstration</div>
                    <div class="auria-scope-row"><span>Portefeuilles</span><strong>5 profils synthetiques</strong></div>
                    <div class="auria-scope-row"><span>Modeles</span><strong>Staging, ECL, scenarios</strong></div>
                    <div class="auria-scope-row"><span>Gouvernance</span><strong>Overlays, audit trail</strong></div>
                    <div class="auria-scope-row"><span>Usage</span><strong>RDV client / comite</strong></div>
                    <div style="
                        margin-top:26px;
                        padding-top:16px;
                        border-top:1px solid rgba(255,255,255,0.16);
                        color:rgba(255,255,255,0.84);
                        font-size:0.84rem;
                        line-height:1.55;
                    ">{DEMO_DISCLAIMER_FR}</div>
                </aside>
            </div>
        </section>
        <style>
            .auria-pill {{
                display:inline-flex;
                align-items:center;
                min-height:30px;
                padding:0 13px;
                border:1px solid rgba(255,255,255,0.20);
                border-radius:999px;
                background:rgba(255,255,255,0.10);
                color:#ffffff;
                font-size:0.78rem;
                font-weight:850;
                white-space:nowrap;
            }}
            .auria-scope-row {{
                display:flex;
                justify-content:space-between;
                gap:16px;
                padding:13px 0;
                border-bottom:1px solid rgba(255,255,255,0.14);
                color:#ffffff;
                font-size:0.88rem;
            }}
            .auria-scope-row span {{
                color:rgba(255,255,255,0.70);
                font-size:0.74rem;
                font-weight:900;
                letter-spacing:0.08em;
                text-transform:uppercase;
            }}
            .auria-scope-row strong {{
                text-align:right;
                font-weight:900;
            }}
        </style>
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


def render_demo_parameters():
    """Render all demo controls in the main home page."""
    st.markdown("### Parametres de la demonstration")
    st.caption("Configurez le portefeuille, les hypotheses macroeconomiques et les overlays avant d'explorer les resultats.")

    with st.expander("1. Portefeuille de demonstration", expanded=True):
        source = st.radio(
            "Source du portefeuille",
            ["Generer un portefeuille synthetique", "Charger un fichier"],
            index=0,
            horizontal=True,
            key="demo_source",
        )
        portfolio_col1, portfolio_col2 = st.columns(2)
        with portfolio_col1:
            demo_profile = st.selectbox(
                "Demo Portfolio Profile",
                DEMO_PORTFOLIO_PROFILES,
                index=0,
                key="demo_profile_control",
            )
            st.caption(PROFILE_CONTEXT.get(demo_profile, "Profil de demonstration synthetique."))
        with portfolio_col2:
            n_exposures = st.slider(
                "Nombre d'expositions",
                min_value=100,
                max_value=5_000,
                value=1_000,
                step=100,
                key="demo_exposure_count",
            )
            seed = st.number_input("Seed aleatoire", min_value=1, value=42, step=1, key="demo_seed")

        uploaded_file = None
        if source == "Charger un fichier":
            uploaded_file = st.file_uploader(
                "Fichier CSV ou Excel",
                type=["csv", "xlsx"],
                key="demo_uploaded_file",
            )
        generate_clicked = st.button(
            "Generer le portefeuille synthetique",
            type="primary",
            disabled=source != "Generer un portefeuille synthetique",
        )

    with st.expander("2. Scenarios macroeconomiques", expanded=False):
        scenario_config = build_scenario_controls()

    with st.expander("3. Overlays manageriaux", expanded=False):
        enabled_overlays = st.multiselect(
            "Overlays actifs",
            options=[overlay["name"] for overlay in PREDEFINED_OVERLAYS],
            default=[overlay["name"] for overlay in PREDEFINED_OVERLAYS],
            key="demo_enabled_overlays",
        )

    return source, demo_profile, n_exposures, seed, generate_clicked, uploaded_file, scenario_config, enabled_overlays


def load_demo_parameters_from_state():
    """Load persisted demo settings when controls are not rendered."""
    source = st.session_state.get("demo_source", "Generer un portefeuille synthetique")
    demo_profile = st.session_state.get("demo_profile_control", "Balanced Portfolio")
    n_exposures = int(st.session_state.get("demo_exposure_count", 1_000))
    seed = int(st.session_state.get("demo_seed", 42))
    uploaded_file = st.session_state.get("demo_uploaded_file")
    scenario_config = {}
    for scenario, defaults in DEFAULT_SCENARIOS.items():
        scenario_config[scenario] = {
            "weight": float(st.session_state.get(f"{scenario.lower()}_weight", defaults["weight"] * 100)) / 100,
            "pd_multiplier": float(
                st.session_state.get(f"{scenario.lower()}_pd_multiplier", defaults["pd_multiplier"])
            ),
            "lgd_multiplier": float(
                st.session_state.get(f"{scenario.lower()}_lgd_multiplier", defaults["lgd_multiplier"])
            ),
        }
    enabled_overlays = st.session_state.get(
        "demo_enabled_overlays",
        [overlay["name"] for overlay in PREDEFINED_OVERLAYS],
    )
    return source, demo_profile, n_exposures, seed, uploaded_file, scenario_config, enabled_overlays


def main() -> None:
    apply_auria_theme()

    with st.sidebar:
        st.header("Navigation")
        selected_page = st.radio(
            "Navigation principale",
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
            ],
            label_visibility="collapsed",
            key="main_navigation",
        )
        st.caption("Selectionnez une rubrique pour afficher son contenu.")

    render_brand_header(st.session_state.get("run_id"))

    if selected_page == "Accueil":
        render_home_introduction()
        source, demo_profile, n_exposures, seed, generate_clicked, uploaded_file, scenario_config, enabled_overlays = (
            render_demo_parameters()
        )
    else:
        source, demo_profile, n_exposures, seed, uploaded_file, scenario_config, enabled_overlays = (
            load_demo_parameters_from_state()
        )
        generate_clicked = False

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
        if selected_page == "Accueil":
            render_home(None, demo_profile, show_introduction=False)
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
    if selected_page == "Accueil":
        render_home(metrics, active_demo_profile, show_introduction=False)

    elif selected_page == "Portefeuille":
        st.subheader("Portefeuille synthetique")
        st.write("Vue ligne a ligne des expositions utilisees pour la demonstration.")
        st.dataframe(portfolio, width="stretch")

    elif selected_page == "Data Quality":
        st.subheader("Controles de qualite des donnees")
        col1, col2, col3 = st.columns(3)
        col1.metric("Nombre d'anomalies", len(findings))
        col2.metric("Expositions concernees", findings["loan_id"].nunique() if not findings.empty else 0)
        col3.metric("Score qualite", f"{quality_score:.2f}/100")
        st.dataframe(dq_summary, width="stretch")
        st.dataframe(findings, width="stretch")

    elif selected_page == "Business Consistency":
        render_business_consistency(business_summary, business_alerts)

    elif selected_page == "Staging":
        st.subheader("Affectation des stages")
        stage_counts = staged.groupby(["stage", "stage_reason"], as_index=False).size().rename(columns={"size": "count"})
        fig_stage = px.bar(stage_counts, x="stage", y="count", color="stage_reason", title="Expositions par stage et raison")
        st.plotly_chart(fig_stage, width="stretch")
        st.dataframe(staged[["loan_id", "client_id", "initial_stage", "stage", "stage_reason", "stage_comment", "days_past_due", "origination_rating", "current_rating"]], width="stretch")

    elif selected_page == "ECL Calculation":
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
    show_introduction: bool = True,
) -> None:
    """Render the client-demo landing section."""
    if show_introduction:
        render_home_introduction()

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

    render_contact_block()


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
    """Render detailed audit trail sections in a more user-friendly audit view."""
    st.subheader("Audit Trail")
    st.write(
        "Vue de tracabilite du run : hypotheses appliquees, parametres, alertes et principaux resultats. "
        "Les tableaux detailles restent disponibles pour audit ou export."
    )

    run_summary = audit_trail.get("run_summary", pd.DataFrame())
    run_values = _audit_section_to_dict(run_summary, "field", "value")
    summary_cols = st.columns(4)
    with summary_cols[0]:
        render_kpi_card("Run ID", str(run_values.get("run_id", "N/A")), str(run_values.get("app_version", "")))
    with summary_cols[1]:
        render_kpi_card("Expositions", str(run_values.get("exposure_count", "N/A")), "Traitees dans le run")
    with summary_cols[2]:
        render_kpi_card("EAD totale", format_compact_currency(float(run_values.get("total_ead", 0) or 0)), "Portefeuille")
    with summary_cols[3]:
        render_kpi_card("ECL finale", format_compact_currency(float(run_values.get("final_ecl_after_overlay", 0) or 0)), "Apres overlays")

    st.info(str(run_values.get("demo_disclaimer", DEMO_DISCLAIMER_FR)))

    st.markdown("#### Points de controle prioritaires")
    control_cols = st.columns(4)
    with control_cols[0]:
        render_kpi_card("Anomalies DQ", str(run_values.get("data_quality_issue_count", 0)), "Data quality")
    with control_cols[1]:
        render_kpi_card("Cas a revoir", str(run_values.get("review_required_count", 0)), "Review required")
    with control_cols[2]:
        render_kpi_card("Alertes metier", str(run_values.get("business_alert_count", 0)), "Coherence")
    with control_cols[3]:
        render_kpi_card("Alertes critiques", str(run_values.get("business_critical_alert_count", 0)), "A prioriser")

    st.markdown("#### Synthese des hypotheses")
    hyp_left, hyp_right = st.columns(2)
    with hyp_left:
        _render_audit_bullets("Regles de staging appliquees", audit_trail.get("staging_rules"), ["rule", "threshold", "description"])
        _render_audit_bullets("Hypotheses ECL", audit_trail.get("ecl_assumptions"), ["stage", "pd_used", "formula"])
    with hyp_right:
        _render_audit_bullets("Scenarios macro", audit_trail.get("scenario_parameters"), ["scenario", "weight", "pd_multiplier", "lgd_multiplier"])
        _render_audit_bullets("Overlays actifs", audit_trail.get("overlay_parameters"), ["name", "overlay_type", "rate", "justification"])

    st.markdown("#### Alertes et contributeurs")
    alert_left, alert_right = st.columns([1.1, 0.9])
    with alert_left:
        critical_alerts = audit_trail.get("critical_business_alerts", pd.DataFrame())
        if critical_alerts is not None and not critical_alerts.empty:
            st.warning("Alertes critiques de coherence metier")
            st.dataframe(critical_alerts, width="stretch", hide_index=True)
        else:
            st.success("Aucune alerte critique de coherence metier dans ce run.")
    with alert_right:
        top_contributors = audit_trail.get("top_contributors", pd.DataFrame())
        if top_contributors is not None and not top_contributors.empty:
            display_top = top_contributors.head(5).copy()
            for column in ["ead", "ecl"]:
                if column in display_top:
                    display_top[column] = display_top[column].map(format_currency)
            st.write("Top contributeurs ECL")
            st.dataframe(display_top, width="stretch", hide_index=True)

    st.markdown("#### Details auditables")
    priority_sections = {
        "run_summary",
        "staging_rules",
        "ecl_assumptions",
        "scenario_parameters",
        "overlay_parameters",
        "critical_business_alerts",
        "top_contributors",
    }
    for title, table in audit_trail.items():
        if title in priority_sections:
            continue
        with st.expander(title.replace("_", " ").title(), expanded=False):
            st.dataframe(table, width="stretch", hide_index=True)


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

    headline_cols = st.columns(4)
    with headline_cols[0]:
        render_kpi_card("Run ID", run_id, demo_profile)
    with headline_cols[1]:
        render_kpi_card("EAD totale", format_compact_currency(metrics["total_ead"]), "Portefeuille")
    with headline_cols[2]:
        render_kpi_card("ECL finale", format_compact_currency(float(overlay_metrics["ecl_after_overlay"])), "Apres scenarios et overlays")
    with headline_cols[3]:
        render_kpi_card("Taux de couverture", f"{metrics['coverage_ratio']:.2%}", "Modele avant overlay")

    movement_cols = st.columns(4)
    with movement_cols[0]:
        render_kpi_card("Impact scenarios", format_compact_currency(scenario_metrics["weighted_impact_amount"]), f"{scenario_metrics['weighted_impact_pct']:.2%}")
    with movement_cols[1]:
        render_kpi_card("Impact overlays", format_compact_currency(float(overlay_metrics["total_overlay_amount"])), f"{overlay_metrics['overlay_variation_pct']:.2%}")
    with movement_cols[2]:
        render_kpi_card("Score coherence", f"{business_summary['business_consistency_score']:.1%}", f"{int(business_summary['business_alert_count'])} alerte(s)")
    with movement_cols[3]:
        render_kpi_card("Cas a revoir", str(metrics["review_required_count"]), "Priorisation metier")

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
        )
        stage_bar.update_layout(height=380, xaxis_title="", yaxis_title="Montant")
        st.plotly_chart(stage_bar, width="stretch")
    with stage_right:
        coverage_fig = px.bar(
            ecl_by_stage,
            x="stage",
            y="coverage_ratio",
            title="Taux de couverture par stage",
            text_auto=".2%",
        )
        coverage_fig.update_layout(height=380, xaxis_title="", yaxis_title="ECL / EAD")
        st.plotly_chart(coverage_fig, width="stretch")

    st.markdown("#### Contributions principales")
    contribution_left, contribution_right = st.columns(2)
    with contribution_left:
        product_share = _build_top_share_frame(ecl_by_product, "product_type", "ecl", top_n=5)
        product_fig = px.pie(product_share, names="label", values="amount", title="Part ECL par produit")
        product_fig.update_traces(textposition="inside", textinfo="percent+label")
        product_fig.update_layout(height=390, showlegend=False)
        st.plotly_chart(product_fig, width="stretch")
    with contribution_right:
        sector_share = _build_top_share_frame(ecl_by_sector, "sector", "ecl", top_n=5)
        sector_fig = px.pie(sector_share, names="label", values="amount", title="Part ECL par secteur")
        sector_fig.update_traces(textposition="inside", textinfo="percent+label")
        sector_fig.update_layout(height=390, showlegend=False)
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
    share = row[value_col] / df[value_col].sum()
    return f"{row[label_col]} ({share:.1%})"


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
