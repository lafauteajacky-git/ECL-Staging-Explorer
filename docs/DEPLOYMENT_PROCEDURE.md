# Procedure de deploiement - PowerShell, GitHub et Streamlit Cloud

Cette note explique comment mettre a jour l'application **ECL Staging Explorer** depuis le dossier local Windows jusqu'a Streamlit Community Cloud.

## 1. Ouvrir PowerShell dans le projet

```powershell
cd "C:\Users\PC\Documents\ECL Staging Explorer"
```

Verifier que l'on est au bon endroit :

```powershell
dir
```

On doit voir notamment :

- `app.py`
- `requirements.txt`
- `README.md`
- `modules`
- `tests`

## 2. Verifier Git

```powershell
git --version
```

Si PowerShell repond que `git` n'est pas reconnu :

1. Fermer PowerShell.
2. Rouvrir PowerShell.
3. Relancer `git --version`.

Si cela ne marche toujours pas, Git n'est pas dans le `PATH`. Reinstaller Git for Windows depuis :

```text
https://git-scm.com/download/win
```

Pendant l'installation, choisir l'option qui ajoute Git au PATH.

## 3. Verifier la branche active

```powershell
git branch --show-current
```

Cas frequents :

- `main` : branche principale, celle lue par Streamlit Cloud dans la plupart des cas.
- `v0.5-audit-trail` : branche de developpement V0.5.

## 4. Verifier l'etat du depot

```powershell
git status
```

Si Git affiche :

```text
nothing to commit, working tree clean
```

Il n'y a rien a enregistrer.

Si Git affiche des fichiers modifies ou non suivis, il faut les ajouter et committer.

## 5. Configurer son identite Git si necessaire

Si le commit affiche :

```text
Author identity unknown
Please tell me who you are.
```

Configurer l'identite Git :

```powershell
git config --global user.name "lafauteajacky-git"
git config --global user.email "lafauteajacky-git@users.noreply.github.com"
```

Puis relancer le commit.

## 6. Creer une branche de travail

Pour travailler sans casser `main` :

```powershell
git checkout -b v0.5-audit-trail
```

Si la branche existe deja :

```powershell
git checkout v0.5-audit-trail
```

## 7. Ajouter les fichiers modifies

```powershell
git add .
```

Verifier ce qui va etre commite :

```powershell
git status
```

## 8. Faire un commit

Exemple :

```powershell
git commit -m "Add V0.5 audit trail and committee summary"
```

Si le message `Author identity unknown` apparait, revenir a l'etape 5.

### Cas frequent : `Changes not staged for commit`

Si `git status` affiche :

```text
Changes not staged for commit:
  modified: README.md
  modified: app.py

Untracked files:
  docs/DEPLOYMENT_PROCEDURE.md

no changes added to commit
```

Cela veut dire que Git voit les modifications, mais qu'elles ne sont pas encore ajoutees au prochain commit.

Ajouter les fichiers :

```powershell
git add app.py README.md docs/DEPLOYMENT_PROCEDURE.md
```

Ou, pour ajouter toutes les modifications du dossier :

```powershell
git add .
```

Verifier :

```powershell
git status
```

Les fichiers doivent apparaitre dans :

```text
Changes to be committed
```

Puis faire le commit :

```powershell
git commit -m "Align Streamlit UI with Auria visual identity"
```

Enfin pousser vers GitHub :

```powershell
git push origin main
```

Apres le push, Streamlit Cloud se met normalement a jour automatiquement. Si ce n'est pas le cas, aller dans `Manage app`, puis cliquer sur `Reboot app` ou `Rerun`.

## 9. Pousser une branche vers GitHub

Si l'on est sur une branche de travail :

```powershell
git push -u origin v0.5-audit-trail
```

Si l'on pousse directement `main` :

```powershell
git push origin main
```

Si GitHub demande une authentification, suivre la fenetre GitHub ou utiliser Git Credential Manager.

## 10. Merger une branche V0.5 dans main

