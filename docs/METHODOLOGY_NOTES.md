# ECL Staging Explorer - Methodology Notes

## Statut du demonstrateur

ECL Staging Explorer est un demonstrateur pedagogique et commercial. Il utilise uniquement des donnees synthetiques et ne doit pas etre utilise comme moteur IFRS 9 de production.

## Donnees synthetiques

Le portefeuille est genere artificiellement avec des champs representatifs d'un schema IFRS 9 simplifie : EAD, PD, LGD, rating, DPD, defaut, forbearance, watchlist, collateraux et LTV.

Les distributions ne sont pas calibrees sur des donnees bancaires reelles.

## Regles de staging simplifiees

Le demonstrateur distingue le stage a l'origine (`initial_stage`), le stage a la
cloture precedente (`previous_stage`) et le stage recalcule. Les transitions
utilisent des periodes de cure pedagogiques :

- Stage 3 vers Stage 2 : disparition du defaut et cure minimale de 3 mois ;
- Stage 2 vers Stage 1 : disparition du SICR, paiements normalises et probation minimale de 6 mois ;
- Stage 3 vers Stage 1 : cas exceptionnel, cure de 12 mois, absence de SICR et justification renforcee ;
- Stage 2 vers Stage 3 : defaut ou credit-impaired, notamment 90 DPD, UTP, faillite probable ou restructuration distressed ;
- Stage 1 vers Stage 2 : SICR via DPD, degradation de rating, hausse de PD, watchlist, forbearance ou signal macro-sectoriel.

Ces durees sont des hypotheses de demonstration et doivent etre remplacees par
les politiques internes et exigences applicables dans toute implementation reelle.

Les regles appliquees sont volontairement simples :

- Stage 3 si defaut ou DPD >= 90.
- Stage 2 si DPD >= 30.
- Stage 2 si degradation de rating >= 2 crans.
- Stage 2 si forbearance ou watchlist.
- Stage 1 sinon.

Une implementation reelle doit etre adaptee a la politique SICR, aux definitions de defaut, aux cures periods et aux exigences internes de gouvernance.

## PD 12M et PD lifetime

Les PD 12 mois sont generees de maniere synthetique a partir d'une logique simple de rating.

Depuis la V2, la PD lifetime est calculee a partir de la PD 12 mois et de la maturite residuelle selon :

`PD cumulative(t) = 1 - (1 - PD 12 mois)^t`

Cette approche suppose un taux de hasard annuel constant. La PD marginale correspond a la variation de PD cumulative entre deux horizons successifs. Un horizon minimal d'un an est applique pour rester coherent avec la convention simplifiee de PD 12 mois du demonstrateur.

Il n'y a pas de courbe PIT/TTC calibree, de matrice de transition, de segmentation modele, de vintage analysis ou de validation statistique.

## LGD simplifiee

La LGD est generee comme un taux synthetique. Le MVP ne modelise pas les recouvrements, garanties, couts de recouvrement, haircuts de collateraux ou delais de recovery.

## Scenarios macroeconomiques

Les scenarios `Baseline`, `Downside` et `Upside` appliquent des multiplicateurs simples sur PD et LGD.

Il n'y a pas de modele macroeconometrique reel, pas de variable PIB, chomage, taux ou immobilier, et pas de calibration statistique.

## Overlays manageriaux

Les overlays sont illustratifs. Ils s'appliquent en pourcentage de l'ECL avant overlay et leurs impacts sont additionnes lorsqu'une exposition remplit plusieurs criteres.

Une implementation reelle devrait inclure une gouvernance d'approbation, une justification documentee, un versioning et une revue periodique.

## Audit trail et note comite

L'audit trail centralise les hypotheses et resultats du run. Il ne constitue pas encore un stockage persistant, horodate et versionne au sens production.

La note comite est generee automatiquement a partir des resultats disponibles. Elle doit etre revue par un expert avant toute utilisation externe.

## Disclaimer methodologique

Toute implementation reelle doit etre adaptee :

- aux politiques internes de la banque ;
- aux exigences IFRS 9 applicables ;
- aux definitions internes de defaut et SICR ;
- aux modeles valides ;
- au cadre de controle interne, audit et gouvernance.
