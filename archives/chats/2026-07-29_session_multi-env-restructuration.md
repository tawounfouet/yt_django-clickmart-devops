# Session: Restructuration Multi-Environnement Docker Compose

**Date**: 2026-07-29
**Duration**: ~1h30
**Agent(s)**: opencode (planification + exécution), deploy-fullstack (vérification)
**Phase**: build + deploy

---

## Intent

Restructurer l'infrastructure Docker Compose pour supporter proprement 3 environnements (local, staging, production) via des fichiers d'override, unifier le naming des variables PostgreSQL, et nettoyer les redondances héritées.

## Outcome

- `docker-compose.yml` splitté en base + 2 overrides (`prod`, `staging`)
- Fichiers `.env` déplacés dans `backend/.envs/`
- Naming PostgreSQL unifié (`POSTGRES_*` avec fallback `DB_*`)
- `.env.db` supprimé (redondant)
- `default.conf` renommé en `prod.conf`
- CI/CD mis à jour avec les flags `-f docker-compose.yml -f docker-compose.prod.yml`
- Déploiement vérifié sur Linode : 8/8 healthy, 200 OK

---

## Decisions

| # | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| 1 | Split docker-compose en base + overrides | Séparation des préoccupations : la base définit les services communs, les overrides spécialisent par environnement. Évite la duplication et les conditionnels `profiles`. | Un seul fichier avec `profiles` — rejeté car difficile à maintenir et sujet aux erreurs de déploiement. |
| 2 | Déplacer `.env` dans `backend/.envs/` | Namespacing clair : les variables appartiennent au backend. Évite la pollution de la racine avec des fichiers cachés. | Garder dans `backend/` à plat — rejeté pour cause de désordre à la racine. |
| 3 | Unifier le naming PostgreSQL (`POSTGRES_*`) | Django settings utilise déjà `POSTGRES_*` comme clé primaire. Le fallback `DB_*` assure la rétrocompatibilité. | Garder `DB_*` partout — rejeté car incompatible avec le naming officiel PostgreSQL attendu par l'image Docker. |
| 4 | Supprimer `.env.db` | Redondant : les variables PostgreSQL (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`) sont déjà dans chaque `.envs/.*`. | Garder `.env.db` séparé — rejeté, ajoute de la confusion (deux sources de vérité pour la DB). |
| 5 | Renommer `default.conf` → `prod.conf` | Alignement avec la convention multi-environnement (`staging.conf` existe déjà). | Garder `default.conf` — rejeté, nom ambigu qui ne reflète pas l'environnement. |
| 6 | Certbot uniquement dans l'override `prod` | Le staging est HTTP-only (port 8080), pas besoin de SSL. | Certbot partout — rejeté, staging n'a pas de domaine valide pour Let's Encrypt. |
| 7 | Volumes nommés distincts par environnement | `clickmart_postgres_data` (prod) vs `staging_postgres_data` (staging) — évite les collisions de données entre environnements. | Volume unique partagé — rejeté, risque de corruption entre envs. |

## Files Created

| File | Purpose |
|---|---|
| `docker-compose.prod.yml` | Override production : SSL (ports 80/443), certbot, volumes Let's Encrypt, env `.prod` |
| `infra/nginx/prod.conf` | Configuration Nginx production avec HTTPS, certificats Let's Encrypt, proxy frontend + backend + static/media |

## Files Modified

| File | Change summary |
|---|---|
| `docker-compose.yml` | Strippé en base commune : plus de ports, plus de SSL, plus de certbot. `env_file` pointe vers `./backend/.envs/.local`. Volumes nommés retirés (délégués aux overrides). |
| `docker-compose.staging.yml` | Aligné avec `.envs/.staging`. Ajout des volumes media/static sur nginx. DB ajoutée à l'override (`env_file`). Port 8080 uniquement (HTTP). |
| `Makefile` | Ajout des cibles `up-staging` et `up-prod` avec les flags `-f docker-compose.yml -f docker-compose.{staging,prod}.yml` |
| `.github/workflows/automate.yml` | Ligne 97 : `docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d` |
| `backend/config/settings.py` | `POSTGRES_DB/USER/PASSWORD` avec fallback `DB_NAME/USER/PASSWORD`. Valeurs par défaut ajoutées (`clickmart`, `postgres`, `postgres`). |
| `.gitignore` | Chemins mis à jour : `backend/.envs/.local`, `backend/.envs/.staging`, `backend/.envs/.prod` |
| `backend/.env.example` | Mis à jour pour refléter le nouveau naming `POSTGRES_*` |

## Files Deleted

| File | Reason |
|---|---|
| `.env.db` | Redondant — les variables PostgreSQL sont déjà dans les `.envs/.*` |
| `infra/nginx/default.conf` | Renommé en `prod.conf` |

## Files Renamed

| From | To | Reason |
|---|---|---|
| `backend/.env.local` | `backend/.envs/.local` | Namespacing dans `.envs/` |
| `backend/.env.staging` | `backend/.envs/.staging` | Namespacing dans `.envs/` |
| `infra/nginx/default.conf` | `infra/nginx/prod.conf` | Alignement naming multi-environnement |

---

## Key Context

- **Serveur production** : Linode 172.239.20.14, domaine `webtech-dev.info`
- **Archi Docker finale** : 8 services (db, redis, backend, celery-worker, celery-beat, frontend, nginx, certbot)
- **Resource limits** (`mem_limit`) appliqués sur les 8 services : db=200m, redis=64m, backend=256m, celery-worker=256m, celery-beat=64m, frontend=128m, nginx=32m, certbot=32m
- **PostgreSQL** : variables passées via `env_file` (plus de `environment:` hardcodé dans docker-compose.yml)
- **Staging** : HTTP uniquement sur port 8080, pas de certbot, volume nommé distinct
- **Certbot** : service Docker avec boucle de renouvellement toutes les 12h, pas de cron host
- **Déploiement CI/CD** : `git reset --hard origin/main` (pas `git pull`) + `docker compose -f docker-compose.yml -f docker-compose.prod.yml`

## Commands Run

| Command | Purpose | Result |
|---|---|---|
| `docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d` | Déploiement production | 8/8 healthy |
| `docker compose ps` | Vérification post-déploiement | Tous les services `Up` |
| `curl -sf http://localhost/api/v1/products/` | Healthcheck backend | 200 OK |
| `curl -sf http://localhost/` | Healthcheck frontend | 200 OK |
| `git reset --hard origin/main` | Synchronisation serveur (CI) | Clean |

## Patterns Established

- **Override pattern** : `docker-compose.yml` = base commune (jamais déployé seul). `docker-compose.{env}.yml` = spécialisation par environnement. Combinaison : `-f base -f override`.
- **Naming convention** : `.envs/.{local,staging,prod}` — fichiers cachés dans un dossier dédié
- **Volume naming** : `{project}_postgres_data` (prod), `{env}_postgres_data` (staging)
- **Nginx conf naming** : `{env}.conf` (`staging.conf`, `prod.conf`)
- **PostgreSQL vars** : primaire `POSTGRES_*`, fallback `DB_*` pour rétrocompatibilité

## Issues & Workarounds

| Issue | Workaround | Status |
|---|---|---|
| `.env.db` redondant avec les `.envs/.*` | Supprimé, toutes les variables DB sont inline dans les `.envs/` | resolved |
| `db` service utilisait `environment:` hardcodé au lieu de `env_file:` | Remplacé par `env_file: ./backend/.envs/.{env}` dans chaque override | resolved |
| Risque de collision de volumes entre staging et prod | Volumes nommés distincts (`clickmart_postgres_data` vs `staging_postgres_data`) | resolved |
| CI/CD ne savait pas quel fichier compose utiliser | Ajout des flags `-f` explicites dans `automate.yml` | resolved |

---

## Action Items

- [ ] Vérifier que `backend/.envs/.prod` contient les bonnes valeurs sur le serveur Linode (actuellement .gitignoré)
- [ ] Tester `make up-staging` localement pour valider l'override staging
- [ ] Documenter le pattern multi-environnement dans `docs/deploy/` (à créer si absent)

## Related Sessions

- `archives/chats/2026-07-28_session_deploiement-linode-clickmart.md` — Déploiement initial sur Linode, base de l'infrastructure
- `archives/chats/2026-07-29_session_finalisation-clickmart.md` — Finalisation P3-P6, SSL, restructuration infra (contexte global)
- `archives/chats/2026-07-29_session_amifond_deploy-production-cicd.md` — Même agent de déploiement utilisé sur un autre projet

---

## Full Conversation Summary

1. **Contexte** : L'infrastructure avait évolué organiquement — un `docker-compose.yml` monolithique avec profils (`profiles: production`), `.env` dispersés entre la racine et `backend/`, et `.env.db` redondant.

2. **Split Compose** : Extraction de tout ce qui est spécifique à un environnement (ports, SSL, certbot, volumes nommés, env_file) vers des fichiers d'override. La base (`docker-compose.yml`) ne contient que les définitions de services communes.

3. **Migration .env** : Déplacement de `backend/.env.{local,staging}` vers `backend/.envs/.{local,staging,prod}`. Mise à jour de `.gitignore` et de tous les `env_file:` dans les fichiers compose.

4. **Unification PostgreSQL** : Les settings Django utilisaient historiquement `DB_NAME/USER/PASSWORD`. Changement vers `POSTGRES_DB/USER/PASSWORD` (naming officiel PostgreSQL) avec fallback `DB_*` pour rétrocompatibilité.

5. **Nettoyage** : Suppression de `.env.db` (redondant) et renommage de `default.conf` → `prod.conf` pour alignement avec `staging.conf`.

6. **CI/CD** : Mise à jour du step de déploiement dans `automate.yml` pour utiliser les flags `-f docker-compose.yml -f docker-compose.prod.yml`.

7. **Vérification** : Déploiement sur Linode, 8/8 services healthy, healthchecks backend et frontend OK (200).
