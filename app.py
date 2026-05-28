"""Streamlit interface for the ECL Staging Explorer MVP."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.data_quality import missing_required_columns
from modules.data_quality import run_data_quality_checks, summarize_quality_findings
from modules.data_quality import calculate_quality_score
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
from modules.sample_data import generate_portfolio
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


st.set_page_config(page_title="ECL Staging Explorer", layout="wide")


@st.cache_data
def load_synthetic_portfolio(n_exposures: int, seed: int) -> pd.DataFrame:
    """Cache synthetic generation for a smoother demo experience."""
    return generate_portfolio(n_exposures=n_exposures, seed=seed)


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    """Read a user-provided CSV or Excel file for demo purposes."""
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    return pd.read_excel(uploaded_file)


def format_currency(value: float) -> str:
    """Format monetary values for dashboard metrics."""
    return f"{value:,.0f} EUR".replace(",", " ")


def main() -> None:
    st.title("ECL Staging Explorer")
    st.caption("IFRS 9 ECL & Staging Demonstrator")

    with st.sidebar:
        st.header("Parametres")
        source = st.radio("Source du portefeuille", ["Generer un portefeuille synthetique", "Charger un fichier"], index=0)
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
        if generate_clicked or "portfolio" not in st.session_state:
            st.session_state["portfolio"] = load_synthetic_portfolio(n_exposures=n_exposures, seed=seed)
            st.session_state["run_datetime"] = datetime.now()
        portfolio = st.session_state["portfolio"]

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
        migration_matrix = build_migration_matrix(ecl_portfolio)
        top_contributors = build_top_ecl_contributors(ecl_portfolio)
        insights = build_management_insights(ecl_portfolio, ecl_by_stage, ecl_by_product, findings, scenario_insights + overlay_insights)
        run_datetime = st.session_state.get("run_datetime", datetime.now())
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
        dashboard_summary = build_dashboard_summary_table(metrics, scenario_metrics | overlay_metrics)
    except Exception as exc:
        st.error(f"Calcul impossible : {exc}")
        st.stop()

    tab_home, tab_portfolio, tab_dq, tab_staging, tab_ecl, tab_macro, tab_overlays, tab_dashboard, tab_export = st.tabs(
        [
            "Accueil",
            "Portefeuille",
            "Data Quality",
            "Staging",
            "ECL Calculation",
            "Macro Scenarios",
            "Management Overlays",
            "Dashboard",
            "Export",
        ]
    )

    with tab_home:
        render_home(metrics)

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
        render_dashboard(metrics, ecl_by_stage, ecl_by_product, ecl_by_sector, ecl_portfolio, migration_matrix, top_contributors, overlay_metrics)

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
        )
        if st.button("Exporter dans le dossier outputs"):
            try:
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
                )
                st.success(f"Export cree : {output_path}")
            except Exception as exc:
                st.error(f"Export impossible : {exc}")
        st.download_button(
            "Telecharger les resultats Excel",
            data=export_bytes,
            file_name="ecl_staging_explorer_results.xlsx",
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


def render_home(metrics: dict[str, float] | None) -> None:
    """Render the client-demo landing section."""
    st.subheader("IFRS 9 ECL & Staging Demonstrator")
    st.write(
        "Ce demonstrateur illustre de maniere simple et pedagogique la chaine IFRS 9 : qualite des donnees, "
        "staging, calcul des pertes attendues et restitution executive pour discussion client."
    )
    st.warning("Toutes les donnees affichees sont synthetiques. Aucune donnee bancaire reelle n'est integree.")

    st.write("Parcours de demonstration")
    steps = [
        "1. Generer ou charger un portefeuille",
        "2. Controler la qualite des donnees",
        "3. Determiner le staging IFRS 9",
        "4. Calculer les ECL",
        "5. Simuler les scenarios macro et exporter",
    ]
    for step in steps:
        st.write(step)

    if metrics:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("EAD totale", format_currency(metrics["total_ead"]))
        col2.metric("ECL totale", format_currency(metrics["total_ecl"]))
        col3.metric("Taux de couverture", f"{metrics['coverage_ratio']:.2%}")
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


def render_dashboard(
    metrics: dict[str, float],
    ecl_by_stage: pd.DataFrame,
    ecl_by_product: pd.DataFrame,
    ecl_by_sector: pd.DataFrame,
    ecl_portfolio: pd.DataFrame,
    migration_matrix: pd.DataFrame,
    top_contributors: pd.DataFrame,
    overlay_metrics: dict[str, float | str],
) -> None:
    """Render the V0.2 executive dashboard."""
    kpi_row_1 = st.columns(4)
    kpi_row_1[0].metric("EAD totale", format_currency(metrics["total_ead"]))
    kpi_row_1[1].metric("ECL totale", format_currency(metrics["total_ecl"]))
    kpi_row_1[2].metric("Taux de couverture", f"{metrics['coverage_ratio']:.2%}")
    kpi_row_1[3].metric("Expositions", f"{metrics['exposure_count']:,}".replace(",", " "))

    kpi_row_2 = st.columns(4)
    kpi_row_2[0].metric("Part Stage 2", f"{metrics['stage_2_share']:.2%}")
    kpi_row_2[1].metric("Part Stage 3", f"{metrics['stage_3_share']:.2%}")
    kpi_row_2[2].metric("Anomalies DQ", metrics["data_quality_issue_count"])
    kpi_row_2[3].metric("Cas a revoir", metrics["review_required_count"])

    kpi_row_3 = st.columns(5)
    kpi_row_3[0].metric("ECL avant overlay", format_currency(float(overlay_metrics["ecl_before_overlay"])))
    kpi_row_3[1].metric("Montant overlays", format_currency(float(overlay_metrics["total_overlay_amount"])))
    kpi_row_3[2].metric("ECL apres overlay", format_currency(float(overlay_metrics["ecl_after_overlay"])))
    kpi_row_3[3].metric("Variation overlays", f"{overlay_metrics['overlay_variation_pct']:.2%}")
    kpi_row_3[4].metric("Top overlay", overlay_metrics["top_overlay_contributor"])

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(px.bar(ecl_by_stage, x="stage", y="ead", title="EAD par stage", text_auto=".2s"), width="stretch")
        st.plotly_chart(
            px.bar(ecl_by_stage, x="stage", y="coverage_ratio", title="Taux de couverture par stage", text_auto=".2%"),
            width="stretch",
        )
        st.plotly_chart(px.bar(ecl_by_product, x="product_type", y="ecl", title="ECL par produit", text_auto=".2s"), width="stretch")
        st.plotly_chart(
            px.bar(migration_matrix, x="Initial stage", y=[col for col in migration_matrix.columns if col != "Initial stage"], title="Migration Stage initial / Stage recalcule"),
            width="stretch",
        )
    with col2:
        st.plotly_chart(px.bar(ecl_by_stage, x="stage", y="ecl", title="ECL par stage", text_auto=".2s"), width="stretch")
        st.plotly_chart(px.bar(ecl_by_sector, x="sector", y="ecl", title="ECL par secteur", text_auto=".2s"), width="stretch")
        rating_counts = ecl_portfolio.groupby("current_rating", as_index=False).size().rename(columns={"size": "count"})
        st.plotly_chart(px.bar(rating_counts, x="current_rating", y="count", title="Distribution des ratings actuels"), width="stretch")
        st.write("Top 10 des expositions contributrices a l'ECL")
        st.dataframe(top_contributors, width="stretch")


if __name__ == "__main__":
    main()
