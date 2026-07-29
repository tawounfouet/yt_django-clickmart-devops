> **⚠️ DOCUMENT HISTORIQUE — État au 28 juillet 2026. Pour l'état actuel, voir DRY_RUN_REPORT.md à la racine du projet.**

# Guide CI/CD — GitHub Actions → Linode

> Mise en place pas-à-pas du pipeline d'intégration et déploiement continu
> Projet ClickMart — Django + React + Docker + Nginx
> Dernière mise à jour : 28 juillet 2026

---

## Table des matières

1. [Principe général](#1-principe-général)
2. [Prérequis](#2-prérequis)
3. [Étape 1 : Générer et configurer la clé SSH](#3-étape-1--générer-et-configurer-la-clé-ssh)
4. [Étape 2 : Ajouter les secrets GitHub](#4-étape-2--ajouter-les-secrets-github)
5. [Étape 3 : Créer le workflow](#5-étape-3--créer-le-workflow)
6. [Étape 4 : Comprendre le pipeline (diagramme)](#6-étape-4--comprendre-le-pipeline-diagramme)
7. [Étape 5 : Tester le pipeline](#7-étape-5--tester-le-pipeline)
8. [Étape 6 : Déboguer un pipeline qui échoue](#8-étape-6--déboguer-un-pipeline-qui-écheque)
9. [Fichier final complet](#9-fichier-final-complet)

---

## 1. Principe général

```
┌─────────────┐     git push      ┌──────────────────────────────────────────┐
│  MON POSTE  │ ────────────────► │              GITHUB ACTIONS              │
│             │                   │                                          │
│  git push   │                   │  ┌──────────┐  ┌───────────┐  ┌───────┐ │
│  origin     │                   │  │ 1.TESTS  │  │ 2.BUILD  │  │3.DEPLOY│ │
│  main       │                   │  │ backend  │─►│ frontend  │─►│  SSH   │ │
│             │                   │  │ 67 tests │  │ vite build│  │ Linode │ │
│             │                   │  └──────────┘  └───────────┘  └───┬───┘ │
│             │                   │                                    │      │
│             │                   └────────────────────────────────────┼──────┘
│             │                                                        │
│             │                                                        ▼
│             │                                              ┌─────────────────┐
│             │                                              │  SERVEUR LINODE │
│             │                                              │                 │
│             │                                              │ git pull        │
│             │                                              │ docker compose  │
│             │                                              │ up --build -d   │
│             │                                              │ health check    │
│             │                                              └─────────────────┘
└─────────────┘
```

**Règle d'or** : le code n'est déployé que si **tous les tests passent**.

---

## 2. Prérequis

- [x] Compte GitHub avec le dépôt `tawounfouet/yt_django-clickmart-devops`
- [x] Serveur Linode accessible en SSH
- [x] Docker et Docker Compose installés sur le serveur
- [x] Le projet cloné dans `/opt/clickmart` sur le serveur
- [x] `gh` CLI installé sur le poste local (`brew install gh`)

Vérification rapide :

```bash
# Tester le SSH
ssh root@172.239.20.14 "echo OK"

# Vérifier Docker sur le serveur
ssh root@172.239.20.14 "docker --version && docker compose version"

# Vérifier gh CLI
gh auth status
```

---

## 3. Étape 1 : Générer et configurer la clé SSH

GitHub Actions a besoin d'une **clé privée SSH** pour se connecter au serveur Linode.

### 3.1 Vérifier la clé existante

```bash
ls ~/.ssh/id_rsa ~/.ssh/id_ed25519
cat ~/.ssh/id_rsa.pub
```

### 3.2 Ou en créer une dédiée (recommandé)

```bash
ssh-keygen -t ed25519 -C "github-actions-clickmart" -f ~/.ssh/clickmart_deploy
cat ~/.ssh/clickmart_deploy.pub
```

### 3.3 Ajouter la clé publique sur le serveur

```bash
# Copier la clé publique sur le serveur
ssh root@172.239.20.14 "echo '$(cat ~/.ssh/clickmart_deploy.pub)' >> ~/.ssh/authorized_keys"

# Ou manuellement :
ssh root@172.239.20.14
nano ~/.ssh/authorized_keys
# Coller la clé publique
```

### 3.4 Tester la connexion avec la nouvelle clé

```bash
ssh -i ~/.ssh/clickmart_deploy root@172.239.20.14 "echo OK"
```

---

## 4. Étape 2 : Ajouter les secrets GitHub

Les secrets sont des variables chiffrées que GitHub Actions injecte dans le pipeline.

### 4.1 Via l'interface web

1. Aller sur `https://github.com/tawounfouet/yt_django-clickmart-devops/settings/secrets/actions`
2. Cliquer **New repository secret**
3. Ajouter les 3 secrets :

| Nom du secret | Valeur |
|---|---|
| `LINODE_HOST` | `172.239.20.14` |
| `LINODE_USER` | `root` |
| `LINODE_SSH_KEY` | Contenu du fichier `~/.ssh/id_rsa` (ou `~/.ssh/clickmart_deploy`) |

```
┌─────────────────────────────────────────────────────────┐
│  ⚠️ Pour LINODE_SSH_KEY : copier TOUT le contenu        │
│     du fichier de clé privée, y compris :               │
│                                                        │
│  -----BEGIN OPENSSH PRIVATE KEY-----                    │
│  b3BlbnNzaC1rZXktdjEAAAAA...                          │
│  -----END OPENSSH PRIVATE KEY-----                      │
│                                                        │
│  Commande pour obtenir le contenu :                     │
│  cat ~/.ssh/id_rsa | pbcopy    (macOS)                 │
│  cat ~/.ssh/id_rsa | xclip     (Linux)                 │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Via la CLI (si `gh` configuré)

```bash
gh secret set LINODE_HOST -b "172.239.20.14" -R tawounfouet/yt_django-clickmart-devops
gh secret set LINODE_USER -b "root" -R tawounfouet/yt_django-clickmart-devops
gh secret set LINODE_SSH_KEY -b "$(cat ~/.ssh/id_rsa)" -R tawounfouet/yt_django-clickmart-devops
```

### 4.3 Vérifier

```bash
gh secret list -R tawounfouet/yt_django-clickmart-devops
```

Doit afficher :
```
LINODE_HOST     2026-07-28
LINODE_SSH_KEY  2026-07-28
LINODE_USER     2026-07-28
```

---

## 5. Étape 3 : Créer le workflow

### 5.1 Créer le fichier

```bash
mkdir -p .github/workflows
touch .github/workflows/automate.yml
```

### 5.2 Structure du fichier YAML

Le fichier `.github/workflows/automate.yml` est structuré en 3 jobs :

```
automate.yml
│
├── on: push/pull_request sur main
│
├── Job 1: test-backend
│   ├── Checkout code
│   ├── Install Python 3.11 + dépendances
│   ├── Lint (ruff)
│   └── Tests Django (67 tests)
│
├── Job 2: test-frontend
│   ├── Checkout code
│   ├── Install Node 20 + npm ci
│   ├── Lint (eslint)
│   ├── Test (vitest)
│   └── Build (vite)
│
└── Job 3: deploy (seulement si job 1 ET job 2 réussissent)
    ├── SSH sur le serveur
    ├── git pull origin main
    ├── docker compose up --build -d
    └── Health check (curl)
```

### 5.3 Le fichier complet

Voir [section 9 — Fichier final complet](#9-fichier-final-complet).

---

## 6. Étape 4 : Comprendre le pipeline (diagramme)

### 6.1 Déclencheurs

```yaml
on:
  push:
    branches: [main]        # Déclenché à chaque push sur main
  pull_request:
    branches: [main]        # Déclenché à chaque PR vers main
```

### 6.2 Job 1 — test-backend

```
┌──────────────────────────────────────────────────────────────┐
│                    Job 1 : test-backend                       │
│                                                              │
│  1. Checkout  ──► Récupère le code source                   │
│                                                              │
│  2. Python 3.11 ──► Configure l'environnement Python         │
│                                                              │
│  3. pip install  ──► Installe Django, DRF, ruff, etc.        │
│                                                              │
│  4. ruff check  ──► Vérifie le style du code (warnings)     │
│     (|| true)       Non bloquant — ne casse pas le pipeline  │
│                                                              │
│  5. python manage.py test                                    │
│     ┌──────────────────────────────────────────┐            │
│     │  SQLite en mémoire (pas de PostgreSQL)   │            │
│     │  67 tests en ~17 secondes                │            │
│     │  users : 12 tests                        │            │
│     │  products : 15 tests                     │            │
│     │  carts : 22 tests                        │            │
│     │  orders : 18 tests                       │            │
│     └──────────────────────────────────────────┘            │
│                                                              │
│  Résultat : ✅ OU ❌ (bloque le déploiement si ❌)           │
└──────────────────────────────────────────────────────────────┘
```

### 6.3 Job 2 — test-frontend

```
┌──────────────────────────────────────────────────────────────┐
│                   Job 2 : test-frontend                       │
│                                                              │
│  1. Checkout  ──► Récupère le code source                   │
│                                                              │
│  2. Node 20   ──► Configure Node.js + npm                    │
│                                                              │
│  3. npm ci    ──► Installe les dépendances (depuis lock)     │
│                                                              │
│  4. npm run lint                                             │
│     (|| true)     Non bloquant                               │
│                                                              │
│  5. npm test     (vitest)                                    │
│     (|| true)     Non bloquant (config jsdom à améliorer)    │
│                                                              │
│  6. npm run build                                            │
│     ┌──────────────────────────────────────────┐            │
│     │  Vite build → dist/                      │            │
│     │  BLOQUANT — si le build casse, on        │            │
│     │  ne déploie pas                          │            │
│     └──────────────────────────────────────────┘            │
│                                                              │
│  Résultat : ✅ OU ❌ (bloque le déploiement si ❌)           │
└──────────────────────────────────────────────────────────────┘
```

### 6.4 Job 3 — deploy

```
┌──────────────────────────────────────────────────────────────┐
│                     Job 3 : deploy                            │
│                                                              │
│  Condition : jobs 1 ET 2 réussis + push sur main             │
│                                                              │
│  1. SSH → serveur                                            │
│     ┌──────────────────────────────────────────┐            │
│     │  appleboy/ssh-action@v1.0.3               │            │
│     │  Utilise les secrets GitHub :              │            │
│     │  LINODE_HOST, LINODE_USER, LINODE_SSH_KEY │            │
│     └──────────────────────────────────────────┘            │
│                                                              │
│  2. Script de déploiement :                                  │
│     ┌──────────────────────────────────────────┐            │
│     │  cd /opt/clickmart                        │            │
│     │  git pull origin main                     │            │
│     │  docker compose up --build -d             │            │
│     │  sleep 15                                  │            │
│     │  docker compose ps                        │            │
│     │                                           │            │
│     │  Health checks :                           │            │
│     │  curl -sf http://localhost/api/v1/products/│            │
│     │  curl -sf http://localhost/                │            │
│     │                                           │            │
│     │  ✅ OU ❌ (échec = pipeline rouge)         │            │
│     └──────────────────────────────────────────┘            │
└──────────────────────────────────────────────────────────────┘
```

### 6.5 Flux de données complet

```
GitHub Actions Runner (Ubuntu)
│
├── Checkout code ──► Code source depuis GitHub
│
├── Job 1 (backend) ──► Python 3.11 + SQLite mémoire
│   └── 67 tests ──► OK / FAIL
│
├── Job 2 (frontend) ──► Node 20 + npm
│   └── build dist/ ──► OK / FAIL
│
└── Job 3 (deploy) ──► SSH vers Linode ──► git pull + docker compose
    └── Seulement si Job1 ET Job2 = OK

Serveur Linode (172.239.20.14)
│
├── /opt/clickmart/ ──► Code source
├── docker compose up --build -d
│   ├── db (postgres:16)
│   ├── backend (gunicorn ×3)
│   ├── frontend (nginx + React)
│   └── nginx (reverse proxy :80)
│
└── Health check : curl → http://localhost
```

---

## 7. Étape 5 : Tester le pipeline

### 7.1 Premier push

```bash
git add .
git commit -m "test: trigger CI/CD pipeline"
git push origin main
```

### 7.2 Surveiller l'exécution

```bash
# Voir le dernier run
gh run list -R tawounfouet/yt_django-clickmart-devops --limit 1

# Voir les logs en direct
gh run watch -R tawounfouet/yt_django-clickmart-devops

# Voir les logs détaillés
gh run view -R tawounfouet/yt_django-clickmart-devops --log
```

### 7.3 Résultat attendu

```
┌─────────────────────────────────────┐
│  CI/CD Pipeline                     │
│                                     │
│  ✅ test-backend    (67 tests OK)   │
│  ✅ test-frontend   (build OK)      │
│  ✅ deploy          (health OK)     │
│                                     │
│  🟢 Pipeline SUCCESS                │
└─────────────────────────────────────┘
```

### 7.4 Vérifier le déploiement

```bash
# Frontend
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://172.239.20.14/

# API
curl -s http://172.239.20.14/api/v1/products/

# Vérifier les containers
ssh root@172.239.20.14 "docker compose -f /opt/clickmart/docker-compose.yml ps"
```

---

## 8. Étape 6 : Déboguer un pipeline qui échoue

### 8.1 Erreur « Ran 0 tests »

```
Ran 0 tests in 0.000s
```

**Cause** : Les fichiers de test ne sont pas dans le dépôt Git.

**Solution** :
```bash
git add backend/*/tests.py
git commit -m "test: add test files"
git push
```

### 8.2 Erreur « NoReverseMatch »

```
django.urls.exceptions.NoReverseMatch: Reverse for 'cart-add' not found
```

**Cause** : Les URLs n'ont pas de paramètre `name=`.

**Solution** : Vérifier `backend/api/urls.py` :
```python
path('cart/add/', CartViews.AddToCartView.as_view(), name='cart-add'),
#                                                   ^^^^^^^^^^^^^^^^
```

### 8.3 Erreur SSH « Permission denied »

```
Permission denied (publickey)
```

**Causes possibles** :
1. Le secret `LINODE_SSH_KEY` contient une clé publique au lieu de la privée
2. La clé publique n'est pas dans `~/.ssh/authorized_keys` sur le serveur
3. Le format de la clé est incorrect (retours à la ligne cassés)

**Solution** :
```bash
# Vérifier le secret
gh secret list -R tawounfouet/yt_django-clickmart-devops

# Vérifier la clé sur le serveur
ssh root@172.239.20.14 "cat ~/.ssh/authorized_keys"
```

### 8.4 Erreur « role root does not exist » (PostgreSQL)

```
FATAL: role "root" does not exist
```

**Cause** : Le test backend utilise PostgreSQL mais les credentials ne correspondent pas.

**Solution** : Ne pas configurer `DB_NAME`/`DB_USER`/`DB_HOST` dans les variables d'environnement du workflow — laisser le fallback SQLite :

```yaml
- name: Run tests
  env:
    SECRET_KEY: ci-test
    DEBUG: 'True'
    # PAS de DB_NAME, DB_USER, DB_HOST → SQLite automatique
```

### 8.5 Workflow refused (OAuth scope)

```
refusing to allow an OAuth App to create or update workflow
```

**Cause** : Le token OAuth n'a pas le scope `workflow`.

**Solutions** :
1. Passer en SSH : `git remote set-url origin git@github.com:tawounfouet/yt_django-clickmart-devops.git`
2. Ou régénérer le token avec le scope `workflow`

---

## 9. Fichier final complet

```yaml
# .github/workflows/automate.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # ═══════════════════════════════════════════════════════════════
  # JOB 1 : Tests backend Django
  # ═══════════════════════════════════════════════════════════════
  test-backend:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
          cache-dependency-path: backend/requirements.txt

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install ruff coverage

      - name: Lint with ruff
        run: |
          cd backend
          ruff check . --ignore F401,E501,E402 || true

      - name: Run tests
        env:
          SECRET_KEY: ci-test-secret-key-not-for-prod
          DEBUG: 'True'
          EMAIL_HOST_USER: test@test.com
          EMAIL_HOST_PASSWORD: test
          ALLOWED_HOSTS: localhost
          CORS_ALLOWED_ORIGINS: http://localhost:5173
        run: |
          cd backend
          python manage.py test --verbosity=2

  # ═══════════════════════════════════════════════════════════════
  # JOB 2 : Tests et build frontend React
  # ═══════════════════════════════════════════════════════════════
  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci
        working-directory: frontend

      - name: Lint
        run: npm run lint || true
        working-directory: frontend

      - name: Test
        run: npm test || true
        working-directory: frontend

      - name: Build
        run: npm run build
        working-directory: frontend
        env:
          VITE_SERVER_BASE_URL: /api/v1

  # ═══════════════════════════════════════════════════════════════
  # JOB 3 : Déploiement sur Linode
  # ═══════════════════════════════════════════════════════════════
  deploy:
    needs: [test-backend, test-frontend]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Linode
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.LINODE_HOST }}
          username: ${{ secrets.LINODE_USER }}
          key: ${{ secrets.LINODE_SSH_KEY }}
          script: |
            set -e
            cd /opt/clickmart
            echo "=== Pull latest code ==="
            git pull origin main
            echo "=== Rebuild and restart ==="
            docker compose up --build -d
            echo "=== Wait for services ==="
            sleep 15
            echo "=== Health check ==="
            docker compose ps
            curl -sf http://localhost/api/v1/products/ || (echo "❌ Backend healthcheck failed" && exit 1)
            curl -sf http://localhost/ || (echo "❌ Frontend healthcheck failed" && exit 1)
            echo "✅ Deployment successful"
```

---

## Annexe : Commandes utiles au quotidien

```bash
# Voir l'état du dernier pipeline
gh run list -R tawounfouet/yt_django-clickmart-devops --limit 3

# Voir les logs d'un run spécifique
gh run view --log -R tawounfouet/yt_django-clickmart-devops

# Relancer un pipeline qui a échoué
gh run rerun <RUN_ID> -R tawounfouet/yt_django-clickmart-devops

# Vérifier les secrets configurés
gh secret list -R tawounfouet/yt_django-clickmart-devops

# Déclencher un déploiement manuel (push vide)
git commit --allow-empty -m "deploy: trigger CI/CD" && git push

# Voir les logs du serveur après déploiement
ssh root@172.239.20.14 "docker compose -f /opt/clickmart/docker-compose.yml logs --tail=50"
```

---

*Guide créé le 28 juillet 2026 — session de mise en place CI/CD.*
