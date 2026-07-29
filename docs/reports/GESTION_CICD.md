# Gestion du Workflow CI/CD — ClickMart

> **Date** : 2026-07-29
> **Version** : 2.0
> **Fichier** : `.github/workflows/automate.yml`

---

## Architecture du pipeline

```
git push main|stg|dev
        │
        ▼
┌─────────────────────────────────────────────┐
│              GitHub Actions                   │
│                                               │
│  ┌──────────┐  ┌───────────┐                 │
│  │test-backend│  │test-frontend│  (parallèle) │
│  │ 67 tests  │  │ 11 tests   │               │
│  └────┬─────┘  └─────┬─────┘                 │
│       └──────┬───────┘                        │
│              ▼                                │
│  ┌──────────────────────┐                    │
│  │   build-and-push     │  (main/stg only)   │
│  │   ghcr.io registry   │                    │
│  └──────────┬───────────┘                    │
│             ▼                                │
│  ┌──────────────────────┐                    │
│  │  deploy-production   │  (main only)       │
│  │  deploy-staging      │  (stg only)        │
│  │  Linode pull + run   │                    │
│  └──────────────────────┘                    │
└─────────────────────────────────────────────┘
```

| Branche | Tests | Build & Push | Déploiement |
|---|---|---|---|
| `dev` | ✅ | ❌ | ❌ |
| `stg` | ✅ | ✅ | ✅ Staging (:8080) |
| `main` | ✅ | ✅ | ✅ Production (:80/443) |

---

## Jobs détaillés

### test-backend

```yaml
runs-on: ubuntu-latest
steps:
  - checkout
  - setup-python 3.11 (cache pip)
  - pip install -r requirements.txt
  - ruff check (lint)
  - python manage.py test (67 tests)
env:
  SECRET_KEY: ci-test-secret-key
  DEBUG: True
  DATABASE_URL: (vide → SQLite)
```

**Base de données** : SQLite (pas de PostgreSQL en CI). `DATABASE_URL` vide → `dj_database_url` fallback automatique.

### test-frontend

```yaml
runs-on: ubuntu-latest
steps:
  - checkout
  - setup-node 20 (cache npm)
  - npm ci
  - npm run lint (eslint)
  - npx vitest run (11 tests)
  - npm run build (vérification build)
```

### build-and-push

```yaml
needs: [test-backend, test-frontend]
if: push sur main ou stg
permissions:
  packages: write

steps:
  - docker/login-action (ghcr.io, GITHUB_TOKEN)
  - docker/build-push-action (backend)
  - docker/build-push-action (frontend)
```

| Image | Tag | Taille | Utilisé par |
|---|---|---|---|
| `ghcr.io/tawounfouet/clickmart-backend:latest` | `latest` | ~668 MB | backend, celery-worker, celery-beat |
| `ghcr.io/tawounfouet/clickmart-frontend:latest` | `latest` | ~26 MB | frontend |

**Cache** : `type=gha` (GitHub Actions cache, 10 GB). `mode=max` exporte toutes les couches.

### deploy-production

```yaml
needs: [build-and-push]
if: push sur main
steps:
  - Deploy to Linode (appleboy/ssh-action)
    script: |
      git pull origin main
      docker compose pull           ← pull depuis ghcr.io
      docker compose up -d          ← recreate si image changée
      docker compose exec nginx nginx -s reload  ← config volume
      curl healthcheck
```

### deploy-staging

```yaml
needs: [build-and-push]
if: push sur stg
steps:
  - Deploy to Linode (appleboy/ssh-action)
    script: |
      git pull origin stg
      docker compose -p clickmart-stg pull
      docker compose -p clickmart-stg up -d
      curl http://localhost:8080 healthcheck
```

---

## Configuration Docker Compose

### Production — images pré-construites

```yaml
# docker-compose.prod.yml
services:
  backend:
    image: ghcr.io/tawounfouet/clickmart-backend:latest
  celery-worker:
    image: ghcr.io/tawounfouet/clickmart-backend:latest  # même image
  celery-beat:
    image: ghcr.io/tawounfouet/clickmart-backend:latest   # même image
  frontend:
    image: ghcr.io/tawounfouet/clickmart-frontend:latest
```

Avantages :
- Build 1× sur GitHub, utilisé 3× (backend + celery ×2)
- Linode fait uniquement `docker pull` (~3s) + `docker up -d` (~5s)
- Zéro build sur le VPS → zéro risque OOM

### Base — builds locaux (dev)

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend      # dev local uniquement
  celery-worker:
    build: ./backend
  frontend:
    build: ./frontend
```

---

## Secrets GitHub

| Secret | Usage |
|---|---|
| `LINODE_HOST` | IP du VPS |
| `LINODE_USER` | `deploy` |
| `LINODE_SSH_KEY` | Clé privée SSH |
| `GITHUB_TOKEN` | Automatique — push vers ghcr.io |

---

## Optimisations

### Dockerfile

```dockerfile
# Ordre optimal : layers stables en premier
RUN apt-get install curl            ← caché (change jamais)
COPY requirements.txt .             ← caché (tant que deps stables)
RUN pip install -r requirements.txt ← caché (~2 min économisées)
COPY . .                            ← rebuild (code change)
```

### Cache GitHub Actions

```yaml
cache-from: type=gha    # restaure les layers du cache
cache-to: type=gha,mode=max  # sauve toutes les couches
```

### Nginx — DNS re-resolution

```nginx
resolver 127.0.0.11 valid=30s;
location /api/ {
    set $backend_upstream backend:8000;
    proxy_pass http://$backend_upstream;  # variable → re-résolution DNS
}
```

Sans variable, Nginx résout `backend` une fois au démarrage. Après recreate du conteneur backend (nouvelle IP), Nginx garde l'ancienne → 502. Avec variable + resolver, re-résolution toutes les 30s.

### Reload nginx après deploy

```bash
docker compose exec nginx nginx -s reload
```

Le fichier `prod.conf` est monté en volume. Quand `git pull` met à jour le fichier, nginx doit être rechargé pour prendre en compte les changements.

---

## Performances

| Métrique | Avant (build local) | Après (build GitHub) |
|---|---|---|
| Temps de déploiement | 3-5 min | ~20s |
| RAM utilisée pendant le déploiement | ~1 000 MB (OOM fréquent) | ~768 MB (stable) |
| Images construites par déploiement | 4 (backend ×3 + frontend) | 0 (pull only) |
| Cache pip install | Non (pas de cache Docker) | Oui (type=gha) |

---

## Commandes utiles

```bash
# Voir les runs récents
gh run list --repo tawounfouet/yt_django-clickmart-devops

# Voir les logs d'un job
gh run view <run_id> --log --job build-and-push

# Voir les packages
gh api /users/tawounfouet/packages/container/clickmart-backend/versions

# Déclencher manuellement
git commit --allow-empty -m "trigger ci" && git push
```
