# ECL Staging Explorer

ECL Staging Explorer est un demonstrateur MVP pour presenter la logique IFRS 9 de staging, les controles de qualite des donnees et un calcul simplifie des pertes de credit attendues.

Le projet utilise uniquement des donnees synthetiques. Il ne doit pas etre utilise comme moteur de production, ni comme implementation normative complete d'IFRS 9.

L'application est prevue pour etre deployee sur Streamlit Community Cloud avec `app.py` comme fichier principal.

## Fonctionnalites V0.5

- Generation d'un portefeuille synthetique d'environ 1 000 expositions.
- Chargement optionnel d'un fichier CSV ou Excel compatible avec le schema MVP.
- Controles simples de qualite des donnees.
- Score simple de qualite des donnees.
- Affectation Stage 1, Stage 2, Stage 3 avec regles transparentes.
- Commentaire metier expliquant la regle de staging declenchante.
- Calcul ECL simplifie par stage.
- Interface organisee pour une demonstration client : Accueil, Portefeuille, Data Quality, Staging, ECL Calculation, Dashboard, Export.
- Dashboard executif avec KPI, graphiques, management insights et audit view simplifiee.
- Marquage des expositions necessitant une revue metier.
- Scenarios macroeconomiques IFRS 9 Baseline, Downside et Upside.
- ECL par scenario, ECL ponderee et impacts vs baseline.
- Overlays manageriaux predefinis, activables et traces.
- ECL avant overlay, montant d'overlay et ECL apres overlay.
- Audit trail detaille avec run_id, hypotheses, scenarios, overlays et avertissements methodologiques.
- Note de synthese automatique pour comite provisionnement, exportable en Markdown et Word.
- Export Excel multi-onglets dans `outputs/` et telechargement depuis l'application.
- Tests unitaires simples pour les modules metier.

## Parcours de demonstration V0.5

1. Generer ou charger un portefeuille.
2. Controler la qualite des donnees.
3. Determiner le staging IFRS 9.
4. Calculer les ECL.
5. Simuler les scenarios macroeconomiques.
6. Appliquer et documenter les overlays manageriaux.
7. Consulter l'audit trail et la note comite.
8. Analyser les resultats, les insights et exporter.

## KPI disponibles

- EAD totale.
- ECL totale.
- Taux de couverture global ECL / EAD.
- Nombre d'expositions.
- Part des expositions en Stage 2.
- Part des expositions en Stage 3.
- Nombre d'anomalies data quality.
- Nombre de cas necessitant une revue.
- ECL baseline.
- ECL downside.
- ECL upside.
- ECL ponderee.
- Impact downside vs baseline.
- Impact ECL ponderee vs baseline.
- ECL avant overlay.
- Montant total des overlays.
- ECL apres overlay.
- Variation overlays en montant et en pourcentage.
- Top overlay contributeur.

## Visualisations V0.2

- EAD par stage.
- ECL par stage.
- Taux de couverture par stage.
- ECL par produit.
- ECL par secteur.
- Distribution des ratings actuels.
- Matrice Stage initial / Stage recalcule.
- Top 10 des expositions contributrices a l'ECL.
- ECL par scenario.
- Contribution ponderee de chaque scenario.
- Comparaison baseline vs ECL ponderee.
- Impact downside par stage.
- Waterfall ECL avant overlay vers ECL apres overlay.
- Montant d'overlay par type.
- Montant d'overlay par stage.
- Top 10 des expositions les plus impactees par les overlays.

## Scenarios macroeconomiques V0.3

Les scenarios sont volontairement simples et explicables :

| Scenario | Ponderation | Multiplicateur PD | Multiplicateur LGD |
| --- | ---: | ---: | ---: |
| Baseline | 60% | 1.00 | 1.00 |
| Downside | 30% | 1.35 | 1.15 |
| Upside | 10% | 0.85 | 0.95 |

