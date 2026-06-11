# ECL Staging Explorer

**ECL Staging Explorer** est un demonstrateur Streamlit pour presenter, de maniere pedagogique, la chaine IFRS 9 de staging et de calcul d'ECL.

Baseline commerciale : **IFRS 9 ECL & Staging Demonstrator**.

Message principal : transformer le provisionnement IFRS 9 en un outil de pilotage transparent, explicable et auditable.

## Objectif du demonstrateur

Le demonstrateur aide a illustrer en rendez-vous client ou en atelier interne :

- la generation d'un portefeuille synthetique ;
- les controles de qualite des donnees ;
- les controles de coherence metier ;
- l'affectation Stage 1 / Stage 2 / Stage 3 ;
- le calcul ECL simplifie ;
- l'impact de scenarios macroeconomiques ;
- les overlays manageriaux ;
- le dashboard executif ;
- l'audit trail ;
- la note de synthese comite ;
- les exports Excel multi-onglets.

## Avertissement sur les donnees

**Donnees 100% synthetiques - demonstrateur a vocation pedagogique et commerciale. Ne pas utiliser pour la production, la comptabilisation ou le reporting reglementaire.**

La V1 ne propose aucun import de fichier externe. Tous les portefeuilles sont generes localement par le moteur de donnees synthetiques du demonstrateur.

## Fonctionnalites principales V1

- Profils de portefeuille de demonstration : `Balanced`, `Low Risk`, `Deteriorated`, `Data Quality Issues`, `CRE Stress`.
- Data quality checks et score qualite.
- Business consistency checks et score de coherence metier.
- Moteur de staging IFRS 9 simplifie et explicable.
- Calcul ECL par stage.
- Scenarios macro `Baseline`, `Downside`, `Upside`.
- Overlays manageriaux predefinis.
- Dashboard executif avec KPI, graphiques, insights et discussion points.
- Audit trail detaille avec run_id.
- Note de synthese comite exportable en Markdown et Word.
- Export Excel multi-onglets avec disclaimer.
- Documentation utilisateur, script de demo, notes methodologiques et roadmap.
- Validation renforcee des ponderations et multiplicateurs macroeconomiques.
- Desactivation complete possible des overlays sans application implicite.
- Coercition stricte des indicateurs booleens et bornage des PD/LGD entre 0% et 100%.

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si `python` n'est pas reconnu sous Windows, verifier l'installation Python ou utiliser le lanceur configure sur votre poste.

## Lancement de l'application

```powershell
streamlit run app.py
```

## Lancement des tests

```powershell
pytest
```

## Commandes Makefile

Si `make` est disponible :

```powershell
make install
make run
make test
make clean-outputs
```

Commandes equivalentes :

```powershell
pip install -r requirements.txt
streamlit run app.py
pytest
Remove-Item outputs\*.xlsx, outputs\*.log, outputs\*.md, outputs\*.docx -ErrorAction SilentlyContinue
```

## Parcours de demonstration recommande

1. Ouvrir `Accueil` et rappeler le cadre demo safe.
2. Choisir un `Demo Portfolio Profile`.
3. Revoir le portefeuille synthetique.
4. Lire les controles `Data Quality`.
5. Lire les controles `Business Consistency`.
6. Presenter le `Staging`.
7. Presenter le calcul `ECL Calculation`.
8. Simuler un scenario macro downside.
9. Activer/desactiver des overlays.
10. Lire le `Dashboard` et les `Client Discussion Points`.
11. Ouvrir l'`Audit Trail`.
12. Generer la `Committee Summary`.
13. Exporter le fichier Excel.

## Profils de portefeuille disponibles

- `Balanced Portfolio` : profil equilibre.
- `Low Risk Portfolio` : faible risque, faible migration Stage 2/3.
- `Deteriorated Portfolio` : deterioration du risque, hausse Stage 2/3.
- `Data Quality Issues Portfolio` : anomalies de donnees plus visibles.
- `CRE Stress Portfolio` : concentration immobilier commercial et stress sectoriel.

## Structure du projet

```text
app.py
requirements.txt
README.md
AGENTS.md
Makefile
.env.example
data/
docs/
  MVP_SPEC.md
  USER_GUIDE.md
  DEMO_SCRIPT.md
  METHODOLOGY_NOTES.md
  ROADMAP.md
  DEPLOYMENT_PROCEDURE.md
modules/
  sample_data.py
  data_quality.py
  business_checks.py
  staging_engine.py
  ecl_calculator.py
  scenario_engine.py
  overlay_engine.py
  reporting.py
  audit_trail.py
  committee_summary.py
  demo_config.py
outputs/
tests/
```

La logique metier est dans `modules/`. L'interface `app.py` orchestre les modules, les graphiques et les exports.

## Documentation

- [User Guide](docs/USER_GUIDE.md)
- [Demo Script](docs/DEMO_SCRIPT.md)
- [Methodology Notes](docs/METHODOLOGY_NOTES.md)
- [Roadmap](docs/ROADMAP.md)
- [Deployment Procedure](docs/DEPLOYMENT_PROCEDURE.md)

## Limites du MVP

- Pas de moteur IFRS 9 de production.
- Pas de donnees reelles.
- Pas de modele macroeconometrique.
- Pas de courbes PD lifetime calibrees.
- Pas de cash-flows actualises.
- Pas de collateraux avances.
- Pas de workflow d'approbation des overlays.
- Pas de stockage persistant des runs.
- Pas de comparaison historisee des runs.
- Pas de gestion multi-entites, multi-devises ou multi-utilisateurs.

## Roadmap

Les prochaines evolutions possibles sont detaillees dans [docs/ROADMAP.md](docs/ROADMAP.md).

Priorite V0.8 proposee :

- deploiement local / cloud leger ;
- packaging demo ;
- support de presentation commerciale ;
- checklist de demonstration ;
- tests end-to-end Streamlit.

## Disclaimer methodologique

Ce projet est un demonstrateur. Les regles, parametres, scenarios et overlays sont simplificateurs. Toute implementation reelle doit etre adaptee aux politiques internes de la banque, aux modeles valides, aux definitions de defaut et SICR, au cadre de controle interne, aux exigences audit et aux obligations reglementaires applicables.
