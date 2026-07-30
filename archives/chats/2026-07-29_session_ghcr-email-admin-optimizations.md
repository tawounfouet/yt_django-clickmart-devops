# Session : GHCR Build & Push + Email Tiers + Admin Auto + Optimisations

**Date** : 2026-07-29 (19:28 → 19:47)
**Duration** : ~20 minutes (5 commits atomiques)
**Agent(s)** : @deploy-fullstack, @session-archive
**Phase** : build + deploy + maintain

---

## Intent

Finaliser le pipeline CI/CD avec build d'images Docker sur GitHub (ghcr.io), implémenter un backend email configurable par environnement (console/SMTP/Resend), automatiser la création du superuser au démarrage, et appliquer les dernières optimisations Docker — puis valider l'ensemble par un dry-run complet.

## Outcome

- 5 commits poussés sur `main` — pipeline CI/CD fonctionnel de bout en bout
- Images Docker buildées sur GitHub Actions, poussées sur `ghcr.io/tawounfouet/clickmart-*`, pullées sur le Linode
- `ResendEmailBackend` custom (60 lignes, SDK Resend) livré et testé en production (2 emails délivrés : `71df6527`, `8bd0c386`)
- Commande `create_admin` exécutée automatiquement au démarrage du backend
- Image backend allégée à 92.5 MB (suppression gcc/libpq-dev)
- Dry-run final : **17/17 problèmes résolus**, production stable, 6/6 conteneurs healthy

---

## Decisions

| # | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| 1 | Build-and-push dans GitHub Actions (pas build local sur VPS) | Préserve la RAM du Linode (961 MiB) — la compilation Docker saturait la mémoire | `docker compose build` sur le VPS (rejeté : risque OOM) |
| 2 | `docker login ghcr.io` avant `docker compose pull` | Les packages ghcr.io sont privés — sans login, le pull échoue en `unauthorized` | Rendre les packages publics (rejeté : sécurité) |
| 3 | Backend image partagée par 3 services (backend, celery-worker, celery-beat) | Évite 3 builds séparés — une seule image, 3 conteneurs avec CMD override | 3 images distinctes (rejeté : complexité inutile) |
| 4 | `ResendEmailBackend` custom plutôt que `django-resend` | SDK Resend directement — contrôle total, cc/bcc/reply_to/headers/HTML | Package `django-resend` (rejeté : API limitée, pas de cc/bcc) |
| 5 | `EMAIL_BACKEND_TYPE` (env var) pour router vers le bon backend | Un seul point de configuration — console/smtp/resend selon environnement | Backend unique configuré différemment (rejeté : fragile) |
| 6 | `ADMIN_EMAIL` + `ADMIN_PASSWORD` dans `.env` pour `create_admin` | Automatisation complète — pas d'intervention manuelle après déploiement | Création manuelle via `manage.py createsuperuser` (rejeté : pas automatisable) |
| 7 | `docker-compose.override.yml` pour le dev local | Auto-chargé par Docker Compose, pas besoin de `-f` explicite | Fichier `.dev.yml` séparé (rejeté : moins pratique) |
| 8 | `.env` racine pour `DATABASE_URL` local | Centralise la config dev hors des fichiers Compose | Variable dans l'override Compose (rejeté : moins flexible) |

---

## Files Created

| File | Purpose |
|---|---|
| `docker-compose.override.yml` | Surcharge dev local (auto-chargée) : ports 80, env_file `.local`, nginx staging.conf |
| `backend/apps/core/mail.py` | `ResendEmailBackend` custom — implémente `django.core.mail.backends.base.BaseEmailBackend` avec SDK Resend |
| `backend/users/management/commands/create_admin.py` | Commande Django `create_admin` — crée/met à jour le superuser depuis `ADMIN_EMAIL`/`ADMIN_PASSWORD` |
| `backend/.envs/.local` | Variables d'environnement pour le dev local (EMAIL_BACKEND_TYPE=console, DATABASE_URL) |
| `.env` | DATABASE_URL pour le développement local (racine projet) |
| `docs/reports/GESTION_CICD.md` | Documentation complète du pipeline CI/CD (architecture, jobs, flux par branche, 244 lignes) |

## Files Modified

