# Gestion du Workflow CI/CD — ClickMart

> **Date** : 2026-07-30
> **Version** : 3.0
> **Fichier** : `.github/workflows/ci-cd.yml` (renommé depuis `automate.yml`)
> **Debug** : [2026-07-30_CI-CD_bugs.md](../debug/2026-07-30_CI-CD_bugs.md)

---

## Architecture du pipeline (v3)

```
git push main|stg|dev
        │
        ▼
┌──────────────────────────────────────────────────────────────────┐
│                        GitHub Actions                             │
│                                                                    │
│  ┌────────────┐      ┌──────────────┐                             │
│  │backend-lint│      │frontend-lint │  (parallèle)                │
│  │  ruff      │      │  eslint      │                             │
│  └─────┬──────┘      └──────┬───────┘                             │
│        ▼                    ▼                                      │
│  ┌────────────┐      ┌──────────────┐                             │
│  │backend-test│      │frontend-test │  (parallèle)                │
│  │ 67 tests   │      │ 11 tests     │                             │
│  └─────┬──────┘      └──────┬───────┘                             │
│        │                    ▼                                      │
│        │             ┌──────────────┐                              │
│        │             │frontend-build│                              │
│        │             └──────┬───────┘                              │
│        └──────────┬─────────┘                                      │
│                   ▼                                                │
│  ┌──────────────────────────────────┐                             │
│  │        build-and-push            │  (main/stg only)            │
│  │   backend → ghcr.io              │                             │
│  │   frontend → ghcr.io             │                             │
│  └────────────────┬─────────────────┘                             │
│                   ▼                                                │
│  ┌──────────────────────────────────┐                             │
│  │  deploy-production  (main only)  │                             │
│  │  deploy-staging     (stg only)   │                             │
│  │  appleboy/ssh-action             │                             │
│  │  → git reset --hard              │                             │
│  │  → deploy-app.sh                 │                             │
│  └──────────────────────────────────┘                             │
└──────────────────────────────────────────────────────────────────┘
```

| Branche | Lint | Test | Build CI | Build & Push | Déploiement | Provision |
|---|---|---|---|---|---|---|
| `dev` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `stg` | ✅ | ✅ | ✅ | ✅ | ✅ Staging (`:8080`) | ❌ |
| `main` | ✅ | ✅ | ✅ | ✅ | ✅ Production (`:80/443`) | ❌ |
| `workflow_dispatch` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Manuel |

### `provision` (workflow_dispatch, optionnel)

Déclenché manuellement depuis l'UI GitHub Actions → **Run workflow**.

```yaml
inputs:
  target:
    type: choice
    options: [production, staging]
  tags:
    type: string
    default: 'docker'
```

| Input | Description | Exemple |
|---|---|---|
| `target` | Environnement cible | `production` ou `staging` |
| `tags` | Tags Ansible (`docker,app,ssl,cicd`) | `docker` (setup), `docker,app,ssl` (complet) |

**Cas d'usage** :
- VPS vierge → `target: production, tags: docker,app,ssl`
- Ajouter SSL → `target: production, tags: ssl`
- Déployer staging → `target: staging, tags: docker,app`

---

## Jobs détaillés

### `backend-lint` (ruff)

```yaml
runs-on: ubuntu-latest
defaults: { working-directory: backend }
steps:
  - checkout
  - setup-python 3.11 (cache pip)
  - pip install -r requirements.txt + ruff
  - ruff check . --ignore F401,E501,E402,B017,BLE001,I001,RUF012,RUF100,S110
```

**Règles ignorées** : violations préexistantes (131 erreurs), ajoutées progressivement. Dette à purger dans une PR dédiée.

### `backend-test` (Django)

```yaml
needs: backend-lint
runs-on: ubuntu-latest
defaults: { working-directory: backend }
steps:
  - checkout
  - setup-python 3.11 (cache pip)
  - pip install -r requirements.txt
  - python manage.py test --verbosity=2  # 67 tests, SQLite
```

### `frontend-lint` (eslint)

```yaml
runs-on: ubuntu-latest
defaults: { working-directory: frontend }
steps:
  - checkout
  - setup-node 20 (cache npm)
  - npm ci
  - npm run lint
```

### `frontend-test` (vitest)

```yaml
needs: frontend-lint
runs-on: ubuntu-latest
defaults: { working-directory: frontend }
steps:
  - checkout
  - setup-node 20 (cache npm)
  - npm ci
  - npx vitest run --config vite.config.js  # 11 tests
```

### `frontend-build` (vite)

```yaml
needs: frontend-test
runs-on: ubuntu-latest
defaults: { working-directory: frontend }
steps:
  - checkout
  - setup-node 20 (cache npm)
  - npm ci
  - npm run build
env:
  VITE_SERVER_BASE_URL: /api/v1
```

### `build-and-push` (Docker + ghcr.io)

```yaml
needs: [backend-test, frontend-build]
if: push sur main ou stg
permissions: { packages: write }
steps:
  - docker/login-action (ghcr.io, GITHUB_TOKEN)
  - docker/build-push-action (backend, cache type=gha)
  - docker/build-push-action (frontend, cache type=gha)
```

| Image | Tag | Utilisé par |
|---|---|---|
| `ghcr.io/tawounfouet/clickmart-backend:latest` | `latest` | backend, celery-worker, celery-beat |
| `ghcr.io/tawounfouet/clickmart-frontend:latest` | `latest` | frontend |

### `deploy-production` (main)

