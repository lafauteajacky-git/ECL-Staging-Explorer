# AGENTS.md

## Projet

ECL Staging Explorer est un demonstrateur Streamlit en Python pour expliquer le staging IFRS 9 et un calcul ECL simplifie sur donnees synthetiques.

## Principes de developpement

- Utiliser uniquement des donnees synthetiques.
- Garder la logique metier dans `modules/`.
- Garder `app.py` centre sur l'interface, l'orchestration et l'export.
- Ecrire du code lisible, testable et extensible.
- Documenter les hypotheses simplificatrices quand elles affectent la logique metier.
- Ne pas transformer le MVP en moteur de production.
- Ajouter des tests pour toute nouvelle regle metier.
- Privilegier la lisibilite a l'optimisation prematuree.

## Stack

- Python
- Streamlit
- pandas
- numpy
- plotly
- openpyxl
- pytest

## Commandes utiles

```powershell
pip install -r requirements.txt
streamlit run app.py
pytest
```

## Modules

- `ui/theme.py` : theme visuel Auria et styles Streamlit.
- `ui/branding.py` : en-tetes et composants de marque Auria.
- `ui/components.py` : composants de presentation reutilisables, notamment les cartes KPI.
- `modules/sample_data.py` : generation de portefeuille et profils de demonstration synthetiques.
- `modules/data_quality.py` : controles simples de qualite des donnees.
- `modules/data_types.py` : coercition partagee des types de donnees, notamment les indicateurs booleens.
- `modules/calculation_utils.py` : helpers numeriques communs, notamment les divisions securisees.
- `modules/staging_engine.py` : regles de staging MVP.
- `modules/ecl_calculator.py` : calcul ECL simplifie.
- `modules/scenario_engine.py` : scenarios macroeconomiques pedagogiques Baseline, Downside et Upside.
- `modules/overlay_engine.py` : overlays manageriaux pedagogiques appliques a l'ECL avant overlay.
- `modules/business_checks.py` : controles de coherence metier, storyline de demo et discussion points.
- `modules/migration_analysis.py` : matrices de transition, indicateurs de migration et cliff effects.
- `modules/audit_trail.py` : audit trail detaille du run et generation du run_id.
- `modules/committee_summary.py` : note de synthese comite provisionnement.
- `modules/demo_config.py` : nom de l'application, disclaimer demo safe et prefixe d'export.
- `modules/reporting.py` : exports et helpers de reporting.

## Documentation

- `docs/USER_GUIDE.md` : guide utilisateur.
- `docs/DEMO_SCRIPT.md` : script de demonstration client.
- `docs/METHODOLOGY_NOTES.md` : hypotheses simplificatrices.
- `docs/ROADMAP.md` : evolutions possibles.

## Tests attendus

Les changements sur les modules metier doivent etre couverts par des tests unitaires dans `tests/`.
