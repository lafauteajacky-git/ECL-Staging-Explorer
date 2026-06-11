"""Auria visual theme for the Streamlit interface."""

import plotly.express as px
import streamlit as st

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

        .kpi-grid-one {
            grid-template-columns: minmax(0, 1fr);
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.16);
        }

        .kpi-grid-one .migration-kpi-item {
            min-height: auto;
            padding-left: 0;
            border-right: 0;
        }

        .kpi-grid-one .migration-kpi-value {
            font-size: clamp(1.35rem, 2vw, 1.9rem);
            line-height: 1.15;
            white-space: normal;
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

        .overlay-rate-info {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 15px;
            height: 15px;
            margin-left: 5px;
            border: 1px solid rgba(255, 255, 255, 0.72);
            border-radius: 50%;
            color: #ffffff;
            font-size: 0.62rem;
            line-height: 1;
            cursor: help;
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

        .light-kpi-panel {
            margin: 16px 0 24px;
            padding: 22px 24px;
            border: 1px solid rgba(11, 43, 70, 0.15);
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.82);
            box-shadow: 0 16px 38px rgba(11, 43, 70, 0.08);
        }

        .light-kpi-kicker {
            margin-bottom: 17px;
            color: var(--auria-peach);
            font-size: 0.72rem;
            font-weight: 900;
            letter-spacing: 0.09em;
            text-transform: uppercase;
        }

        .light-kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }

        .light-kpi-item {
            min-width: 0;
            min-height: 88px;
            padding: 2px 18px;
            border-right: 1px solid rgba(11, 43, 70, 0.13);
        }

        .light-kpi-item:first-child {
            padding-left: 0;
        }

        .light-kpi-item:last-child {
            padding-right: 0;
            border-right: 0;
        }

        .light-kpi-label {
            min-height: 2.1em;
            color: var(--auria-grey);
            font-size: 0.68rem;
            font-weight: 850;
            line-height: 1.35;
            text-transform: uppercase;
        }

        .light-kpi-value {
            margin: 7px 0 6px;
            color: var(--auria-navy);
            font-size: clamp(1.45rem, 2vw, 2.05rem);
            font-weight: 900;
            line-height: 1.05;
            overflow-wrap: anywhere;
        }

        .light-kpi-caption {
            color: var(--auria-grey);
            font-size: 0.75rem;
            line-height: 1.4;
        }

        .decision-tree {
            margin: 14px 0 26px;
            padding: 22px;
            border: 1px solid rgba(11, 43, 70, 0.15);
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.82);
            box-shadow: 0 16px 38px rgba(11, 43, 70, 0.08);
        }

        .decision-root {
            max-width: 560px;
            margin: 0 auto 18px;
            padding: 14px 18px;
            border-radius: 12px;
            color: #ffffff;
            background: var(--auria-navy);
            text-align: center;
            font-weight: 900;
        }

        .decision-branches {
            position: relative;
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 16px;
            padding-top: 22px;
        }

        .decision-branches::before {
            content: "";
            position: absolute;
            top: 0;
            left: 16.7%;
            right: 16.7%;
            border-top: 2px solid rgba(11, 43, 70, 0.20);
        }

        .decision-branches::after {
            content: "";
            position: absolute;
            top: -22px;
            left: 50%;
            height: 22px;
            border-left: 2px solid rgba(11, 43, 70, 0.20);
        }

        .decision-node {
            position: relative;
            min-height: 205px;
            padding: 18px;
            border: 1px solid rgba(11, 43, 70, 0.13);
            border-top: 4px solid var(--auria-peach);
            border-radius: 14px;
            background: rgba(248, 244, 239, 0.64);
        }

        .decision-node::before {
            content: "";
            position: absolute;
            top: -24px;
            left: 50%;
            height: 22px;
            border-left: 2px solid rgba(11, 43, 70, 0.20);
        }

        .decision-stage {
            margin-bottom: 8px;
            color: var(--auria-navy);
            font-size: 1.05rem;
            font-weight: 900;
        }

        .decision-condition {
            margin-bottom: 10px;
            color: var(--auria-ink);
            font-size: 0.82rem;
            font-weight: 800;
            line-height: 1.45;
        }

        .decision-detail {
            color: var(--auria-grey);
            font-size: 0.78rem;
            line-height: 1.5;
        }

        .governance-card {
            min-height: 145px;
            padding: 19px 20px;
            border: 1px solid rgba(11, 43, 70, 0.14);
            border-radius: 15px;
            background: rgba(255, 255, 255, 0.82);
            box-shadow: 0 14px 32px rgba(11, 43, 70, 0.07);
        }

        .governance-label {
            color: var(--auria-peach);
            font-size: 0.68rem;
            font-weight: 900;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .governance-value {
            margin: 7px 0;
            color: var(--auria-navy);
            font-size: 1.02rem;
            font-weight: 900;
            line-height: 1.35;
        }

        .governance-detail {
            color: var(--auria-grey);
            font-size: 0.78rem;
            line-height: 1.5;
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

            .light-kpi-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                row-gap: 20px;
            }

            .decision-branches {
                grid-template-columns: minmax(0, 1fr);
            }

            .decision-branches::before {
                display: none;
            }

            .decision-branches::after {
                display: none;
            }

            .decision-node::before {
                display: none;
            }

            .kpi-grid-four,
            .kpi-grid-two,
            .kpi-grid-one {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                row-gap: 20px;
            }

            .kpi-grid-one {
                grid-template-columns: minmax(0, 1fr);
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
            .kpi-grid-two,
            .kpi-grid-one {
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

            .light-kpi-grid {
                grid-template-columns: minmax(0, 1fr);
            }

            .light-kpi-item {
                min-height: auto;
                padding: 14px 0;
                border-right: 0;
                border-bottom: 1px solid rgba(11, 43, 70, 0.13);
            }

            .light-kpi-item:last-child {
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