Les ponderations et multiplicateurs sont modifiables dans l'interface. Les PD et LGD ajustees sont capees a 100%.

## Overlays manageriaux V0.4

Les overlays sont des ajustements pedagogiques appliques en pourcentage de l'ECL avant overlay. Si plusieurs overlays s'appliquent a une meme exposition, leurs montants sont additionnes sans dupliquer la ligne.

Overlays predefinis :

- `Commercial Real Estate Stress` : +15% d'ECL sur le secteur Real estate.
- `SME Energy Sensitivity` : +20% d'ECL sur les expositions SME du secteur Energy.
- `Data Quality Uncertainty` : +10% d'ECL sur les expositions avec anomalie data quality critique.
- `Stage 2 Prudence Overlay` : +5% d'ECL sur les expositions Stage 2.
- `Stage 3 Recovery Risk` : +10% d'ECL sur les expositions Stage 3.

## Audit trail et note comite V0.5

Chaque run recoit un identifiant du type `RUN-YYYYMMDD-HHMMSS`. Cet identifiant apparait dans l'application, dans l'export Excel et dans la note de synthese.

L'audit trail detaille centralise la date du run, la version de l'application, les hypotheses de staging et d'ECL, les parametres de scenarios, les overlays actives, les anomalies data quality, les expositions a revoir, les top contributeurs et les avertissements methodologiques.

La note de synthese comite est generee automatiquement a partir des resultats calcules. Elle est factuelle, orientee comite provisionnement et exportable en `.md` ou `.docx`.

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Lancement de l'application

```powershell
streamlit run app.py
```

## Lancement des tests

```powershell
pytest
```

## Architecture

```text
app.py
requirements.txt
README.md
AGENTS.md
data/
modules/
  sample_data.py
  data_quality.py
  staging_engine.py
  ecl_calculator.py
  scenario_engine.py
  overlay_engine.py
  audit_trail.py
  committee_summary.py
  reporting.py
outputs/
tests/
```

La logique metier est centralisee dans `modules/`. L'interface Streamlit orchestre les modules et gere l'affichage, les graphiques et l'export.

## Hypotheses simplificatrices

- Les ratings sont representes par des notes numeriques de 1 a 10.
- Une hausse de rating numerique correspond a une degradation du risque.
- Le Stage 3 est prioritaire sur le Stage 2.
- Le Stage 1 utilise la PD 12 mois, le Stage 2 la PD lifetime, le Stage 3 une PD de 100 %.
- Les scenarios macro appliquent des multiplicateurs simples sur PD et LGD.
- Les ponderations par defaut sont 60% Baseline, 30% Downside et 10% Upside.
- Les overlays sont appliques sur l'ECL avant overlay et s'additionnent en montant.
- Les overlays ne modifient pas le stage, la PD, la LGD ou l'EAD sous-jacents.
- La note comite est generee automatiquement a partir des resultats calcules et reste factuelle.
- Le run_id est horodate mais ne constitue pas encore un audit trail versionne complet.
- Les PD, LGD, EAD, maturites et indicateurs de defaut sont synthetiques.
- Les effets de discounting ne sont pas encore modelises.

## Limites du MVP

- Pas de moteur de production IFRS 9.
- Pas de validation avancee de schema en entree.
- Pas de stockage persistant des historiques de runs.
- Pas de modele macroeconometrique avance.
- Pas de scenarios sectoriels ou geographiques.
- Pas de workflow d'approbation des overlays.
- Pas de versioning detaille des overlays.
- Pas de calcul de cash-flows actualises.
- Pas de gestion multi-entites ou multi-devises.

## Prochaines etapes V0.6

- Polish commercial pour une demonstration client.
- Controles de coherence metier avances.
- Amelioration de la mise en page de la note comite.
- Versioning persistant des runs.
- Preparation d'un jeu de scenarios de demo guide.
- Formaliser un dictionnaire de donnees et une validation de schema.
- Enrichir les graphiques par produit, secteur, pays et vintage.
