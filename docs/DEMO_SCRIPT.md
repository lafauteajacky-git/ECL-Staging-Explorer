# ECL Staging Explorer - Demo Script 10-15 minutes

## Objectif de la demo

Montrer comment le demonstrateur transforme une logique IFRS 9 souvent technique en un parcours transparent, explicable et auditable pour les equipes Risques, Finance, Modeles, Audit et Management.

## 1. Introduction IFRS 9 - 1 minute

Message cle : IFRS 9 impose de suivre la deterioration du risque de credit, de calculer les pertes attendues et de documenter les hypotheses utilisees.

Insister sur trois enjeux client :

- explicabilite du staging ;
- qualite des donnees ;
- gouvernance des scenarios, overlays et restitutions comite.

## 2. Portefeuille synthetique - 1 minute

Ouvrir l'onglet `Accueil`.

Rappeler que les donnees sont 100% synthetiques. Choisir un profil selon le message voulu :

- `Balanced Portfolio` pour une demo standard ;
- `Deteriorated Portfolio` pour illustrer une deterioration ;
- `Data Quality Issues Portfolio` pour parler controles ;
- `CRE Stress Portfolio` pour parler concentration sectorielle.

## 3. Revue Data Quality - 1 minute

Ouvrir `Data Quality`.

Montrer :

- nombre d'anomalies ;
- score qualite ;
- types d'anomalies detectees.

Message cle : la qualite des donnees conditionne la fiabilite de l'ECL.

## 4. Coherence metier - 1 minute

Ouvrir `Parametres de risque`.

Presenter la PD 12 mois, la PD lifetime et la courbe cumulative par stage. Expliquer que la V2 utilise une hypothese de taux de hasard constant, transparente et facilement remplacable par des courbes calibrees dans une implementation client.

Montrer le score de coherence, les alertes et les recommandations.

Message cle : au-dela de la data quality technique, il faut controler la coherence entre stage, defaut, DPD, PD, LGD et ECL.

## 5. Determination du staging - 1 minute

Ouvrir `Staging`.

Montrer les stages, les regles declenchantes et les commentaires metier.

Message cle : chaque affectation doit etre explicable et defendable.

## 6. Calcul ECL - 1 minute

Ouvrir `ECL Calculation`.

Expliquer les formules simples par stage :

- Stage 1 : PD 12M ;
- Stage 2 : PD lifetime ;
- Stage 3 : proxy 100% x LGD x EAD.

Message cle : le MVP reste volontairement pedagogique.

## 7. Dashboard executif - 2 minutes

Ouvrir `Dashboard`.

Montrer :

- EAD totale ;
- ECL totale ;
- taux de couverture ;
- ECL par stage, produit et secteur ;
- top contributeurs ;
- management insights ;
- client discussion points.

Message cle : le dashboard transforme le calcul en support de pilotage.

## 8. Simulation macro downside - 1 minute

Dans la barre laterale, augmenter le poids du downside ou ses multiplicateurs.

Ouvrir `Macro Scenarios`.

Montrer l'impact downside vs baseline et l'ECL ponderee.

Message cle : les hypotheses macro doivent etre explicites, testables et documentees.

## 9. Application d'overlays - 1 minute

Ouvrir `Management Overlays`.

Activer/desactiver un overlay, puis montrer :

- ECL avant overlay ;
- montant overlay ;
- ECL apres overlay ;
- justification.

Message cle : les ajustements experts doivent etre traces et gouvernes.

## 10. Audit trail - 1 minute

Ouvrir `Audit Trail`.

Montrer le run_id, la version, les hypotheses, les parametres et les alertes.

Message cle : l'auditabilite commence par la tracabilite des hypotheses.

## 11. Note comite - 1 minute

Ouvrir `Committee Summary`.

Montrer la structure de la note et les exports Markdown/Word.

Message cle : l'outil produit une restitution sobre et factuelle pour comite provisionnement.

## 12. Ouverture vers cas d'usage client - 1 minute

Questions de conclusion :

- Quels seuils SICR sont utilises aujourd'hui ?
- Comment les overlays sont-ils documentes ?
- Quels controles data quality sont critiques ?
- Comment les scenarios macro sont-ils gouvernes ?
- Quels livrables comite ou audit pourraient etre automatises ?
