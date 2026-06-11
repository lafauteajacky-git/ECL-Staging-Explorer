"""Reusable Streamlit presentation components."""

from html import escape
from textwrap import dedent

import streamlit as st

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
        if len(secondary_metrics) == 1:
            secondary_class = "kpi-grid-one"
        elif len(secondary_metrics) == 2:
            secondary_class = "kpi-grid-two"
        else:
            secondary_class = "migration-kpi-grid-secondary"
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


def render_light_kpi_panel(
    kicker: str,
    metrics: list[tuple[str, str, str]],
) -> None:
    """Render a grouped KPI panel on a light background."""
    items = []
    for label, value, caption in metrics:
        items.append(
            '<div class="light-kpi-item">'
            f'<div class="light-kpi-label">{escape(str(label))}</div>'
            f'<div class="light-kpi-value">{escape(str(value))}</div>'
            f'<div class="light-kpi-caption">{escape(str(caption))}</div>'
            "</div>"
        )
    st.markdown(
        (
            '<section class="light-kpi-panel">'
            f'<div class="light-kpi-kicker">{escape(kicker)}</div>'
            f'<div class="light-kpi-grid">{"".join(items)}</div>'
            "</section>"
        ),
        unsafe_allow_html=True,
    )


def render_governance_card(label: str, value: str, detail: str = "") -> None:
    """Render a compact light governance card."""
    st.markdown(
        (
            '<div class="governance-card">'
            f'<div class="governance-label">{escape(label)}</div>'
            f'<div class="governance-value">{escape(value)}</div>'
            f'<div class="governance-detail">{escape(detail)}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