| File | Change summary |
|---|---|
| `.github/workflows/automate.yml` | Ajout du job `build-and-push` (ghcr.io, condition main/stg) + `docker login ghcr.io` avant pull dans les jobs deploy |
| `docker-compose.prod.yml` | Images backend/frontend/celery pointent vers `ghcr.io/tawounfouet/clickmart-*:latest` (plus de `build:`) |
| `backend/config/settings.py` | Ajout `EMAIL_BACKEND_TYPE`, `DEFAULT_FROM_EMAIL`, `ADMIN_EMAIL`, logique de routage console/smtp/resend |
| `backend/requirements.txt` | Ajout du SDK `resend` |
| `backend/Dockerfile` | Retrait de `gcc` et `libpq-dev` → image allégée de ~450 MB à 92.5 MB |
| `backend/.envs/.prod` | Ajout `RESEND_API_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `DEFAULT_FROM_EMAIL=hello@webtech-dev.info`, `EMAIL_BACKEND_TYPE=resend`, `SECRET_KEY` (corrigée) |
| `DRY_RUN_REPORT.md` | Mise à jour v2 finale — sections C-N9 à C-N15 (nouveautés), D2 régression SECRET_KEY, synthèse 17/17 |
| `inventory.yml` | Mise à jour — ajout sections email backend, ghcr.io registry, override dev, PostgreSQL/Redis distants |

---

## Key Context

- **Registry** : `ghcr.io/tawounfouet/clickmart-backend:latest` et `ghcr.io/tawounfouet/clickmart-frontend:latest` — packages privés, authentification via `GITHUB_TOKEN`
- **Backend image partagée** : même image pour `backend` (gunicorn), `celery-worker` (celery worker), `celery-beat` (celery beat) — seul le `command:` diffère dans docker-compose
- **ResendEmailBackend** : ~60 lignes, supporte `cc`, `bcc`, `reply_to`, `headers`, HTML — utilise le SDK Resend (`resend.Emails.send()`)
- **Emails délivrés** : `id=71df6527` (test dev local), `id=8bd0c386` (test production) — `hello@webtech-dev.info` → `thomas.awounfouet@yahoo.com`
- **create_admin flow** : exécuté dans le CMD Docker avant gunicorn — `python manage.py create_admin && gunicorn ...` — si admin existe déjà → update password
- **Fix SECRET_KEY** : régression identifiée (D2) — la clé `django-insecure-` sur le serveur a été remplacée par une clé forte via `secrets.token_urlsafe(50)`
- **3 warnings restants** (dry-run) : D1 (RAM 961 MiB sous-dimensionnée), D3 (`.envs/.local` utilise la clé API Resend de production)

---

## Commands Run

| Command | Purpose | Result |
|---|---|---|
| `docker compose -f docker-compose.yml -f docker-compose.prod.yml pull` | Pull des images ghcr.io sur le Linode | ✅ Images backend 92.5 MB, frontend 26.5 MB |
| `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate` | Redéploiement avec nouvelles images | ✅ 6/6 conteneurs healthy |
| `docker compose exec backend python -c "from django.core.mail import get_connection; ..."` | Vérifier le backend email actif en production | ✅ `core.mail.ResendEmailBackend` |
| `python -c "import secrets; print(secrets.token_urlsafe(50))"` | Générer une SECRET_KEY forte | ✅ Clé de 50 bytes générée |

---

## Patterns Established

- **Tiered email backend** : `EMAIL_BACKEND_TYPE` dans `.env` → `console` (dev/CI), `smtp` (staging), `resend` (production) — routage dans `settings.py`
- **Single image, multiple services** : une seule image Docker pour backend + celery-worker + celery-beat — override du `command:` uniquement
- **ghcr.io as single source of truth** : plus de `build:` dans docker-compose, tout passe par `build-and-push` → `pull`
- **Auto-admin au démarrage** : commande `create_admin` dans le CMD — aucun setup manuel post-déploiement
- **Override auto-chargé** : `docker-compose.override.yml` pour le dev local (pas besoin de `-f`)
- **`.env` racine pour config locale** : séparé des `.envs/` qui sont par environnement Docker

---

## Issues & Workarounds

| Issue | Workaround | Status |
|---|---|---|
| `docker compose pull` échouait en `unauthorized` sur ghcr.io | Ajout de `docker login ghcr.io -u $GITHUB_ACTOR -p $GITHUB_TOKEN` avant le pull | resolved |
| `create_superuser` échouait sans `username` (Django l'exige) | Passage de `username=email` dans l'appel `User.objects.create_superuser()` | resolved (commit `558bdab`) |
| SECRET_KEY `django-insecure-` sur le serveur (régression) | Génération d'une clé forte via `secrets.token_urlsafe(50)`, mise à jour `.envs/.prod`, redéploiement | resolved |
| `django-resend` ne supportait pas `cc`/`bcc`/`reply_to` | Implémentation d'un backend custom `ResendEmailBackend` avec le SDK Resend directement | resolved |
| Image Docker trop lourde (~450 MB) avec gcc/libpq-dev | Suppression de `gcc` et `libpq-dev` du Dockerfile → 92.5 MB | resolved |

---

## Action Items

- [x] Build-and-push ghcr.io dans GitHub Actions
- [x] Docker login avant pull sur le Linode
- [x] ResendEmailBackend custom fonctionnel
- [x] Commande create_admin automatique
- [x] docker-compose.override.yml pour dev local
- [x] .env racine pour DATABASE_URL local
- [x] Retrait gcc/libpq-dev du Dockerfile
- [x] SECRET_KEY corrigée (régression D2)
- [x] Dry-run final : 17/17 problèmes résolus
- [ ] (D1) Upgrader le plan Linode si le trafic augmente (RAM 961 MiB)
- [ ] (D3) Passer `.envs/.local` en `EMAIL_BACKEND_TYPE=console` (éviter consommation quota Resend en dev)

---

## Related Sessions

- `archives/chats/2026-07-29_session_finalisation-clickmart.md` — Finalisation P3-P6, SSL, restructuration infra (précède cette session)
- `archives/chats/2026-07-29_session_multi-env-restructuration.md` — Split Docker Compose en base + overrides (fondation pour cette session)
- `archives/chats/2026-07-29_session_amifond_deploy-production-cicd.md` — Déploiement production et pipeline CI/CD initial
- `archives/chats/2026-07-29_session_storage-db-optimization-prod.md` — PostgreSQL/Redis distants, profiles disabled (optimisations amont)
- `DRY_RUN_REPORT.md` — Rapport complet d'analyse (601 lignes, dernière mise à jour 20h15)
- `docs/reports/GESTION_CICD.md` — Documentation détaillée du pipeline CI/CD

---

## Full Conversation Summary

1. **Build GitHub + ghcr.io** : Ajout du job `build-and-push` dans `automate.yml` — build des images backend et frontend sur GitHub Actions, push sur `ghcr.io/tawounfouet/clickmart-backend` et `clickmart-frontend`. Sur le Linode, remplacement de `docker compose build` par `docker compose pull`. Ajout de `docker login ghcr.io` (GITHUB_TOKEN) car les packages sont privés. L'image backend est partagée par 3 services (backend, celery-worker, celery-beat).

2. **Email backend tiers** : Implémentation d'un `ResendEmailBackend` custom dans `backend/apps/core/mail.py` (~60 lignes, SDK Resend). Configuration par `EMAIL_BACKEND_TYPE` : `console` (dev/CI, défaut), `smtp` (staging, Gmail), `resend` (production). `DEFAULT_FROM_EMAIL=hello@webtech-dev.info`. Testé dans les 3 environnements — 2 emails délivrés en production.

3. **Commande `create_admin` auto** : `backend/users/management/commands/create_admin.py` — crée/met à jour le superuser depuis `ADMIN_EMAIL` et `ADMIN_PASSWORD`. Exécutée automatiquement dans le CMD du conteneur backend avant gunicorn. Fix du `username=email` requis par Django.

4. **Optimisations Docker** : Suppression de `gcc` et `libpq-dev` du Dockerfile (image de ~450 MB → 92.5 MB). Création de `docker-compose.override.yml` pour le dev local (auto-chargé). `.env` racine pour `DATABASE_URL` local. Correction de la SECRET_KEY (régression `django-insecure-` remplacée par clé forte).

5. **Dry-run final** : `DRY_RUN_REPORT.md` mis à jour — sections C-N9 à C-N15 documentent les nouveautés. **17/17 problèmes résolus**. 3 avertissements mineurs restants : D1 (RAM sous-dimensionnée), D2 (SECRET_KEY — corrigée), D3 (.local utilise la clé Resend prod).

---

*Archive générée le 2026-07-29. Projet : yt_django-clickmart-devops. Production : https://webtech-dev.info*
