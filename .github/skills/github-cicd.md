# Skill: github-cicd

## Rôle

Configurer le pipeline CI/CD GitHub Actions pour déploiement automatique à chaque push sur main.

## Prérequis

- `gh` CLI configuré (`gh auth status` OK)
- Application déployée et fonctionnelle
- Clé SSH privée disponible (celle utilisée pour SSH)
- Repo GitHub accessible en écriture

## Procédure

### 1. Créer le workflow GitHub Actions

```bash
mkdir -p .github/workflows
```

Créer `.github/workflows/deploy.yml` :

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            set -e
            cd /opt/<PROJECT_NAME>
            git fetch origin main
            git reset --hard origin/main
            docker compose up --build -d
            sleep 15
            docker compose ps
            curl -sf http://localhost/api/v1/products/ || (echo "❌ Backend healthcheck failed" && exit 1)
            curl -sf http://localhost/ || (echo "❌ Frontend healthcheck failed" && exit 1)
            echo "✅ Deployment successful"
```

### 2. Ajouter les secrets GitHub

```bash
gh secret set VPS_HOST -b "${VPS_IP}" -R <OWNER>/<REPO>
gh secret set VPS_USER -b "${VPS_USER}" -R <OWNER>/<REPO>
gh secret set VPS_SSH_KEY -b "$(cat ${SSH_KEY:-~/.ssh/id_rsa})" -R <OWNER>/<REPO>
```

### 3. Vérifier les secrets

```bash
gh secret list -R <OWNER>/<REPO>
```

Doit afficher : `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.

### 4. Committer et pousser le workflow

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: add automated deployment pipeline"
git push origin main
```

### 5. Surveiller le premier run

```bash
gh run watch -R <OWNER>/<REPO>
```

Résultat attendu : ✅ pipeline vert, déploiement exécuté.

## Version avec tests (recommandée)

Si le projet a des tests, utiliser la version complète :

```yaml
jobs:
  test-backend:
    # ... tests Django avec SQLite ...

  test-frontend:
    # ... tests React avec vitest ...

  deploy:
    needs: [test-backend, test-frontend]
    # ... déploiement SSH ...
```

## Vérification

```
✅ Workflow .github/workflows/deploy.yml créé
✅ Secrets GitHub configurés (VPS_HOST, VPS_USER, VPS_SSH_KEY)
✅ Pipeline déclenché → succès
```

## Fallback

| Problème | Action |
|---|---|
| `gh` non configuré | `gh auth login` |
| `gh secret set` échoue | Ajouter les secrets via l'interface web GitHub |
| Pipeline rouge | Vérifier les logs dans l'onglet Actions |
| SSH denied (pipeline) | Vérifier le format de la clé dans VPS_SSH_KEY |
| Workflow refusé (OAuth) | `git remote set-url origin git@github.com:...` |

## Leçons ClickMart

- Le premier pipeline n'avait pas de tests → déployait du code cassé
- Le `git pull` échouait à cause de modifications locales → `git reset --hard`
- Le push était refusé (OAuth sans scope workflow) → passé en SSH `git@github.com`
- `sleep 15` crucial : le backend met ~20s à démarrer (migrations + collectstatic + gunicorn)
- Le healthcheck post-deploy évite de découvrir 30 min plus tard que l'app est down