Quand la branche V0.5 est prete :

```powershell
git checkout main
git pull origin main
git merge v0.5-audit-trail
```

### Si Git ouvre un editeur avec le message de merge

On peut voir un ecran du type :

```text
Merge branch 'v0.5-audit-trail'
# Please enter a commit message...
```

C'est normal. L'editeur est souvent Vim.

Pour sauvegarder et quitter :

1. Appuyer sur `Esc`.
2. Taper :

```text
:wq
```

3. Appuyer sur `Entree`.

Ensuite pousser `main` :

```powershell
git push origin main
```

## 11. Verifier que GitHub est a jour

Aller sur :

```text
https://github.com/lafauteajacky-git/ECL-Staging-Explorer
```

Verifier :

- la branche `main` ;
- le dernier commit ;
- la presence des nouveaux fichiers ;
- `app.py` a jour.

## 12. Verifier Streamlit Cloud

Ouvrir l'application :

```text
https://ecl-staging-explorer-demo.streamlit.app
```

Pour verifier que la V0.5 est bien deployee, chercher :

- l'onglet `Audit Trail` ;
- l'onglet `Committee Summary` ;
- un `Run ID` du type `RUN-YYYYMMDD-HHMMSS` ;
- la version `V0.5`.

## 13. Forcer la mise a jour Streamlit si necessaire

Si l'application publique ne montre pas les dernieres modifications :

1. Aller sur :

```text
https://share.streamlit.io
```

2. Ouvrir l'app.
3. Cliquer sur `Manage app`.
4. Cliquer sur `Reboot app` ou `Rerun`.
5. Attendre la fin du build.

## 14. Verifier les logs Streamlit

Si l'app ne demarre pas :

1. Streamlit Cloud.
2. `Manage app`.
3. `Logs`.

Lire le message d'erreur.

Erreurs frequentes :

### ModuleNotFoundError

Exemple :

```text
ModuleNotFoundError: No module named 'docx'
```

Solution : ajouter la dependance dans `requirements.txt`, par exemple :

```text
python-docx>=1.1
```

Puis :

```powershell
git add requirements.txt
git commit -m "Add missing dependency"
git push origin main
```

### ImportError

Exemple :

```text
ImportError: cannot import name ...
```

Solution :

- verifier que le fichier appele contient bien la fonction ou constante ;
- verifier que le fichier a ete commite ;
- verifier que Streamlit lit bien la branche `main`.

### Mauvaise branche Streamlit

Si Streamlit lit `main` mais que les changements sont sur `v0.5-audit-trail`, il faut soit :

- merger dans `main` ;
- ou changer la branche dans `Manage app > Settings`.

## 15. Branches : quelle option choisir ?

### Option simple

Travailler directement sur `main`.

Avantage : Streamlit se met a jour automatiquement.

Risque : une erreur peut casser l'application publique.

### Option recommandee

Travailler sur une branche, par exemple :

```text
v0.5-audit-trail
```

Puis merger dans `main` quand les tests sont OK.

## 16. Commandes types pour une evolution complete

```powershell
cd "C:\Users\PC\Documents\ECL Staging Explorer"
git checkout main
git pull origin main
git checkout -b v0.6-polish-demo

# Faire les modifications

python -m pytest
git status
git add .
git commit -m "Add V0.6 demo polish"
git push -u origin v0.6-polish-demo

# Quand c'est valide
git checkout main
git pull origin main
git merge v0.6-polish-demo
git push origin main
```

## 17. Commandes utiles de diagnostic

Voir la branche courante :

```powershell
git branch --show-current
```

Voir l'etat :

```powershell
git status
```

Voir les derniers commits :

```powershell
git log --oneline -5
```

Voir le remote GitHub :

```powershell
git remote -v
```

Lancer les tests :

```powershell
python -m pytest
```

Lancer l'application en local :

```powershell
streamlit run app.py
```

Ou :

```powershell
python -m streamlit run app.py
```
