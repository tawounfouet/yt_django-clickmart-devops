> **⚠️ DOCUMENT HISTORIQUE — État au 28 juillet 2026. Pour l'état actuel, voir DRY_RUN_REPORT.md à la racine du projet.**

# ÉTAT DES LIEUX — ClickMart

> Date : 28 juillet 2026
> Session : déploiement sur Linode (172.239.20.14)
> Documents consolidés : 3 sessions, 7 fichiers d'analyse

---

## 1. Chronologie du projet

```
2025-12-24    v0.1.0 — Backend Django initial (users, products, carts, orders)
2025-12-26    v0.2.0 — Tax, adresses, migrations
2025-12-28    v0.3.0 — Frontend React init (14 pages, auth, cart)
2025-12-30    v0.4.0 — UI polish (Dashboard, checkout)
2026-04-14    v0.5.0 — Docker + docker-compose, JWT config
2026-04-16    v0.6.0 — Tests backend (67+ tests), media fix
2026-07-02    🌟 SESSION 1 — Analyse codebase + 5 docs créés + 4 commits
2026-07-22    🌟 SESSION 2 — Analyse critique + recommandations + plan (3 docs)
2026-07-28    🌟 SESSION 3 — Déploiement Linode + CI/CD GitHub Actions
```

---

## 2. Ce qui est fait

### 2.1 Code applicatif

| Composant | Statut | Détail |
|---|---|---|
| Backend Django 5.2 | ✅ Fonctionnel | 5 apps (users, products, carts, orders, api), JWT auth |
| Frontend React 19 | ✅ Fonctionnel | 14 pages, AuthProvider, CartProvider, 14 routes |
| Tests backend | ✅ 67+ tests | products (15), carts (22), orders (18), users (12) |
| Tests frontend | 🔶 Partiel | Vitest configuré, quelques tests |
| Migrations Django | ✅ À jour | 7 migrations (3 apps) |

### 2.2 Infrastructure

| Composant | Statut | Détail |
|---|---|---|
| Dockerfile backend | ✅ Présent | python:3.10-slim → gunicorn (gitignoré) |
| Dockerfile frontend | ✅ Présent | Node 18 build → nginx:alpine (gitignoré) |
| docker-compose.yml | ✅ Présent | 4 services : db, backend, frontend, nginx (gitignoré) |
| nginx/default.conf | ✅ Présent | Reverse proxy HTTP/HTTPS (git tracké) |
| certbot/ | ✅ Dossiers créés | conf/ + www/ (vides, .gitkeep) |
| .github/workflows/automate.yml | ✅ Pipeline complet | 3 jobs : tests backend (67) + tests frontend + déploiement SSH |

### 2.3 Serveur Linode (172.239.20.14)

| Composant | Statut | Version |
|---|---|---|
| SSH | ✅ Configuré | root@172.239.20.14 |
| Ubuntu | ✅ 24.04.4 | Kernel 6.8.0-111 |
| Docker | ✅ Installé | 29.6.2 |
| Docker Compose | ✅ Installé | v5.3.1 |
| Git | ✅ Installé | 2.43.0 |
| `/opt/clickmart` | ✅ Clone + SCP | Projet complet + fichiers gitignorés |
| UFW Firewall | ⚠️ Inactif | Docker gère iptables |
| Ports firewall cloud | ✅ Configurés | 22, 80, 443 (8000/5173 supprimés) |
| App accessible | ✅ | http://172.239.20.14 |

### 2.4 Documentation existante

| Fichier | Taille | Créé | Commit | Contenu |
|---|---|---|---|---|
| `README.md` | 17 Ko | 2025-12 | ✅ | Tutorial de déploiement pas-à-pas |
| `AGENTS.md` | 2.7 Ko | 2026-07-02 | ✅ | Instructions OpenCode |
| `ANALYSE_CODECOMPLETE.md` | 46 Ko | 2026-07-02 | ✅ | Analyse exhaustive (1047 lignes) |
| `ARCHITECTURE.md` | 13 Ko | 2026-07-02 | ✅ | Diagrammes déploiement, flux, composants |
| `CHANGELOG.md` | 5 Ko | 2026-07-02 | ✅ | Historique versions 0.1.0 → 0.6.0 |
| `INDEX.md` | 6 Ko | 2026-07-02 | ✅ | Plan de navigation du dépôt |
| `ANALYSE_CRITIQUE.md` | 20 Ko | 2026-07-22 | ✅ | Diagnostic 25 problèmes, score 5.4/10 |
| `RECOMMANDATIONS.md` | 30 Ko | 2026-07-22 | ✅ | Plan d'action 6 phases avec code |
| `PLAN_IMPLEMMENTATION.md` | 45 Ko | 2026-07-22 | ✅ | Roadmap 15 jours, dépendances |
| `ETAT_DES_LIEUX.md` | 10 Ko | 2026-07-28 | ✅ | Ce fichier |
| `docs/deploy/DEPLOIEMENT_LINODE.md` | 26 Ko | 2026-07-28 | ✅ | Guide déploiement avec diagrammes ASCII |
| `docs/deploy/GUIDE_CICD.md` | 24 Ko | 2026-07-28 | ❌ | Guide CI/CD pas-à-pas |

### 2.5 Sessions archivées

| Session | Date | Contenu |
|---|---|---|
| `archives/chats/2026-07-02_...` | 2026-07-02 | Analyse codebase + 5 docs + 4 commits |
| `archives/sessions/2026-07-02_...` | 2026-07-02 | Transcript brut de la session 1 (7253 lignes) |
| `archives/chats/2026-07-22_...` | 2026-07-22 | Analyse critique + recommandations + plan |

---

## 3. Ce qui n'est pas fait

### 3.1 Fait aujourd'hui ✅

| Problème | Statut |
|---|---|
| `ALLOWED_HOSTS = []` en dur → dynamique via `config()` | ✅ Résolu |
| `CORS_ALLOWED_ORIGINS` limité à localhost → dynamique | ✅ Résolu |
| Dockerfiles + docker-compose gitignorés → SCP sur serveur | ✅ Résolu |
| Firewall cloud : ports 80/443 ouverts, 8000/5173 supprimés | ✅ Résolu |
| `.env.docker` + `.env.production` créés sur le serveur | ✅ Résolu |
| Déploiement : `docker compose up --build -d` → 4 containers | ✅ Résolu |
| CI/CD : pipeline vide → 3 jobs (tests backend + frontend + deploy) | ✅ Résolu |
| Tests : stubs vides dans git → 67 tests commités | ✅ Résolu |
| Docs non commités → tous commités | ✅ Résolu |

### 3.2 Reste à faire

### 3.2 Sécurité (CRITICAL — PLAN_IMPLEMMENTATION.md Phase 1)

| Problème | Fichier | Statut |
|---|---|---|
| Pas de rate limiting sur les endpoints auth | `settings.py` | ❌ Non implémenté |
| `SECURE_SSL_REDIRECT` non configuré | `settings.py` | ❌ Non implémenté |
| `SECURE_HSTS_SECONDS` non configuré | `settings.py` | ❌ Non implémenté |
| `SESSION_COOKIE_SECURE` non configuré | `settings.py` | ❌ Non implémenté |
| `is_active` exposé dans ProductSerializer | `products/serializers.py` | ❌ Non corrigé |
| Validation mot de passe absente du serializer | `users/serializers.py` | ❌ Non corrigé |
| SSH en root | Serveur Linode | ❌ Pas de user dédié |

### 3.3 Fiabilité (CRITICAL — PLAN_IMPLEMMENTATION.md Phase 2)

| Problème | Fichier | Statut |
|---|---|---|
| Pas de `transaction.atomic()` dans PlaceOrderView | `orders/views.py` | ❌ Non corrigé |
| `Cart.objects.get()` sans try/except | `orders/views.py:19` | ❌ Peut crasher 500 |
| `int(quantity)` sans validation | `carts/views.py:42` | ❌ Peut crasher 500 |
| `fail_silently=False` sur email | `orders/utils.py` | ❌ Crashe toute la commande |
| Imports inutilisés | views.py multiples | ❌ Non nettoyé |
| Pas de contrainte unique (cart, product) | `carts/models.py` | ❌ Non ajouté |

### 3.4 CI/CD

| Problème | Statut |
|---|---|
| Pipeline sans tests (deploy direct sur push) | ❌ Non corrigé |
| Pas de linting dans le pipeline | ❌ |
| Pas de build check frontend | ❌ |
| Pas de health check post-deploy | ❌ |
| Pas de rollback | ❌ |

### 3.5 DevOps

| Problème | Statut |
|---|---|
| Pas de `.dockerignore` | ❌ |
| Pas de healthcheck Docker | ❌ |
| Pas de backup DB | ❌ |
| Pas de cron renouvellement SSL | ❌ |
| Pas de logging structuré | ❌ |

### 3.6 Frontend

| Problème | Statut |
|---|---|
| Pas d'ErrorBoundary | ❌ |
| Pas de lazy loading (toutes les pages importées statiquement) | ❌ |
| Pas de pagination API | ❌ |
| `backend/static/` (163 fichiers) tracké dans git | ❌ |

---

## 4. Dettes documentaires

### 4.1 README.md — Incohérences vs repo réel

| Section README | Description README | Réalité du repo |
|---|---|---|
| Dockerfiles | « Create a new file Dockerfile » | Déjà créés, mais **gitignorés** |
| docker-compose | Version sans nginx, ports 8000+5173 exposés | Version **avec nginx**, ports 80+443 |
| `runserver` en prod | `python manage.py runserver 0.0.0.0:8000` | Déjà migré vers `gunicorn` |
| `VITE_SERVER_BASE_URL` | `http://<IP>:8000/api/v1` | Déjà migré vers `/api/v1` |
| ALLOWED_HOSTS | `os.getenv("ALLOWED_HOSTS", "").split(",")` | Encore `ALLOWED_HOSTS = []` en dur |
| CORS | Montre comment ajouter l'IP | Encore limité à localhost:5173 |
| Gunicorn section | « Replace run command with Gunicorn » | Déjà fait (doublon) |

### 4.2 Fichiers non commités

| Fichier | Créé le | Actions nécessaires |
|---|---|---|
| `ANALYSE_CRITIQUE.md` | 22 juillet | Committer |
| `RECOMMANDATIONS.md` | 22 juillet | Committer |
| `PLAN_IMPLEMMENTATION.md` | 22 juillet | Committer |
| `ÉTAT_DES_LIEUX.md` | 28 juillet | Committer (ce fichier) |

### 4.3 `.gitignore` — Fichiers à revoir

```
# Ces 4 fichiers sont gitignorés mais critiques pour le déploiement :
frontend/Dockerfile     # Ligne 175
backend/.env.docker     # Ligne 176 — OK (secret)
backend/.env.production # Ligne 177 — OK (secret)
backend/.env.development # Ligne 178
backend/Dockerfile      # Ligne 179
docker-compose.yml      # Ligne 180
```

**Décision à prendre** : Garder les Dockerfiles + docker-compose gitignorés (stratégie server-managed) OU les tracker pour que le serveur les reçoive au `git pull`.

---

## 5. Prochaine étape immédiate — Déploiement

### Option A : Déploiement rapide (serveur seul, sans CI/CD)

```bash
# 1. Créer les répertoires sur le serveur
ssh root@172.239.20.14 "mkdir -p /opt/clickmart"

# 2. Copier les fichiers gitignorés manuellement (scp)
scp backend/Dockerfile root@172.239.20.14:/opt/clickmart/backend/
scp frontend/Dockerfile root@172.239.20.14:/opt/clickmart/frontend/
scp docker-compose.yml root@172.239.20.14:/opt/clickmart/

# 3. Cloner le repo
ssh root@172.239.20.14 "cd /opt/clickmart && git clone https://github.com/tawounfouet/yt_django-clickmart-devops.git ."

# 4. Créer les fichiers .env
ssh root@172.239.20.14 "cat > /opt/clickmart/backend/.env.docker << 'EOF'
SECRET_KEY=django-insecure-change-me-now
DEBUG=True
DB_NAME=clickmart
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
ALLOWED_HOSTS=172.239.20.14,localhost,127.0.0.1
EMAIL_HOST_USER=test@test.com
EMAIL_HOST_PASSWORD=test
EOF"

ssh root@172.239.20.14 "cat > /opt/clickmart/backend/.env.production << 'EOF'
POSTGRES_DB=clickmart
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
EOF"

# 5. Ouvrir les ports (interface Linode cloud)
# → Ports 80 et 443 à ouvrir dans le firewall Linode

# 6. Démarrer
ssh root@172.239.20.14 "cd /opt/clickmart && docker compose up --build -d"
```

### Option B : D'abord corriger les critiques + CI/CD

Suivre `PLAN_IMPLEMMENTATION.md` :
1. Phase 1 (J1-2) : Sécurité — rate limiting, headers SSL, ALLOWED_HOSTS
2. Phase 2 (J3-5) : Fiabilité — transactions, validation
3. Phase 3 (J6-8) : CI/CD — pipeline avec tests
4. Puis déployer

---

## 6. Matrice récapitulative

| Domaine | Fait | Restant | Bloquant |
|---|---|---|---|
| **Code backend** | ✅ | 🔶 5 bugs critiques | OUI (transactions) |
| **Code frontend** | ✅ | 🔶 ErrorBoundary, lazy loading | NON |
| **Tests** | ✅ 67+ commités | 🔶 CI frontend (vitest config) | NON |
| **Docker** | ✅ Déployé | 🔴 Gitignorés (SCP manuel) | NON |
| **Serveur** | ✅ App en ligne | 🔴 User SSH dédié | NON |
| **CI/CD** | ✅ Pipeline complet | 🔶 Frontend test non bloquant | NON |
| **Sécurité** | 🔶 ALLOWED_HOSTS OK | 🔴 Rate limiting, headers | OUI |
| **Documentation** | ✅ 8 fichiers | 🔶 GUIDE_CICD à committer | NON |
| **SSL/Domaine** | 🔶 Certbot dossier prêt | ❌ Pas de domaine | NON |

---

*Ce document est un état des lieux vivant — à mettre à jour après chaque session.*