```yaml
needs: [build-and-push]
if: github.ref == 'refs/heads/main'
steps:
  - appleboy/ssh-action@v1.0.3
    script: |
      cd /opt/clickmart && git reset --hard origin/main
      bash infra/scripts/deploy-app.sh production main <github.actor> <GITHUB_TOKEN>
```

### `deploy-staging` (stg)

```yaml
needs: [build-and-push]
if: github.ref == 'refs/heads/stg'
steps:
  - appleboy/ssh-action@v1.0.3
    script: |
      cd /opt/clickmart-stg && git reset --hard origin/stg
      bash infra/scripts/deploy-app.sh staging stg
```

---

## Script de déploiement externalisé

> Fichier : `infra/scripts/deploy-app.sh`

```
Usage: deploy-app.sh <staging|production> <branch> [gh_user] [gh_token]

Étapes :
  1. cd /opt/clickmart[-stg] && git fetch && git reset --hard
  2. docker login ghcr.io (production uniquement)
  3. docker compose pull + docker compose up -d
  4. nginx reload (production uniquement)
  5. sleep 15 + docker compose ps
  6. Health checks :
     - Frontend : curl http://localhost/ (200|301|302)
     - API      : curl http://localhost/api/v1/products/ (200|301|302)
     - Swap     : swapon --show | grep swapfile (warning, non bloquant)
```

### Avantages vs inline script

| Critère | Avant (inline) | Après (deploy-app.sh) |
|---|---|---|
| Maintenabilité | Duplication staging/prod dans le YAML | Logique unique |
| Testabilité | Impossible en local | `ssh deploy@host "bash infra/scripts/deploy-app.sh ..."` |
| Visibilité | Dissimulé dans le workflow | Fichier versionné, lisible, commenté |
| Health checks | 1 curl basique | 3 checks (frontend + API + swap) avec ✅/❌ |

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

---

## Secrets GitHub

| Secret | Usage |
|---|---|
| `LINODE_HOST` | IP du VPS (172.239.20.14) |
| `LINODE_USER` | `deploy` |
| `LINODE_SSH_KEY` | Clé privée ED25519 (mise à jour 30/07 après reprovisionnement Ansible) |
| `GITHUB_TOKEN` | Automatique — push vers ghcr.io + docker login |

---

## Optimisations

### Dockerfile — ordre des layers

```dockerfile
# Ordre optimal : layers stables en premier
RUN apt-get install curl            ← caché (change jamais)
COPY requirements.txt .             ← caché (tant que deps stables)
RUN pip install -r requirements.txt ← caché (~2 min économisées)
COPY . .                            ← rebuild (code change)
```

### Cache GitHub Actions

```yaml
cache-from: type=gha       # restaure les layers du cache
cache-to: type=gha,mode=max # sauve toutes les couches
```

### Nginx — DNS re-resolution

```nginx
resolver 127.0.0.11 valid=30s;
location /api/ {
    set $backend_upstream backend:8000;
    proxy_pass http://$backend_upstream;  # variable → re-résolution DNS
}
```

### Reload nginx après deploy

```bash
docker compose exec nginx nginx -s reload
```

---

## Évolution du pipeline

| Version | Date | Changements |
|---|---|---|
| 1.0 | 2026-07-28 | Pipeline initial : `test-backend` + `test-frontend` + `build-and-push` + `deploy` |
| 2.0 | 2026-07-29 | Git reset --hard, health checks curl, cache gha, nginx reload |
| 3.0 | 2026-07-30 | **Split lint/test/build** (6 jobs), **deploy-app.sh externalisé**, **health checks enrichis**, lint strict, `working-directory` defaults, `automate.yml` → `ci-cd.yml` |

---

## Performances

| Métrique | v2 (avant) | v3 (après) |
|---|---|---|
| Jobs CI | 2 (test-backend + test-frontend) | 5 (lint×2 + test×2 + build) |
| Parallélisme | backend ↔ frontend | lint↔lint, test↔test, build isolé |
| Feedback lint | Après tests (~60s) | ~15s (avant les tests) |
| Temps de déploiement | ~20s | ~20s (inchangé) |
| Script de déploiement | Inline dans le YAML | Externalisé `deploy-app.sh` |
| Health checks | 1 curl basique | 3 checks structurés (frontend + API + swap) |

---

## Commandes utiles

```bash
# Voir les runs récents
gh run list --workflow ci-cd.yml --limit 5

# Voir le statut de tous les jobs d'un run
gh run view <run_id> --json jobs --jq '.jobs[] | "\(.name): \(.conclusion)"'

# Voir les logs d'un job spécifique
gh run view <run_id> --log --job <job_id>

# Voir les logs avec filtre
gh run view <run_id> --log --job <job_id> | grep -i 'error\|fail'

# Re-run un workflow échoué
gh run rerun <run_id>

# Déclencher manuellement
git commit --allow-empty -m "trigger ci" && git push

# Déployer manuellement depuis le serveur
ssh deploy@172.239.20.14
bash /opt/clickmart/infra/scripts/deploy-app.sh production main <user> <token>
```

---

## Voir aussi

- [Debug CI/CD — 8 bugs documentés](../debug/2026-07-30_CI-CD_bugs.md)
- [Documentation Ansible](../../docs/infra/ansible/)
- [Déploiement Linode](../deploy/DEPLOIEMENT_LINODE.md)
- [Guide CI/CD (historique)](../deploy/GUIDE_CICD.md)
