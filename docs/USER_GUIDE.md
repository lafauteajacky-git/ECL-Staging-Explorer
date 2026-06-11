# ECL Staging Explorer - User Guide

## 1. Lancer l'application

Depuis le dossier du projet :

```powershell
streamlit run app.py
```

L'application s'ouvre dans le navigateur. Le demonstrateur utilise uniquement des donnees synthetiques et n'est pas destine a la production.

## 2. Generer un portefeuille

Dans la barre laterale :

1. Choisir `Generer un portefeuille synthetique`.
2. Selectionner un `Demo Portfolio Profile`.
3. Choisir le nombre d'expositions.
4. Cliquer sur `Generer le portefeuille synthetique`.

Les profils disponibles sont : `Balanced Portfolio`, `Low Risk Portfolio`, `Deteriorated Portfolio`, `Data Quality Issues Portfolio` et `CRE Stress Portfolio`.

## 3. Lire les KPI

Les KPI principaux sont disponibles dans l'accueil et le dashboard :

- `EAD totale` : exposition totale au defaut.
- `ECL totale` : perte de credit attendue calculee par le MVP.
- `Taux de couverture` : ECL / EAD.
- `Part Stage 2` et `Part Stage 3` : part des expositions ayant migre vers des stages plus sensibles.
- `Alertes metier` : controles de coherence a revoir.

## 4. Interpreter le staging

L'onglet `Staging` montre le stage final, la regle declenchante et un commentaire metier.

Les regles simplifiees sont :

- Stage 3 si defaut ou DPD >= 90.
- Stage 2 si DPD >= 30, degradation de rating >= 2 crans, forbearance ou watchlist.
- Stage 1 sinon.

## 5. Lire les resultats ECL

L'onglet `ECL Calculation` affiche l'ECL ligne a ligne.

- Stage 1 : PD 12M x LGD x EAD.
- Stage 2 : PD lifetime x LGD x EAD.
- Stage 3 : 100% x LGD x EAD.

Les champs `review_required` et `review_reason` indiquent les expositions a revoir.

## 6. Utiliser les scenarios macro

Dans la barre laterale, ajuster les ponderations et multiplicateurs PD/LGD des scenarios `Baseline`, `Downside` et `Upside`.

L'onglet `Macro Scenarios` controle que les ponderations totalisent 100% et affiche :

- ECL par scenario.
- ECL ponderee.
- Impact downside vs baseline.
- Impact weighted ECL vs baseline.

## 7. Utiliser les overlays

Dans la barre laterale, activer ou desactiver les overlays manageriaux.

L'onglet `Management Overlays` affiche :

- ECL avant overlay.
- Montant total des overlays.
- ECL apres overlay.
- Synthese par overlay.
- Expositions impactees.

## 8. Lire l'audit trail

L'onglet `Audit Trail` centralise :

- run_id ;
- date et heure du run ;
- version de l'application ;
- disclaimer demo safe ;
- hypotheses de staging et ECL ;
- parametres de scenarios ;
- overlays actives ;
- alertes data quality et coherence metier.

## 9. Generer la note comite

L'onglet `Committee Summary` genere une note Markdown factuelle pour comite provisionnement.

La note peut etre telechargee en `.md` ou en `.docx`.

## 10. Exporter les resultats

L'onglet `Export` permet :

- de telecharger un fichier Excel ;
- d'ecrire l'export dans le dossier `outputs/`.

Le fichier suit le format :

```text
ECL_Staging_Explorer_RUN-YYYYMMDD-HHMMSS.xlsx
```

L'export contient notamment les onglets `Disclaimer`, `Portfolio`, `Data Quality Issues`, `Staging Results`, `ECL Results`, `Risk Parameters`, `Lifetime PD Curve`, `Dashboard Summary`, `Audit Trail`, `Committee Summary`, `Business Consistency`, `Demo Storyline` et `Client Discussion Points`.

## Lire les parametres de risque

L'onglet `Parametres de risque` presente :

- la PD 12 mois moyenne ponderee par l'EAD ;
- la PD lifetime cumulative moyenne ;
- le multiplicateur entre PD lifetime et PD 12 mois ;
- la LGD moyenne ponderee ;
- la courbe de PD cumulative par stage ;
- les PD par rating et les PD marginales annuelles.

Dans la V2, la PD lifetime est calculee avec une hypothese de taux de hasard annuel constant :

`PD cumulative(t) = 1 - (1 - PD 12 mois)^t`

Cette formule est pedagogique. Elle ne remplace pas des courbes de PD calibrees, des matrices de transition ou des modeles PIT/TTC utilises en production.
