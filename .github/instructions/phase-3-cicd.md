# Phase 3 — CI/CD (optionnelle)

## Objectif

Configurer le déploiement automatique via GitHub Actions :
- Push sur main → déploiement automatique sur le serveur

## Skills à charger

1. `github-cicd` — Créer le workflow, configurer les secrets

## Déroulement

```
1. github-cicd
   ├── Créer .github/workflows/deploy.yml
   │   (appleboy/ssh-action → git fetch + reset --hard + docker compose up)
   ├── Ajouter les secrets GitHub :
   │   gh secret set VPS_HOST -b "<IP>"
   │   gh secret set VPS_USER -b "<USER>"
   │   gh secret set VPS_SSH_KEY -b "$(cat ~/.ssh/id_rsa)"
   ├── git add && git commit && git push
   └── gh run watch (vérifier que le pipeline passe)
```

## Version du workflow

### Basique (sans tests)

```yaml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            set -e
            cd /opt/<PROJECT>
            git fetch origin main
            git reset --hard origin/main
            docker compose up --build -d
            sleep 15
            docker compose ps
            curl -sf http://localhost/ || exit 1
            curl -sf http://localhost/api/v1/products/ || exit 1
            echo "✅ Deployment successful"
```

### Avec tests (recommandé si le projet a des tests)

```yaml
jobs:
  test-backend:
    # Exécute les tests Django
  test-frontend:
    # Exécute les tests React + build
  deploy:
    needs: [test-backend, test-frontend]
    # Déploiement seulement si les tests passent
```

## Checkpoint

```
✅ Workflow .github/workflows/deploy.yml créé
✅ Secrets GitHub configurés
✅ Pipeline vert → déploiement OK
```

→ Chaque `git push` sur `main` déploie automatiquement.
