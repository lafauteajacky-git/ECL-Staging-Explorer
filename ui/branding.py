"""Auria branding components for the Streamlit interface."""

import streamlit as st

from modules.demo_config import APP_NAME

def render_brand_header(run_id: str | None = None, compact: bool = False) -> None:
    """Render the Auria brand header, compact on internal application pages."""
    if compact:
        st.markdown(
            f"""
            <div style="
                display:flex;
                align-items:center;
                gap:10px;
                margin:0 0 12px;
                color:#0b2b46;
            ">
                <div aria-label="Auria Advisory logo mark" style="
                    width:42px;
                    height:42px;
                    flex:0 0 42px;
                    background-image:url('https://auria-advisory.fr/wp-content/uploads/2025/10/Logo-final-vertical-or-blanc-h.png');
                    background-repeat:no-repeat;
                    background-position:left center;
                    background-size:138px auto;
                "></div>
                <div style="line-height:0.95;">
                    <div style="font-family:Georgia, 'Times New Roman', serif;font-size:1.65rem;
                        line-height:0.95;font-weight:900;letter-spacing:0.055em;color:#0b2b46;">AURIA</div>
                    <div style="margin-top:4px;font-size:0.68rem;line-height:1;font-weight:900;
                        letter-spacing:0.22em;color:#0b2b46;">ADVISORY</div>
                </div>
            </div>
            <section class="auria-main-hero auria-compact-hero" style="
                position:relative;
                overflow:hidden;
                border-radius:22px;
                padding:20px 22px;
                margin-bottom:18px;
                color:#ffffff;
                background:linear-gradient(135deg, #061d31, #0b2b46);
                box-shadow:0 18px 44px rgba(11,43,70,0.14);
            ">
                <div class="auria-main-hero-grid" style="
                    display:grid;
                    grid-template-columns:minmax(0, 1.65fr) minmax(280px, 0.65fr);
                    gap:22px;
                    align-items:stretch;
                ">
                    <div>
                        <div style="color:#f1a986;font-size:0.66rem;font-weight:950;
                            letter-spacing:0.08em;text-transform:uppercase;margin-bottom:14px;">
                            Auria Advisory | IFRS 9 ECL & Staging Systems
                        </div>
                        <h1 style="margin:0;color:#ffffff;font-size:clamp(2.15rem,4.2vw,3.65rem);
                            line-height:0.98;font-weight:900;letter-spacing:0;">{APP_NAME}</h1>
                        <p style="max-width:780px;margin:18px 0 0;color:rgba(255,255,255,0.86);
                            font-size:0.9rem;line-height:1.55;">
                            Demonstrateur IFRS 9 pour explorer le staging, les ECL,
                            les scenarios macro et les overlays manageriaux.
                        </p>
                    </div>
                    <aside style="border:1px solid rgba(255,255,255,0.18);border-radius:17px;
                        background:rgba(255,255,255,0.12);padding:17px 16px;backdrop-filter:blur(12px);">
                        <div style="color:#f1a986;font-size:0.68rem;font-weight:950;
                            letter-spacing:0.11em;text-transform:uppercase;margin-bottom:12px;">
                            Perimetre de demonstration
                        </div>
                        <div class="auria-scope-row"><span>Modeles</span><strong>Staging, ECL, scenarios</strong></div>
                        <div class="auria-scope-row"><span>Gouvernance</span><strong>Overlays, audit trail</strong></div>
                        <div style="margin-top:14px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.16);
                            color:rgba(255,255,255,0.80);font-size:0.74rem;line-height:1.45;">
                            Donnees 100% synthetiques - demonstrateur a vocation pedagogique.
                            Ne pas utiliser pour la production, la comptabilisation ou le reporting reglementaire.
                        </div>
                    </aside>
                </div>
            </section>
            <style>
                .auria-main-hero.auria-compact-hero h1 {{
                    font-size:clamp(2.15rem,4.2vw,3.65rem) !important;
                }}
                .auria-scope-row {{
                    display:flex;
                    justify-content:space-between;
                    gap:14px;
                    padding:9px 0;
                    border-bottom:1px solid rgba(255,255,255,0.14);
                    color:#ffffff;
                    font-size:0.78rem;
                }}
                .auria-scope-row span {{
                    color:rgba(255,255,255,0.68);
                    font-size:0.66rem;
                    font-weight:900;
                    letter-spacing:0.08em;
                    text-transform:uppercase;
                }}
                .auria-scope-row strong {{text-align:right;font-weight:900;}}
                @media (max-width:1100px) {{
                    .auria-main-hero.auria-compact-hero h1 {{
                        font-size:clamp(2rem,6vw,3.1rem) !important;
                    }}
                }}
            </style>
            """,
            unsafe_allow_html=True,
        )
        return

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
                align-items:start;
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
                        font-size:clamp(2.8rem, 5.4vw, 4.8rem);
                        line-height:1;
                        font-weight:900;
                        letter-spacing:0;
                    ">{APP_NAME}</h1>
                    <p style="
                        max-width:760px;
                        margin:28px 0 0;
                        color:rgba(255,255,255,0.88);
                        font-size:0.96rem;
                        line-height:1.72;
                    ">
                        Ce demonstrateur illustre, sur un portefeuille entierement synthetique,
                        la chaine de provisionnement IFRS 9 : controle de la qualite des donnees,
                        identification d'une augmentation significative du risque de credit,
                        classement en Stage 1, 2 ou 3, calcul des pertes de credit attendues,
                        prise en compte d'informations prospectives et documentation des jugements manageriaux.
                    </p>
                    <div style="
                        margin-top:24px;
                        padding:18px 20px;
                        border:1px solid rgba(255,255,255,0.12);
                        border-left:4px solid #f1a986;
                        border-radius:0 14px 14px 0;
                        background:rgba(255,255,255,0.08);
                    ">
                        <div style="color:#f1a986;font-size:0.7rem;font-weight:950;
                            letter-spacing:0.1em;text-transform:uppercase;margin-bottom:14px;">
                            Ancrages reglementaires
                        </div>
                        <div class="regulatory-anchor-list">
                            <div class="regulatory-anchor-row">
                                <strong>IFRS 9</strong>
                                <span>Depreciation, ECL 12 mois et lifetime, SICR et informations prospectives.</span>
                            </div>
                            <div class="regulatory-anchor-row">
                                <strong>EBA / GL / 2017 / 06</strong>
                                <span>Gestion du risque de credit et comptabilisation des pertes attendues.</span>
                            </div>
                            <div class="regulatory-anchor-row">
                                <strong>BCE</strong>
                                <span>Gouvernance, qualite des donnees, modeles et jugements experts.</span>
                            </div>
                            <div class="regulatory-anchor-row">
                                <strong>BCBS 239</strong>
                                <span>Agregation et reporting des donnees de risque.</span>
                            </div>
                        </div>
                    </div>
                </div>
                <aside style="
                    position:relative;
                    overflow:hidden;
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
                        margin-bottom:16px;
                    ">Perimetre de demonstration</div>
                    <div class="auria-scope-row"><span>Modeles</span><strong>Staging, ECL, scenarios</strong></div>
                    <div class="auria-scope-row"><span>Gouvernance</span><strong>Overlays, audit trail</strong></div>
                    <div style="
                        margin-top:20px;
                        padding-top:18px;
                        border-top:1px solid rgba(255,255,255,0.16);
                        color:rgba(255,255,255,0.76);
                        font-size:0.78rem;
                        line-height:1.62;
                    ">
                        Donnees 100% synthetiques - demonstrateur a vocation pedagogique.
                        Ne pas utiliser pour la production, la comptabilisation ou le reporting reglementaire.
                    </div>
                </aside>
            </div>
            <div class="auria-home-hero-mark" aria-hidden="true"></div>
        </section>
        <style>
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
            .regulatory-anchor-list {{
                display:grid;
                gap:10px;
            }}
            .regulatory-anchor-row {{
                display:grid;
                grid-template-columns:minmax(120px, 0.72fr) minmax(0, 1.8fr);
                gap:14px;
                align-items:start;
                color:rgba(255,255,255,0.86);
                font-size:0.78rem;
                line-height:1.45;
            }}
            .regulatory-anchor-row strong {{
                color:#ffffff;
                font-size:0.74rem;
                font-weight:900;
                letter-spacing:0.02em;
            }}
            .regulatory-anchor-row span {{
                color:rgba(255,255,255,0.76);
            }}
            .auria-main-hero-grid {{
                position:relative;
                z-index:2;
            }}
            .auria-home-hero-mark {{
                position:absolute;
                right:24px;
                bottom:-62px;
                width:310px;
                height:310px;
                z-index:1;
                opacity:0.20;
                background-image:url('https://auria-advisory.fr/wp-content/uploads/2025/10/picto-rose-trans60.png');
                background-repeat:no-repeat;
                background-position:center;
                background-size:contain;
                transform:rotate(-10deg);
                pointer-events:none;
            }}
            .auria-home-hero-mark::before {{
                content:"";
                position:absolute;
                inset:-34px;
                border:1px solid rgba(241,169,134,0.20);
                border-radius:50%;
            }}
            @media (max-width:720px) {{
                .regulatory-anchor-row {{
                    grid-template-columns:minmax(0, 1fr);
                    gap:3px;
                }}
                .auria-home-hero-mark {{
                    display:none;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )
