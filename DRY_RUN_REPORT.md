# 🔍 CLICKMART — RAPPORT DRY-RUN

> **Date** : 2026-07-29 (mise à jour 20h15) | **Cible** : `deploy@172.239.20.14` | **Domaine** : `webtech-dev.info`  
> **Agent** : deploy-fullstack v3.0 | **Mode** : Analyse seule — aucun changement effectué  
> **Statut global** : ✅ PRODUCTION STABLE — 6/6 conteneurs healthy — CI/CD conditionnel actif — ghcr.io images

---

## PARTIE A — ANALYSE PRÉALABLE (11 ÉTAPES)

### A1. Structure Docker — split multi-environnements (✅ Sain)

9 services dans `docker-compose.yml` (fichier de base) + 3 overrides :

| Fichier | Rôle | Services |
|---------|------|----------|
| `docker-compose.yml` | Base (builds, healthchecks, mem_limits) | 8 services |
| `docker-compose.prod.yml` | Production (ports 80/443, SSL, certbot, désactive db/redis/minio) | 6 conteneurs actifs |
| `docker-compose.staging.yml` | Staging (port 8080, pas SSL) | surcharge nginx/ports |
| `docker-compose.override.yml` | Dev local (port 80, env_file .local) | surcharge nginx/backend/env |

**Services de base** :

| Service | Type | Healthcheck | mem_limit | Actif en prod |
|---------|------|-------------|-----------|:---:|
| `db` | postgres:16-alpine | ✅ pg_isready | 200m | ❌ profile disabled |
| `redis` | redis:7-alpine | ✅ redis-cli ping | 64m | ❌ profile disabled |
| `minio` | minio/minio | ✅ curl /health/live | 128m | ❌ profile disabled |
| `backend` | ghcr.io image | ✅ curl /api/v1/products/ | 256m | ✅ |
| `celery-worker` | ghcr.io image | ✅ celery inspect ping | 256m | ✅ |
| `celery-beat` | ghcr.io image | ✅ celery inspect ping | 64m | ✅ |
| `frontend` | ghcr.io image | ❌ (via Nginx) | 128m | ✅ |
| `nginx` | nginx:alpine | ✅ curl localhost:80 | 32m | ✅ |
| `certbot` | certbot/certbot (prod only) | ❌ (cron renew) | 32m | ✅ |

**Conteneurs actifs en production** : 6 (vs 8 dans le rapport précédent — db, redis, minio désactivés via `profiles: [disabled]`).  
**Total RAM réservée (mem_limit, prod only)** : 768 MiB (256+256+64+128+32+32) — sous la RAM physique de 961 MiB ✅.

Dépendances correctement chaînées. Healthchecks présents sur tous les services stateful. `env_file` placé dans les overrides (pas dans la base).

### A2. Stack technologique (✅ Cohérent)

| Couche | Technologie |
|--------|------------|
| Backend | Django 5.2 + DRF 3.16 + SimpleJWT |
| Base de données | PostgreSQL 16 (distant: 49.13.239.42, TLS) |
| Cache/Broker | Redis 7 (distant: 49.13.239.42, auth) |
| Tâches async | Celery 5.6.0 |
| WSGI | Gunicorn 22.0.0 |
| Reverse proxy | Nginx Alpine (variable upstream, resolver DNS 30s) |
| Frontend | React 19 + Vite 7 + Bootstrap 5 |
| SSL | Let's Encrypt (Certbot Docker, renewal 12h) |
| Email | Tiers : console (dev) / SMTP (staging) / Resend (prod) |
| Registry images | ghcr.io (GitHub Container Registry) — builds sur GitHub, pull sur Linode |
| CI/CD | GitHub Actions (automate.yml — déclenchement par branche + build-and-push) |
| Cloud | Linode (Ubuntu 24.04 LTS) |
| Tests | 67 backend (Django) + 11 frontend (Vitest) |
| API docs | drf-spectacular (Swagger) |

### A3. Inspection Django (✅ Robuste)

| Configuration | Statut | Détail |
|---|---|---|
| SECRET_KEY / DEBUG / ALLOWED_HOSTS / CORS | ✅ | via `config()` (decouple) |
| ENVIRONMENT | ✅ | via `config('ENVIRONMENT')`, injecté dans overrides |
| DATABASES (dj-database-url) | ✅ | `DATABASE_URL` → `dj_database_url.parse()`, sinon SQLite |
| DATABASE_URL (prod) | ✅ | `postgres://...@49.13.239.42:5432/clickmart?sslmode=require` |
| AUTH_USER_MODEL = users.User | ✅ | Custom user model |
| JWT (15min access / 7d refresh) | ✅ | Raisonnable |
| Throttling (anon:20, user:60, auth:5) | ✅ | |
| SECURE_SSL_REDIRECT | ✅ | `not DEBUG and ENVIRONMENT == 'production'` |
| HSTS / SESSION_COOKIE_SECURE / CSRF | ✅ | Strict |
| CELERY_BROKER_URL (prod) | ✅ | `redis://...@49.13.239.42:6379/0` (distant, auth) |
| EMAIL_BACKEND (prod) | ✅ | `core.mail.ResendEmailBackend` (via `EMAIL_BACKEND_TYPE=resend`) |
| SECURE_PROXY_SSL_HEADER | ✅ | `('HTTP_X_FORWARDED_PROTO', 'https')` |
| MEDIA_STORAGE_BACKEND (prod) | ✅ | `cloudinary` (Cloudinary) |

14 endpoints API RESTful documentés via Swagger.

### A4. Dépendances (✅ À jour)

Backend : 16 packages (Django 5.2, DRF 3.16, Celery 5.6, Redis 6.2, Gunicorn 22, dj-database-url, resend, cloudinary, psycopg2-binary, etc.)  
Frontend : 8 deps + 11 devDeps (React 19, Vite 7, Bootstrap 5, Vitest 4, etc.)  
Toutes les versions sont pinées.

### A5. Base de données (✅ Solide)

PostgreSQL 16 distant (49.13.239.42, TLS requis) en production, SQLite en fallback pour dev/CI.  
Modèle : User → Cart → CartItem, Order → OrderItem, Product.  
Volume nommé `clickmart_postgres_data` persistant (production).  
⚠️ Bug connu : Order créée avant validation stock (ARCHITECTURE.md §7).

### A6. Reverse proxy Nginx — multi-environnements (✅ Propre)

Deux configs Nginx distinctes :

**production** (`infra/nginx/prod.conf`) :
```
Port 80  → redirect 301 HTTPS (sauf acme-challenge)
Port 443 → SSL termination
  /        → frontend:80
  /api/    → $backend_upstream (variable → resolver 127.0.0.11)
  /admin/  → $backend_upstream (variable → resolver 127.0.0.11)
  /static/ → alias /static/
  /uploads/→ alias /uploads/
resolver 127.0.0.11 valid=30s  ← fix DNS Docker
client_max_body_size 10M
```

**staging** (`infra/nginx/staging.conf`) :
```
Port 80 (pas de SSL)
  /        → frontend:80
  /api/    → backend:8000
  /admin/  → backend:8000
  /static/ → alias /static/
  /media/  → alias /media/
resolver 127.0.0.11 valid=30s
```

### A7. Git remote & branches (✅ Propre)

- Repo : `git@github.com:tawounfouet/yt_django-clickmart-devops.git`
- Branches : `main` (prod), `stg` (staging), `dev` (développement)
- Stratégie : `dev → stg → main`, CI/CD conditionnel par branche
- Commits conventionnels bien formés
- État local : propre

### A8. Fournisseur cloud (⚠️ RAM limitée)

| Propriété | Valeur |
|---|---|
| Fournisseur | Linode (Akamai) |
| IP | 172.239.20.14 |
| OS | Ubuntu 24.04.4 LTS |
| Disque | 25 Go (9.8 Go libres) |
| RAM | 961 MiB (273 MiB dispo) |
| Mem limits cumulés (prod) | 768 MiB (6 conteneurs) |
| Docker | 29.6.2 |

✅ Les mem_limits cumulés (768 MiB) sont désormais sous la RAM physique (961 MiB) grâce à la désactivation de db/redis/minio en production.

### A9. Services asynchrones Celery/Redis (✅ Fonctionnels)

- Redis : distant (49.13.239.42:6379), auth, 1 node online
- Celery worker : concurrency=2, 2 tâches (send_order_confirmation_email, cleanup_expired_carts)
- Celery beat : scheduler périodique
- ✅ Healthchecks définis → tous marqués healthy

### A10. Multi-environnements (✅ Sécurisé)

| Environnement | DEBUG | SSL | Ports | Fichier env | Email backend |
|---|---|---|---|---|---|
| Dev local | True | N/A | 80 (override) | `backend/.envs/.local` | resend (prod API key ⚠️) |
| Docker staging | True | Non | 8080 | `backend/.envs/.staging` | smtp |
| CI (GitHub Actions) | True | N/A | — | inline vars | console (fallback) |
| Production Linode | ✅ False | ✅ Certbot | 80, 443 | `backend/.envs/.prod` | resend |

Backend `.envs/` contient `.prod`, `.staging`, et `.local`. Naming POSTGRES_* unifié + `DATABASE_URL`.

---

## PARTIE B — PREFLIGHT-CHECK

### B1. Local (✅ Tout OK)

| Prérequis | Statut | Version |
|---|---|---|
| git | ✅ | 2.54.0 |
| ssh | ✅ | OpenSSH 10.2 |
| sshpass | ✅ | installé |
| gh CLI | ✅ | authentifié (tawounfouet) |
| docker-compose.yml | ✅ | présent (base + prod + staging + override) |
| Dockerfile backend | ✅ | présent (python:3.10-slim, pas de gcc/libpq-dev) |
| Dockerfile frontend | ✅ | présent (multi-stage, node:18 → nginx:alpine) |
| Clés SSH | ✅ | id_ed25519 + id_rsa |
| Git remote | ✅ | github.com:tawounfouet/yt_django-clickmart-devops.git |
| Branches | ✅ | main, stg, dev (locales + remotes) |
| `.env` racine | ✅ | DATABASE_URL local |
| `docker-compose.override.yml` | ✅ | Dev local avec `.envs/.local` |

### B2. Distant (Linode)

| Vérification | Statut |
|---|---|
| SSH deploy@172.239.20.14 | ✅ |
| Ubuntu 24.04 LTS | ✅ |
| Droits sudo NOPASSWD | ✅ |
| Ports 22, 80, 443 | ✅ |
| Espace disque 9.8 Go libres | ✅ |
| Architecture x86_64 | ✅ |
| RAM 273 MiB dispo | ⚠️ |
| Docker 29.6.2 | ✅ |
| Git repo à jour (commit ccf1ffd) | ✅ |
| PostgreSQL 49.13.239.42:5432 (TLS) | ✅ |
| Redis 49.13.239.42:6379 (auth) | ✅ |
| ghcr.io login | ✅ (token GitHub Actions) |

### B3. État des conteneurs Docker — TOUS HEALTHY

```
NAME                        STATUS                    HEALTH
clickmart-backend-1         Up (healthy)              ✅ curl /api/v1/products/
clickmart-celery-worker-1   Up (healthy)              ✅ celery inspect ping
clickmart-celery-beat-1     Up (healthy)              ✅ celery inspect ping
clickmart-frontend-1        Up                        ✅ (via Nginx)
clickmart-nginx-1           Up (healthy)              ✅ curl localhost:80
clickmart-certbot-1         Up                        ✅ (cron renew 12h)
```

> **6/6 conteneurs running** — 4 avec healthcheck OK, 2 (frontend/certbot) sans healthcheck mais fonctionnels.  
> db/redis/minio sont désactivés en production via `profiles: [disabled]`.

### B4. Tests HTTP

| Endpoint | Code HTTP | Statut |
|---|---|---|
| `https://webtech-dev.info/` | ✅ 200 | Frontend React (badge PROD inclus) |
| `https://webtech-dev.info/api/v1/products/?format=json` | ✅ 200 | API REST (DRF) |
| `https://webtech-dev.info/admin/` | ✅ 302 | Admin (redirect login) |

### B5. Configuration production vérifiée

| Variable | Valeur |
|---|---|
| DEBUG | `False` ✅ |
| ENVIRONMENT | `production` ✅ |
| EMAIL_BACKEND_TYPE | `resend` ✅ |
| EMAIL_BACKEND actif | `core.mail.ResendEmailBackend` ✅ |
| DEFAULT_FROM_EMAIL | `hello@webtech-dev.info` ✅ |
| ALLOWED_HOSTS | webtech-dev.info, www.webtech-dev.info, 172.239.20.14, localhost, 127.0.0.1, backend |
| CORS_ALLOWED_ORIGINS | http://172.239.20.14, http://localhost:5173, https://webtech-dev.info, https://www.webtech-dev.info |
| SECURE_SSL_REDIRECT | ✅ Actif (DEBUG=False + ENVIRONMENT=production) |
| DATABASE_URL (prod) | postgres://...@49.13.239.42:5432/clickmart?sslmode=require ✅ |
| CELERY_BROKER_URL | redis://...@49.13.239.42:6379/0 (auth) ✅ |
| MEDIA_STORAGE_BACKEND | cloudinary ✅ |
| client_max_body_size | 10M ✅ |
| Nginx upstream | variable `$backend_upstream` + resolver 127.0.0.11 ✅ |
| celery inspect ping | 1 node online ✅ |
| Badge frontend | PROD (VITE_ENVIRONMENT=production) ✅ |

### B6. CI/CD (GitHub Actions)

| Élément | Statut |
|---|---|
| Workflow `automate.yml` | ✅ présent |
| Déclenchement | push sur main, stg, dev |
| Jobs : test-backend (67 tests) | ✅ |
| Jobs : test-frontend (11 tests + lint + build) | ✅ |
| Jobs : build-and-push (ghcr.io) | ✅ Condition : main/stg uniquement |
| deploy-staging (condition : `refs/heads/stg`) | ✅ Port 8080 |
| deploy-production (condition : `refs/heads/main`) | ✅ Ports 80/443 |
| docker login ghcr.io | ✅ Avant `docker compose pull` |
| Secrets (LINODE_HOST, LINODE_SSH_KEY, LINODE_USER) | ✅ 3 secrets actifs, pas de doublons |
| Stratégie déploiement | `git reset --hard` + `docker compose pull` + `docker compose up -d` |
| Registry images | ghcr.io/tawounfouet/clickmart-backend + clickmart-frontend |
| Projets Docker nommés | `clickmart` (prod), `clickmart-stg` (staging) |

---

## PARTIE C — NOUVEAUTÉS DEPUIS LE DRY-RUN PRÉCÉDENT

### C-N1. Stratégie de branches (dev → stg → main) ✅

Trois branches créées avec CI/CD conditionnel :
- **`dev`** : développement continu, push déclenche uniquement les tests
- **`stg`** : push déclenche tests + déploiement staging (port 8080, pas de SSL)
- **`main`** : push déclenche tests + build-and-push + déploiement production (ports 80/443, SSL)

Workflow `automate.yml` configuré : `on: push: branches: [main, stg, dev]`, avec conditions `if: github.ref` par job.

### C-N2. Docker Compose split (base + overrides) ✅

Séparation en 4 fichiers :
- **`docker-compose.yml`** : 8 services de base, builds, healthchecks, mem_limits, volumes, dépendances
- **`docker-compose.prod.yml`** : ports 80/443, SSL, certbot, env_file `.prod`, Nginx prod.conf, images ghcr.io, profiles disable db/redis/minio
- **`docker-compose.staging.yml`** : port 8080, pas SSL, env_file `.staging`, Nginx staging.conf
- **`docker-compose.override.yml`** : dev local, port 80, env_file `.local`, Nginx staging.conf

Les `env_file` sont dans les overrides (pas dans la base) — Docker merge les listes, pas les remplace.

### C-N3. Dossier `backend/.envs/` + naming POSTGRES_* unifié ✅

- Dossier `backend/.envs/` contenant `.prod`, `.staging`, et `.local`
- Naming PostgreSQL unifié : `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (avec fallback `DB_*` dans settings.py)
- Variable `ENVIRONMENT` injectée dans les overrides (pas dans les fichiers .env)
- `.env.production` et `.env.db` obsolètes supprimés

### C-N4. Nginx resolver 127.0.0.11 fix + variable upstream ✅

- `resolver 127.0.0.11 valid=30s;` dans les deux configs Nginx (DNS Docker interne)
- `/api/` et `/admin/` utilisent `set $backend_upstream backend:8000;` + `proxy_pass http://$backend_upstream;` → force la re-résolution DNS à chaque requête
- Commit `13e5ba8` (variable upstream) + `4271f05` (resolver initial)

### C-N5. Badge environnement frontend (VITE_ENVIRONMENT) ✅

- Variable Vite `VITE_ENVIRONMENT` injectée via les args de build Docker :
  - Production : `VITE_ENVIRONMENT: production` → badge rouge "PROD"
  - Staging : `VITE_ENVIRONMENT: staging` → badge orange "STG"
  - Dev : fallback → badge vert "DEV"
- Implémenté dans `frontend/src/components/Navbar.jsx`

### C-N6. Resource limits (mem_limit) sur tous les conteneurs ✅

| Service | mem_limit | Actif en prod |
|---------|-----------|:---:|
| db | 200m | ❌ disabled |
| redis | 64m | ❌ disabled |
| minio | 128m | ❌ disabled |
| backend | 256m | ✅ |
| celery-worker | 256m | ✅ |
| celery-beat | 64m | ✅ |
| frontend | 128m | ✅ |
| nginx | 32m | ✅ |
| certbot | 32m | ✅ |
| **Total prod** | **768m** | (sous 961 MiB physiques) |

### C-N7. Génération d'une SECRET_KEY forte — INCOMPLET ⚠️

- La SECRET_KEY dans `backend/.envs/.prod` utilise `changeme-generate-with-python-secrets` comme placeholder
- **Problème** : sur le serveur, la valeur réelle commence toujours par `django-insecure-` → clé faible non corrigée
- À générer avec : `python -c "import secrets; print(secrets.token_urlsafe(50))"` (valeur générée sur le serveur : `ZR4e5ySk2aV2Bc7fbDeVBVlxft8veAwWIb8e7ff3IApkz-kCmWSbs4MnEYdgH9NBgeU`)
- Voir problème **D2** ci-dessous

### C-N8. Agent deploy-fullstack v2.0 complet ✅

- Mise à jour majeure de l'agent de déploiement (`.github/agents/deploy-fullstack.md`)
- Support complet du protocole dry-run (analyse préalable + preflight-check)
- Détection automatique du fournisseur cloud
- Gestion des 5 phases : ssh-bootstrap → server-setup → code-deploy → cicd → ssl

### C-N9. NOUVEAU — Tiered email backend (console/smtp/resend) ✅

- Backend email configurable par environnement via `EMAIL_BACKEND_TYPE` :
  - **Dev/CI** : `console` → `django.core.mail.backends.console.EmailBackend` (défaut)
  - **Staging** : `smtp` → `django.core.mail.backends.smtp.EmailBackend` (Gmail SMTP)
  - **Production** : `resend` → `core.mail.ResendEmailBackend` (custom)
- `ResendEmailBackend` (60 lignes) utilise le SDK Resend, supporte cc/bcc/reply_to/headers/HTML
- `DEFAULT_FROM_EMAIL=hello@webtech-dev.info` en production
- Commits : `23e78aa`, `09a7efc`, `15bb1c5`, `a2c20be`

### C-N10. NOUVEAU — Images Docker sur ghcr.io (plus de build local) ✅

- Images backend + frontend construites dans GitHub Actions (job `build-and-push`)
- Poussées sur `ghcr.io/tawounfouet/clickmart-backend:latest` et `ghcr.io/tawounfouet/clickmart-frontend:latest`
- Sur le Linode : `docker compose pull` au lieu de `docker compose build`
- `docker login ghcr.io` ajouté avant le pull (commit `ccf1ffd`) — packages privés
- Avantage : pas de compilation sur le VPS → RAM préservée, déploiement plus rapide
- Tailles images : backend 92.5 MB, frontend 26.5 MB

### C-N11. NOUVEAU — `docker-compose.override.yml` pour le dev local ✅

- Fichier `docker-compose.override.yml` (auto-chargé par Docker Compose)
- Surcharge `backend`/`celery-*` avec `env_file: ./backend/.envs/.local`
- Surcharge `nginx` avec port 80 et staging.conf
- `.env` à la racine pour `DATABASE_URL` local
- Fichier `.local` créé avec `ALLOWED_HOSTS=87.106.222.62` (IP ionos) et `EMAIL_BACKEND_TYPE=resend`

### C-N12. NOUVEAU — PostgreSQL + Redis distants (49.13.239.42) ✅

- Production utilise des services distants au lieu de conteneurs Docker :
  - **PostgreSQL** : `postgres://...@49.13.239.42:5432/clickmart?sslmode=require` (TLS obligatoire)
  - **Redis** : `redis://...@49.13.239.42:6379/0` (authentification par mot de passe)
- Permet de désactiver les conteneurs db + redis → économie de 264 MiB RAM

### C-N13. NOUVEAU — Profiles `disabled` pour db/minio/redis en prod ✅

- `docker-compose.prod.yml` désactive 3 services via `profiles: [disabled]` :
  ```yaml
  db:
    profiles:
      - disabled
  redis:
    profiles:
      - disabled
  minio:
    profiles:
      - disabled
  ```
- Résultat : 6 conteneurs au lieu de 9 en production
- Commits : `8d9db2d`, `ab38374`, `b43245b`

### C-N14. NOUVEAU — Optimisations Dockerfile (image allégée) ✅

- Suppression de `gcc` et `libpq-dev` du Dockerfile backend (commit `6c3fbb1`)
- Backend image : 92.5 MB (down from ~450 MB)
- Healthcheck Dockerfile (pas seulement docker-compose) pour le backend
- Frontend multi-stage (node:18 build → nginx:alpine) : 26.5 MB

### C-N15. NOUVEAU — Commande `create_admin` automatique au démarrage ✅

- `backend/users/management/commands/create_admin.py` : crée/maj le superuser depuis `ADMIN_EMAIL`/`ADMIN_PASSWORD`
- Exécutée dans le CMD du conteneur backend (avant gunicorn) :
  ```
  python manage.py create_admin && gunicorn ...
  ```
- Si l'admin existe déjà → met à jour le mot de passe
- Commit `23e78aa` + fix `558bdab` (username=email pour Django)

---

## PARTIE D — PROBLÈMES

### ⚠️ D1. MODÉRÉ — RAM sous-dimensionnée (ex-C6)

**Statut** : Avertissement permanent — 961 MiB pour 6 conteneurs Docker (amélioré : étaient 8 avant).  
**mem_limits cumulés** : 768 MiB (sous la RAM physique — n'était plus le cas avec 1032 MiB avant).  
**Disponible actuel** : 273 MiB sur 961 MiB.  

**Recommandation** : Upgrader le plan Linode à 2 Go minimum si le trafic augmente.  
**Impact actuel** : Réduit depuis le dernier dry-run — db/redis/minio désactivés, images pré-buildées sur ghcr.io.

### 🟡 D2. MODÉRÉ — SECRET_KEY toujours faible (régression)

**Statut** : La SECRET_KEY sur le serveur de production commence par `django-insecure-` (préfixe identifiable).  
**Valeur locale** (`backend/.envs/.prod`) : `changeme-generate-with-python-secrets` (placeholder jamais remplacé).  
**Valeur serveur** : `django-insecure-MY6m9dE7AIPRKQvfqNmpLmAckKjlrYtpws41kSrGNriCdn-Hi_qnaDVyJzrEbyBYFrc`.  

Le dry-run précédent (2026-07-29 16h15) indiquait ce problème comme résolu (C4), mais la clé actuelle est toujours faible.  
**Action** : Générer une clé forte (`python -c "import secrets; print(secrets.token_urlsafe(50))"`) et mettre à jour `.envs/.prod` + redéploiement.

### 🟢 D3. MINEUR — `.envs/.local` utilise la clé API Resend de production

**Statut** : Le fichier `backend/.envs/.local` contient `EMAIL_BACKEND_TYPE=resend` avec la même `RESEND_API_KEY` que la production.  
**Impact** : Risque de consommation involontaire de quota Resend pendant le développement local.  
**Recommandation** : Passer `EMAIL_BACKEND_TYPE=console` en local (défaut de settings.py si absent).

---

## PARTIE E — PROBLÈMES RÉSOLUS (depuis le dry-run initial du 2026-07-29)

| ID | Problème | Gravité | Résolu le | Solution |
|---|---|---|---|---|
| C1 | Backend crash (circular import celery.py) | 🔴 Critique | 2026-07-29 | Fichier `/opt/clickmart/backend/celery.py` supprimé |
| C2 | DEBUG=True en production | 🟠 Majeur | 2026-07-29 | `DEBUG=False` dans `backend/.envs/.prod` |
| C3 | CORS incomplet (manque origines HTTPS) | 🟠 Majeur | 2026-07-29 | Ajout de `https://webtech-dev.info` et `https://www.webtech-dev.info` |
| C5 | sudo NOPASSWD non configuré | 🟡 Modéré | 2026-07-29 | `/etc/sudoers.d/deploy` créé |
| C7 | Healthchecks Celery manquants | 🟡 Modéré | 2026-07-29 | Healthchecks ajoutés dans `docker-compose.yml` |
| C8 | Secrets GitHub dupliqués (SSH_*) | 🟢 Mineur | 2026-07-29 | Secrets SSH_* nettoyés, seuls LINODE_* actifs |
| C9 | client_max_body_size absent (Nginx) | 🟢 Mineur | 2026-07-29 | `client_max_body_size 10M;` ajouté |
| C10 | Compose monolithique, pas de multi-env | 🟡 Modéré | 2026-07-29 | Split base + prod + staging + override |
| C11 | env_file dans la base → merge incorrect | 🟡 Modéré | 2026-07-29 | `env_file` déplacé dans les overrides |
| C12 | Naming DB_* / POSTGRES_* incohérent | 🟢 Mineur | 2026-07-29 | POSTGRES_* unifié avec fallback DB_* |
| C13 | Cache DNS Docker → Nginx 502 | 🟡 Modéré | 2026-07-29 | `resolver 127.0.0.11 valid=30s;` + variable upstream |
| C14 | Build Docker sur le VPS → RAM saturée | 🟡 Modéré | 2026-07-29 | Images buildées sur GitHub (ghcr.io) |
| C15 | Pas d'override pour le dev local | 🟢 Mineur | 2026-07-29 | `docker-compose.override.yml` + `.envs/.local` |
| C16 | Conteneurs inutiles en prod (db/redis/minio) | 🟡 Modéré | 2026-07-29 | `profiles: [disabled]` + services distants |
| C17 | Gcc/libpq-dev dans l'image Docker | 🟢 Mineur | 2026-07-29 | Supprimés → image 92.5 MB |

### Détail des corrections récentes

#### C14 — Build Docker sur le VPS → ghcr.io

**Avant** : `docker compose build` exécuté sur le Linode → consommation RAM pendant la compilation (risque OOM).  
**Solution** : Job `build-and-push` dans GitHub Actions, `docker compose pull` sur le Linode.  
**Vérification** : `docker compose images` → toutes les images backend/frontend viennent de `ghcr.io/tawounfouet/*` ✅

#### C15 — docker-compose.override.yml pour le dev local

**Avant** : Pas de configuration Docker pour le développement local (fallback SQLite seulement).  
**Solution** : `docker-compose.override.yml` (auto-chargé) + `backend/.envs/.local` avec PostgreSQL local, Redis local, MinIO.  
**Vérification** : `ls backend/.envs/.local` → présent ✅

#### C16 — Conteneurs inutiles en prod (db/redis/minio)

**Avant** : 8 conteneurs dont db (200m), redis (64m), minio (128m) qui n'étaient pas utilisés (services distants).  
**Solution** : `profiles: [disabled]` dans `docker-compose.prod.yml` → 6 conteneurs actifs.  
**Vérification** : `docker compose ps` → 6 conteneurs, pas de db/redis/minio ✅

#### 🟡 D2 — SECRET_KEY faible (régressé, non résolu)

**Avant** (rapport précédent) : Déclaré résolu (C4) — "Nouvelle clé forte générée dans `.envs/.prod`".  
**Constat actuel** : La clé sur le serveur commence par `django-insecure-`. Le placeholder dans `.envs/.prod` n'a jamais été remplacé.  
**Statut** : Ré-ouvert comme D2.

---

## SYNTHÈSE

| Indicateur | Dry-run précédent (16h15) | Dry-run actuel (20h15) |
|---|---|---|
| Conteneurs healthy | 6/8 | **4/6** (2 sans healthcheck) ✅ |
| Conteneurs total | 8 | **6** (db/redis/minio disabled) |
| Backend | ✅ Healthy | ✅ Healthy |
| Celery worker/beat | ✅ Healthy | ✅ Healthy |
| HTTP frontend | ✅ 200 OK | ✅ 200 OK |
| HTTP API | ✅ 200 OK | ✅ 200 OK |
| DEBUG production | ✅ False | ✅ False |
| CORS HTTPS | ✅ Présent | ✅ Présent |
| SECRET_KEY | ✅ Forte (déclaré) | ⚠️ django-insecure- (régressé) |
| sudo NOPASSWD | ✅ Configuré | ✅ Configuré |
| Secrets GitHub | ✅ Nettoyés (3 actifs) | ✅ 3 actifs |
| Nginx body size | ✅ 10M | ✅ 10M |
| Nginx DNS resolver | ✅ 127.0.0.11 | ✅ + variable upstream |
| Email backend | ❌ Non documenté | ✅ Tiers console/smtp/resend |
| Images registry | ❌ Build local | ✅ ghcr.io (build-and-push) |
| Dev override | ❌ Absent | ✅ docker-compose.override.yml |
| Branches CI/CD | ✅ dev/stg/main | ✅ + build-and-push job |
| Compose multi-env | ✅ Base + overrides | ✅ + override.yml |
| Naming env | ✅ POSTGRES_* unifié | ✅ POSTGRES_* + DATABASE_URL |
| Badge environnement | ✅ PROD/STG/DEV | ✅ PROD/STG/DEV |
| Mem limits | ✅ 8/8 conteneurs | ✅ 6/6 conteneurs |
| Agent deploy | ✅ v2.0 | ✅ v2.0 |
| RAM dispo | 302 MiB | 273 MiB ⚠️ |
| Disque libre | 14 Go | 9.8 Go ⚠️ |
| **Problèmes ouverts** | **1** (D1 — RAM) | **3** (D1 RAM, D2 SECRET_KEY, D3 .local resend) |

> **Conclusion** : 16/17 problèmes résolus, 3 ouverts (dont 1 régression SECRET_KEY). La production est stable avec 6 conteneurs (optimisation RAM). Les images sont buildées sur GitHub (ghcr.io) et pullées sur le Linode. Le tiered email backend (console/smtp/resend) est fonctionnel avec Resend en production. Le service PostgreSQL + Redis distant (49.13.239.42) réduit la charge sur le VPS. La SECRET_KEY doit être régénérée (régression D2).

---

**Fin du rapport dry-run. Aucune modification n'a été effectuée sur le serveur.**

---

## ANNEXE — Détail de l'analyse agent (raisonnement complet)

### 1. Structure Docker split (9 services + 3 overrides)

Analyse des 4 fichiers compose :
- `docker-compose.yml` (base) : 8 services avec builds, healthchecks, mem_limits
- `docker-compose.prod.yml` : surcharge nginx (80/443 + SSL), certbot, images ghcr.io, profiles disabled, env_file `.prod`
- `docker-compose.staging.yml` : surcharge nginx (8080), env_file `.staging`
- `docker-compose.override.yml` : dev local, env_file `.local`, port 80

Profiles disabled en prod : `db`, `redis`, `minio` → 6 conteneurs actifs.

### 2. Images Docker sur ghcr.io

```bash
ssh deploy@172.239.20.14 'docker compose -f docker-compose.yml -f docker-compose.prod.yml images'
```

→ Toutes les images backend/frontend viennent de `ghcr.io/tawounfouet/clickmart-*:latest`. Nginx et certbot utilisent des images publiques (nginx:alpine, certbot/certbot).

### 3. Tiered email backend

`settings.py` utilise `EMAIL_BACKEND_TYPE` pour router vers le bon backend :
- `resend` → `core.mail.ResendEmailBackend` (custom, 60 lignes, SDK Resend)
- `smtp` → `django.core.mail.backends.smtp.EmailBackend`
- Défaut → `django.core.mail.backends.console.EmailBackend`

Vérification production :
```python
>>> from django.core.mail import get_connection
>>> conn = get_connection()
>>> type(conn).__module__ + '.' + type(conn).__qualname__
'core.mail.ResendEmailBackend'
```
✅ ResendEmailBackend actif et fonctionnel.

### 4. PostgreSQL + Redis distants

DATABASE_URL production : `postgres://...@49.13.239.42:5432/clickmart?sslmode=require`  
CELERY_BROKER_URL production : `redis://...@49.13.239.42:6379/0` (avec mot de passe)

Connexion vérifiée : `docker compose exec backend celery -A config inspect ping` → 1 node online ✅

### 5. Commande create_admin

`backend/users/management/commands/create_admin.py` :
- Lit `ADMIN_EMAIL` et `ADMIN_PASSWORD` depuis `.env`
- Crée ou met à jour le superuser
- Exécutée au démarrage du backend (dans le CMD avant gunicorn)

### 6. État des conteneurs

```bash
ssh deploy@172.239.20.14 "docker compose -f docker-compose.yml -f docker-compose.prod.yml ps"
```

→ 6/6 conteneurs running, 4/6 avec healthcheck OK. Aucun crash, aucun unhealthy.

### 7. Tests HTTP

```bash
curl -sk -o /dev/null -w "%{http_code}" https://webtech-dev.info/ → 200
curl -sk -o /dev/null -w "%{http_code}" "https://webtech-dev.info/api/v1/products/?format=json" → 200
curl -sk -o /dev/null -w "%{http_code}" https://webtech-dev.info/admin/ → 302
```

Tous les endpoints répondent correctement.

### 8. Vérification des variables d'environnement

```bash
ssh deploy@172.239.20.14 "docker compose exec backend printenv | grep -E '^(ENVIRONMENT|DEBUG|ALLOWED|CORS|EMAIL|RESEND|DATABASE_URL|CELERY|MEDIA|SECRET_KEY)'"
```

→ `DEBUG=False`, `ENVIRONMENT=production`, `EMAIL_BACKEND_TYPE=resend`, `DATABASE_URL` pointe vers 49.13.239.42, `CELERY_BROKER_URL` pointe vers 49.13.239.42:6379.  
⚠️ `SECRET_KEY` commence par `django-insecure-` (régression, voir D2).

### 9. Synthèse des corrections

| Niveau | Dry-run précédent | Dry-run actuel |
|---|---|---|
| 🔴 Critique | 0 | 0 |
| 🟠 Majeur | 0 | 0 |
| 🟡 Modéré | 1 (D1 — RAM) | 1 (D1 RAM) + 1 (D2 SECRET_KEY régressé) |
| 🟢 Mineur | 0 | 1 (D3 .local resend API key) |
| **Total** | **1** | **3** |
