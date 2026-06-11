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
from modules.demo_config import APP_NAME, DEMO_DISCLAIMER_FR, EXPORT_FILE_PREFIX
from modules.ecl_calculator import calculate_ecl
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


st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="expanded")


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

        [data-testid="stHeader"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"] {
            display: none;
        }

        [data-testid="stSidebar"] {
            display: block !important;
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            bottom: 0 !important;
            min-width: 300px !important;
            width: 300px !important;
            max-width: 300px !important;
            flex-basis: 300px !important;
            transform: none !important;
            visibility: visible !important;
            background: #fffaf5 !important;
            border-right: 1px solid var(--auria-line);
            overflow-y: auto !important;
            z-index: 999 !important;
        }

        [data-testid="stSidebar"] > div:first-child {
            min-width: 300px !important;
            width: 300px !important;
            max-width: 300px !important;
        }

        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapseButton"],
        button[data-testid="stSidebarCollapseButton"] {
            display: none !important;
        }

        [data-testid="stAppViewContainer"] {
            margin-left: 300px !important;
            width: calc(100vw - 300px) !important;
            max-width: calc(100vw - 300px) !important;
        }

        [data-testid="stAppViewContainer"] > .main,
        [data-testid="stAppViewContainer"] main {
            margin-left: 0 !important;
            width: 100% !important;
            max-width: 100% !important;
        }

        [data-testid="stAppViewBlockContainer"] {
            max-width: 1380px !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
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
            padding-top: 1rem;
            padding-bottom: 3rem;
            max-width: 1380px;
        }

        .sidebar-actions {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 6px;
            margin: 2px 0 18px;
        }

        .sidebar-actions a {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 36px;
            padding: 7px 5px;
            border: 1px solid rgba(11, 43, 70, 0.16);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.82);
            color: var(--auria-navy);
            font-size: 0.72rem;
            font-weight: 850;
            text-align: center;
            text-decoration: none;
        }

        .sidebar-actions a:hover {
            border-color: var(--auria-navy);
            background: var(--auria-navy);
            color: #ffffff;
        }

        .storyline-section {
            margin: 30px 0 10px;
            padding: 28px;
            border: 1px solid var(--auria-line);
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.70);
            box-shadow: var(--auria-shadow);
        }

        .storyline-kicker {
            color: var(--auria-peach);
            font-size: 0.76rem;
            font-weight: 950;
            letter-spacing: 0.10em;
            text-transform: uppercase;
        }

        .storyline-heading {
            margin: 7px 0 8px;
            color: var(--auria-navy);
            font-size: 1.65rem;
        }

        .storyline-intro {
            max-width: 760px;
            margin: 0 0 22px;
            color: var(--auria-grey);
            line-height: 1.55;
        }

        .storyline-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
        }

        .storyline-card {
            display: grid;
            grid-template-columns: 42px minmax(0, 1fr);
            gap: 12px;
            min-height: 118px;
            padding: 17px;
            border: 1px solid rgba(11, 43, 70, 0.12);
            border-radius: 12px;
            background: #ffffff;
        }

        .storyline-number {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background: var(--auria-navy);
            color: #ffffff;
            font-size: 0.76rem;
            font-weight: 900;
        }

        .storyline-title {
            margin: 2px 0 7px;
            color: var(--auria-navy);
            font-size: 0.96rem;
            font-weight: 900;
        }

        .storyline-description {
            color: var(--auria-grey);
            font-size: 0.84rem;
            line-height: 1.45;
        }

        .migration-kpi-panel {
            margin: 18px 0 26px;
            padding: 24px 26px;
            border: 1px solid rgba(11, 43, 70, 0.18);
            border-radius: 18px;
            color: #ffffff;
            background: linear-gradient(135deg, #0b2b46, #174866);
            box-shadow: 0 18px 44px rgba(11, 43, 70, 0.12);
        }

        .migration-kpi-kicker {
            margin-bottom: 17px;
            color: #f1a986;
            font-size: 0.72rem;
            font-weight: 900;
            letter-spacing: 0.09em;
            text-transform: uppercase;
        }

        .migration-kpi-grid {
            display: grid;
            gap: 0;
        }

        .migration-kpi-grid-primary {
            grid-template-columns: repeat(5, minmax(0, 1fr));
        }

        .migration-kpi-grid-secondary {
            grid-template-columns: repeat(4, minmax(0, 1fr));
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.16);
        }

        .ecl-kpi-grid {
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }

        .kpi-grid-four {
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }

        .kpi-grid-two {
            grid-template-columns: repeat(2, minmax(0, 1fr));
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.16);
        }

        .overlay-rule-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 16px;
            margin: 14px 0 26px;
        }

        .overlay-rule-card {
            min-width: 0;
            padding: 20px 22px;
            border: 1px solid rgba(11, 43, 70, 0.14);
            border-left: 5px solid var(--auria-peach);
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.88);
            box-shadow: 0 16px 38px rgba(11, 43, 70, 0.09);
        }

        .overlay-rule-heading {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 14px;
            margin-bottom: 15px;
        }

        .overlay-rule-name {
            color: var(--auria-navy);
            font-size: 1rem;
            font-weight: 900;
            line-height: 1.3;
        }

        .overlay-rule-rate {
            flex: 0 0 auto;
            padding: 5px 10px;
            border-radius: 999px;
            color: #ffffff;
            background: var(--auria-navy);
            font-size: 0.82rem;
            font-weight: 900;
        }

        .overlay-rule-label {
            margin-bottom: 4px;
            color: var(--auria-peach);
            font-size: 0.67rem;
            font-weight: 900;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .overlay-rule-scope {
            margin-bottom: 13px;
            color: var(--auria-navy);
            font-size: 0.88rem;
            font-weight: 800;
            line-height: 1.45;
        }

        .overlay-rule-comment {
            color: var(--auria-grey);
            font-size: 0.82rem;
            line-height: 1.55;
        }

        .migration-kpi-item {
            min-width: 0;
            min-height: 92px;
            padding: 2px 18px;
            border-right: 1px solid rgba(255, 255, 255, 0.14);
        }

        .migration-kpi-item:first-child {
            padding-left: 0;
        }

        .migration-kpi-item:last-child {
            padding-right: 0;
            border-right: 0;
        }

        .migration-kpi-label {
            min-height: 2.1em;
            color: rgba(255, 255, 255, 0.68);
            font-size: 0.68rem;
            font-weight: 850;
            line-height: 1.35;
            text-transform: uppercase;
        }

        .migration-kpi-value {
            margin: 7px 0 6px;
            color: #ffffff;
            font-size: clamp(1.55rem, 2.2vw, 2.15rem);
            font-weight: 850;
            line-height: 1;
            white-space: nowrap;
        }

        .migration-kpi-caption {
            color: rgba(255, 255, 255, 0.70);
            font-size: 0.75rem;
            line-height: 1.4;
        }

        @media (max-width: 1100px) {
            .auria-main-hero-grid {
                grid-template-columns: minmax(0, 1fr) !important;
            }

            .auria-main-hero h1 {
                font-size: clamp(2.6rem, 7vw, 4.4rem) !important;
            }

            .portfolio-summary-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
            }

            .storyline-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .migration-kpi-grid-primary {
                grid-template-columns: repeat(3, minmax(0, 1fr));
                row-gap: 20px;
            }

            .migration-kpi-grid-secondary {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                row-gap: 20px;
            }

            .ecl-kpi-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                row-gap: 20px;
            }

            .kpi-grid-four,
            .kpi-grid-two {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                row-gap: 20px;
            }

            .overlay-rule-grid {
                grid-template-columns: minmax(0, 1fr);
            }
        }

        @media (max-width: 720px) {
            .portfolio-summary-grid {
                grid-template-columns: minmax(0, 1fr) !important;
            }

            .storyline-grid {
                grid-template-columns: minmax(0, 1fr);
            }

            .migration-kpi-grid-primary,
            .migration-kpi-grid-secondary,
            .ecl-kpi-grid,
            .kpi-grid-four,
            .kpi-grid-two {
                grid-template-columns: minmax(0, 1fr);
            }

            .migration-kpi-item {
                min-height: auto;
                padding: 14px 0;
                border-right: 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.14);
            }

            .migration-kpi-item:last-child {
                border-bottom: 0;
            }
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
        <section class="auria-main-hero" style="
            position:relative;
            overflow:hidden;
            border-radius:26px;
            padding:24px;
            margin-bottom:22px;
            color:#ffffff;
            background:linear-gradient(135deg, #061d31, #0b2b46);
            box-shadow:0 24px 60px rgba(11, 43, 70, 0.16);
        ">
            <div class="auria-main-hero-grid" style="
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


def render_kpi_panel(
    kicker: str,
    primary_metrics: list[tuple[str, str, str]],
    secondary_metrics: list[tuple[str, str, str]] | None = None,
) -> None:
    """Render compact Auria KPI rows in the same style as the staging view."""

    def metric_markup(metric: tuple[str, str, str]) -> str:
        label, value, caption = metric
        return (
            '<div class="migration-kpi-item">'
            f'<div class="migration-kpi-label">{label}</div>'
            f'<div class="migration-kpi-value">{value}</div>'
            f'<div class="migration-kpi-caption">{caption}</div>'
            "</div>"
        )

    primary_class = "kpi-grid-four" if len(primary_metrics) == 4 else "migration-kpi-grid-primary"
    secondary_markup = ""
    if secondary_metrics:
        secondary_class = "kpi-grid-two" if len(secondary_metrics) == 2 else "migration-kpi-grid-secondary"
        secondary_markup = (
            f'<div class="migration-kpi-grid {secondary_class}">'
            f"{''.join(metric_markup(metric) for metric in secondary_metrics)}"
            "</div>"
        )

    st.markdown(
        dedent(
            f"""
            <section class="migration-kpi-panel">
                <div class="migration-kpi-kicker">{kicker}</div>
                <div class="migration-kpi-grid {primary_class}">
                    {''.join(metric_markup(metric) for metric in primary_metrics)}
                </div>
                {secondary_markup}
            </section>
            """
        ).strip(),
        unsafe_allow_html=True,
    )


def default_demo_parameters() -> dict:
    """Return a fresh copy of the default demonstration settings."""
    return {
        "source": "Generer un portefeuille synthetique",
        "demo_profile": "Balanced Portfolio",
        "data_quality_level": DATA_QUALITY_LEVELS[0],
        "n_exposures": 1_000,
        "seed": 42,
        "uploaded_file": None,
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
        "demo_source": parameters["source"],
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
        "demo_source",
        "demo_profile_control",
        "demo_data_quality_level",
        "demo_exposure_count",
        "demo_seed",
        "demo_uploaded_file",
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

        data_quality_level = st.select_slider(
            "Niveau de qualite des donnees",
            options=DATA_QUALITY_LEVELS,
            value=DATA_QUALITY_LEVELS[0],
            key="demo_data_quality_level",
        )
        st.caption(DATA_QUALITY_LEVEL_DESCRIPTIONS[data_quality_level])

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
        generated_summary = st.session_state.get("portfolio_generation_summary", {})
        if source == "Generer un portefeuille synthetique" and generated_summary:
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
            default=[overlay["name"] for overlay in PREDEFINED_OVERLAYS],
            key="demo_enabled_overlays",
        )

    st.session_state["persisted_demo_parameters"] = {
        "source": source,
        "demo_profile": demo_profile,
        "data_quality_level": data_quality_level,
        "n_exposures": int(n_exposures),
        "seed": int(seed),
        "uploaded_file": uploaded_file,
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
        uploaded_file,
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
    uploaded_file = parameters.get("uploaded_file")
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
        uploaded_file,
        scenario_config,
        enabled_overlays,
    )


def render_active_demo_context(
    source: str,
    demo_profile: str,
    data_quality_level: str,
    portfolio: pd.DataFrame,
    uploaded_file=None,
) -> None:
    """Render the active demonstration context on every application page."""
    generation = st.session_state.get("portfolio_generation_summary", {})
    if source == "Charger un fichier":
        file_name = getattr(uploaded_file, "name", "Fichier charge")
        source_label = "Fichier utilisateur"
        source_detail = file_name
    else:
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
        source, demo_profile, data_quality_level, n_exposures, seed, generate_clicked, uploaded_file, scenario_config, enabled_overlays = (
            render_demo_parameters()
        )
    else:
        source, demo_profile, data_quality_level, n_exposures, seed, uploaded_file, scenario_config, enabled_overlays = (
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
        portfolio_requires_transition_upgrade = (
            "portfolio" in st.session_state
            and "previous_stage" not in st.session_state["portfolio"].columns
        )
        if generate_clicked or "portfolio" not in st.session_state or portfolio_requires_transition_upgrade:
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
        st.info("Chargez un fichier CSV ou Excel, ou repassez en generation synthetique.")
        st.stop()

    missing_columns = missing_required_columns(portfolio)
    if missing_columns:
        st.error("Calcul impossible : colonnes obligatoires absentes.")
        st.write(", ".join(missing_columns))
        st.stop()

    portfolio = ensure_staging_transition_context(portfolio, seed=seed)
    if source == "Generer un portefeuille synthetique":
        st.session_state["portfolio"] = portfolio

    render_active_demo_context(
        source,
        active_demo_profile,
        st.session_state.get("data_quality_level", data_quality_level),
        portfolio,
        uploaded_file,
    )

    try:
        findings = run_data_quality_checks(portfolio)
        dq_summary = summarize_quality_findings(findings)
        raw_quality_tests = run_raw_data_quality_tests(portfolio)
        raw_quality_metrics = build_raw_quality_metrics(portfolio, raw_quality_tests)
        raw_quality_dimensions = build_raw_quality_dimension_summary(raw_quality_tests)
        raw_column_profile = build_raw_column_profile(portfolio)
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

    elif selected_page == "Business Consistency":
        render_business_consistency(business_summary, business_alerts)

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
                "sicr_flag",
                "credit_impaired_flag",
                "unlikely_to_pay_flag",
                "bankruptcy_flag",
                "distressed_restructuring_flag",
                "payment_normalized_flag",
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
    default_rate = float(portfolio.get("default_flag", pd.Series(False, index=portfolio.index)).fillna(False).mean())
    forbearance_rate = float(
        portfolio.get("forbearance_flag", pd.Series(False, index=portfolio.index)).fillna(False).mean()
    )
    watchlist_rate = float(
        portfolio.get("watchlist_flag", pd.Series(False, index=portfolio.index)).fillna(False).mean()
    )
    collateral_rate = float(
        portfolio.get("collateral_flag", pd.Series(False, index=portfolio.index)).fillna(False).mean()
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
    coverage_ratio = total_ecl / total_ead if total_ead else 0.0

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
    stage_summary["coverage_ratio"] = np.where(
        stage_summary["ead"].ne(0),
        stage_summary["ecl"] / stage_summary["ead"],
        0,
    )
    stage_summary["ecl_share"] = (
        stage_summary["ecl"] / total_ecl if total_ecl else 0
    )

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
                probation_mask = stage_1[probation_column].fillna(False).astype(bool)
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
        cards.append(
            f"""
            <article class="overlay-rule-card">
                <div class="overlay-rule-heading">
                    <div class="overlay-rule-name">{overlay_name}</div>
                    <div class="overlay-rule-rate">{float(overlay.get("rate", 0)):.0%}</div>
                </div>
                <div class="overlay-rule-label">Périmètre concerné</div>
                <div class="overlay-rule-scope">{scope}</div>
                <div class="overlay-rule-label">Commentaire métier</div>
                <div class="overlay-rule-comment">{comment}</div>
            </article>
            """
        )

    if not cards:
        st.info("Aucun overlay n'est activé pour ce run.")
        return
    st.markdown(
        f'<section class="overlay-rule-grid">{"".join(cards)}</section>',
        unsafe_allow_html=True,
    )


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

    st.markdown("#### Transitions de stage et periodes de cure")
    transition_summary = audit_trail.get("staging_transition_summary", pd.DataFrame())
    if transition_summary is not None and not transition_summary.empty:
        transition_chart = px.bar(
            transition_summary,
            x="transition_rule",
            y="exposure_count",
            color="stage",
            text="exposure_count",
            title="Transitions observees dans le run",
            color_discrete_map={
                "Stage 1": "#8298AA",
                "Stage 2": "#F1A986",
                "Stage 3": "#0B2B46",
            },
        )
        transition_chart.update_layout(
            height=410,
            xaxis_title="",
            yaxis_title="Nombre d'expositions",
            legend_title_text="Stage final",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(transition_chart, width="stretch")
        with st.expander("Consulter la synthese detaillee des transitions", expanded=False):
            st.dataframe(transition_summary, width="stretch", hide_index=True)
    else:
        st.caption("Synthese des transitions non disponible.")

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
        "staging_transition_summary",
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
    render_kpi_panel(
        "Lecture synthetique de la coherence metier",
        [
            (
                "Score de coherence",
                f"{business_summary['business_consistency_score']:.1%}",
                "Part des controles sans alerte",
            ),
            (
                "Controles passes",
                f"{int(business_summary['business_checks_passed']):,}".replace(",", " "),
                "Tests de coherence satisfaits",
            ),
            (
                "Alertes",
                str(int(business_summary["business_alert_count"])),
                "Cas necessitant une analyse",
            ),
            (
                "Alertes critiques",
                str(int(business_summary["business_critical_alert_count"])),
                "Points a prioriser",
            ),
        ],
    )
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
