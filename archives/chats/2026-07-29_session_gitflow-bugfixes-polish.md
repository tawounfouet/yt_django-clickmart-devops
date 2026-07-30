# Session: GitFlow, Bugfixes & Final Polish

**Date**: 2026-07-29
**Duration**: ~2h (session étalée sur plusieurs sous-sessions)
**Agent(s)**: opencode (planification + exécution), deploy-fullstack
**Phase**: build + deploy + maintain

---

## Intent

Finaliser l'architecture multi-environnement après la restructuration Docker Compose : activer le CI/CD conditionnel par branche (dev→tests, stg→deploy staging :8080, main→deploy prod :80/443), corriger 3 bugs critiques découverts lors des déploiements parallèles, ajouter le badge d'environnement dans la navbar, et durcir l'agent de déploiement contre les OOM.

## Outcome

- CI/CD fonctionnel sur 3 branches avec déploiements conditionnels
- 2 stacks Docker isolées sur le même VPS via `docker compose -p clickmart` / `-p clickmart-stg`
- 3 bugs corrigés : merge d'env_file, DNS caching Nginx, .local symlink hack
- Badge PROD/STG/DEV visible dans la navbar
- Agent deploy-fullstack enrichi avec règle anti-OOM et commandes `inventory`/`dry-run`
- Leçon apprise : 2 stacks simultanées sur 961 MiB → OOM kernel → reboot

---

## Decisions

| # | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| 1 | CI/CD conditionnel par branche : `dev` → tests seuls, `stg` → deploy staging :8080, `main` → deploy prod :80/443 | Séparation claire : dev = CI seul (pas de VPS), stg = pré-production HTTP, main = production HTTPS. Évite les déploiements intempestifs. | Un seul job de déploiement avec condition `if: github.ref` — rejeté, trop fragile et pas assez explicite. |
| 2 | Deux répertoires serveur distincts : `/opt/clickmart` (main) et `/opt/clickmart-stg` (stg) | Permet des `git fetch` + `git reset --hard` indépendants par branche. Chaque stack a son propre clone git. | Répertoire unique avec `git checkout` dynamique — rejeté, risque de conflit git entre les deux environnements. |
| 3 | Retirer `env_file` de `docker-compose.yml` (base) | Docker Compose **fusionne** les listes `env_file` (ne les remplace pas). Si la base déclare `.envs/.local`, l'override `.prod` ne l'écrase pas → les valeurs locales polluent la production. Chaque override déclare maintenant son propre `env_file` pour chaque service. | Garder `env_file` dans la base avec un symlink `.envs/.local` → lien cassé sur le serveur — rejeté, hack fragile. |
| 4 | `resolver 127.0.0.11 valid=30s` dans Nginx | Sans directive `resolver`, Nginx résout les noms Docker une seule fois au démarrage. Si le conteneur backend est recréé avec une nouvelle IP, Nginx garde l'ancienne → `Connection refused`. `127.0.0.11` est le DNS interne de Docker ; `valid=30s` force la re-résolution sans casser le cache. | `resolver_timeout` seul — rejeté, ne résout pas le problème de cache permanent. |
| 5 | Badge d'environnement dans la navbar (`VITE_ENVIRONMENT`) | Distinguer instantanément PROD/STG/DEV dans l'interface. Build-time arg passé via `docker-compose.{env}.yml` → injecté dans le Dockerfile → accessible via `import.meta.env.VITE_ENVIRONMENT`. | Variable runtime (fetch API backend) — rejeté, trop lent et dépend d'un backend fonctionnel. |
| 6 | Règle anti-OOM : arrêter l'autre environnement avant de déployer | Le VPS Linode n'a que 961 MiB de RAM. Lancer les 2 stacks simultanément (2× postgres, 2× redis, 2× backend+gunicorn, 2× celery-worker, 2× frontend+nginx) dépasse la mémoire → OOM killer tue des processus au hasard → corruption possible. La règle est maintenant codifiée dans l'agent : un seul environnement à la fois sauf si ≥ 2 Go RAM. | Ajouter du swap — rejeté, masque le problème et dégrade les perfs. Upgrade VPS — rejeté, coût. |
| 7 | `mem_limit` sur tous les services Docker Compose | Plafonnement explicite empêche un service de consommer toute la RAM. Postgres 200m, Redis 64m, backend 256m, celery-worker 256m, celery-beat 64m, frontend 128m, nginx 32m, certbot 32m. | Pas de limite — rejeté, déjà prouvé que ça mène à l'OOM. |

---

## Files Created

| File | Purpose |
|---|---|
| `backend/.envs/.prod` | Variables d'environnement production : `POSTGRES_*`, `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `CORS_*`, `ENVIRONMENT=production` |
| `backend/.envs/.staging` | Variables d'environnement staging : même structure que `.prod` avec `DEBUG=True`, `ENVIRONMENT=staging`, DB staging dédiée |
| `Makefile` | Commandes `up-staging`, `up-prod`, `logs-staging`, `logs-prod` avec les flags `-p` et `-f` appropriés |

## Files Modified

| File | Change summary |
|---|---|
| `docker-compose.yml` | Retrait de `env_file` (8 lignes) — la base ne déclare plus aucun fichier d'environnement |
| `docker-compose.prod.yml` | Ajout `env_file: ./backend/.envs/.prod` sur `db`, `backend`, `celery-worker`, `celery-beat`. Ajout `VITE_ENVIRONMENT: production` sur le build `frontend`. Nginx : ports 80/443, montage `prod.conf`, volumes certbot. Volume nommé `clickmart_postgres_data`. |
| `docker-compose.staging.yml` | Ajout `env_file: ./backend/.envs/.staging` sur tous les services backend. Ajout `VITE_ENVIRONMENT: staging`. Nginx : port 8080 uniquement, montage `staging.conf`. Volume nommé `staging_postgres_data`. `ENVIRONMENT=staging` en variable d'env explicite. |
| `infra/nginx/prod.conf` | Ajout `resolver 127.0.0.11 valid=30s;` dans les 2 blocs `server` (HTTP + HTTPS) |
| `infra/nginx/staging.conf` | Ajout `resolver 127.0.0.11 valid=30s;` dans le bloc `server` HTTP |
| `frontend/Dockerfile` | Ajout `ARG VITE_ENVIRONMENT` + `ENV VITE_ENVIRONMENT=$VITE_ENVIRONMENT` (build-time → runtime) |
| `frontend/src/components/Navbar.jsx` | Ajout du badge d'environnement : lecture `import.meta.env.VITE_ENVIRONMENT`, map de couleurs (`production=red`, `staging=yellow`, `dev=grey`), badge Bootstrap `<span class="badge">` à côté de "ClickMart" |
| `.github/workflows/automate.yml` | Passage de 1 job `deploy` → 3 jobs conditionnels : `test-backend` + `test-frontend` (toutes branches) → `deploy-staging` (`if: stg + push`) → `deploy-production` (`if: main + push`). Chaque job de déploiement utilise son propre répertoire serveur et ses propres flags Docker Compose. |
| `Makefile` | Réécriture complète : `up-dev` (local, sans `-p`), `up-staging` (`-p clickmart-stg -f base -f staging`), `up-prod` (`-p clickmart -f base -f prod`), commandes `logs-*` et `down-*` symétriques |
| `backend/.env.staging` | Supprimé (déplacé dans `backend/.envs/.staging`) |
| `.opencode/agents/deploy-fullstack.md` | Ajout des entrées `inventory` et `dry-run` dans la table de détection du point de départ |
| `~/.config/opencode/agents/deploy-fullstack.md` | Ajout de la **règle d'or** (lignes 430-451) : ne jamais lancer prod+staging simultanément, vérifier et arrêter l'autre environnement avant de déployer, exception si ≥ 2 Go RAM. Commandes exactes de `docker compose down` par environnement. |

---

## Key Context

- **VPS Linode** : 961 MiB RAM, 1 vCPU, 25 Go SSD — contrainte mémoire sévère
- **Docker Compose merge behavior** : les listes (`env_file`, `ports`, `volumes`) sont **fusionnées**, pas remplacées. Un `env_file` dans la base + un dans l'override = les deux sont chargés. C'est documenté dans la spec Compose mais contre-intuitif.
- **Docker embedded DNS** : `127.0.0.11` est le résolveur DNS interne de Docker. Sans directive `resolver`, Nginx utilise le résolveur système (`/etc/resolv.conf`) qui ne connaît pas les noms de conteneurs Docker.
- **Vite environment variables** : seules les variables préfixées `VITE_` sont exposées au code client via `import.meta.env`. Les `ARG` du Dockerfile doivent être explicitement repassés en `ENV` pour être disponibles au build.
- **git reset --hard** utilisé dans le CI (pas `git pull`) pour éviter les conflits de merge sur le serveur.
- **Certbot** est un service Docker (pas un cron host), renouvellement toutes les 12h.

---

## Commands Run

| Command | Purpose | Result |
|---|---|---|
| `docker compose -p clickmart -f docker-compose.yml -f docker-compose.prod.yml up -d --build` | Déploiement production avec nom de projet isolé | 8/8 containers healthy |
| `docker compose -p clickmart-stg -f docker-compose.yml -f docker-compose.staging.yml up -d --build` | Déploiement staging sur port 8080 | 7/7 containers healthy |
| `docker compose -p clickmart ps` | Vérifier l'état de la stack production | Liste des conteneurs avec noms préfixés `clickmart-` |
| `curl -sf http://localhost:8080/` | Health check staging | 200 OK |
| `curl -sf http://localhost/api/v1/products/` | Health check backend production | 200 OK |

---

## Patterns Established

- **Project-named Compose** : `docker compose -p <name>` isole complètement les stacks (réseaux, volumes, noms de conteneurs). Les flags `-f` multiples permettent la composition déclarative base + override.
- **Environnement badge frontend** : pattern Vite build-arg → Dockerfile ARG+ENV → `import.meta.env.VITE_*` → composant React. Extensible à d'autres métadonnées (version, commit SHA).
- **env_file par override** : la base ne déclare aucun `env_file`. Chaque override déclare explicitement son `env_file` pour chaque service backend. Pas de symlink, pas de hack.
- **resolver 127.0.0.11** : à inclure systématiquement dans les confs Nginx qui proxient vers des noms de service Docker.
- **Anti-OOM deploy guard** : avant tout `docker compose up`, vérifier et `down` l'autre environnement.

---

## Issues & Workarounds

| Issue | Workaround | Status |
|---|---|---|
| Docker Compose fusionne `env_file` au lieu de remplacer → les valeurs `.local` polluent `.prod` | Retirer `env_file` de la base, chaque override déclare le sien | resolved |
| Nginx garde en cache l'IP du conteneur backend → `Connection refused` après rebuild | `resolver 127.0.0.11 valid=30s;` dans chaque bloc `server` | resolved |
| Le hack `.envs/.local` → symlink cassé sur le serveur (`.local` n'existe pas en staging/prod) | Supprimé avec la règle "pas de env_file dans la base" | resolved |
| 2 stacks Docker simultanées → OOM kernel (961 MiB RAM) → reboot serveur nécessaire | Règle anti-OOM dans l'agent : arrêter l'autre env avant de déployer. `mem_limit` sur chaque service. | resolved |
| `backend/.env.staging` à la racine → pollué | Déplacé dans `backend/.envs/.staging` avec `.prod` | resolved |

---

## Action Items

- [ ] Vérifier que le swap est activé sur le VPS (filet de sécurité, même avec la règle anti-OOM)
- [ ] Ajouter le commit SHA dans le badge d'environnement (optionnel — utile pour le debug)
- [ ] Documenter la contrainte mémoire dans le README ou AGENTS.md
- [ ] Tester le scénario "déploiement main alors que staging tourne" → doit automatiquement stopper staging

---

## Related Sessions

- `archives/chats/2026-07-29_session_multi-env-restructuration.md` — Restructuration Docker Compose (base + overrides, .envs, POSTGRES_* naming) — prérequis de cette session
- `archives/chats/2026-07-29_session_agent-deploy-fullstack.md` — Création initiale de l'agent deploy-fullstack
- `archives/chats/2026-07-29_session_amifond_deploy-production-cicd.md` — Premier déploiement production + CI/CD sur le VPS Linode
- `archives/chats/2026-07-28_session_deploiement-linode-clickmart.md` — Déploiement initial sur Linode

---

## Full Conversation Summary

1. **Mise en place du GitFlow** : Création des branches `dev`, `stg`, `main`. Le workflow CI/CD est repensé : `dev` ne déclenche que les tests, `stg` déploie automatiquement le staging sur le port 8080, `main` déploie la production sur 80/443. Chaque branche a son propre répertoire sur le serveur (`/opt/clickmart` vs `/opt/clickmart-stg`).

2. **Project-named Docker Compose** : Introduction de `docker compose -p clickmart` et `-p clickmart-stg` pour isoler les stacks. Les volumes Postgres sont nommés distinctement (`clickmart_postgres_data` vs `staging_postgres_data`). Le Makefile est enrichi avec `up-staging`, `up-prod`, `logs-staging`, `logs-prod`.

3. **Bug env_file merge** : Découverte que Docker Compose fusionne les listes `env_file` au lieu de les remplacer. La base déclarait `.envs/.local`, et malgré l'override `.staging`, les valeurs locales étaient toujours chargées. Solution : retirer tout `env_file` de la base et les déclarer explicitement dans chaque override.

4. **Bug Nginx DNS caching** : Après un rebuild du backend, Nginx continuait d'utiliser l'ancienne IP → `Connection refused`. Cause : Nginx résout les noms Docker au démarrage et les garde en cache indéfiniment. Solution : `resolver 127.0.0.11 valid=30s;` force la re-résolution via le DNS interne de Docker.

5. **Badge d'environnement** : Ajout d'un badge coloré (PROD rouge, STG jaune, DEV gris) dans la navbar à côté du logo ClickMart. Implémentation via `VITE_ENVIRONMENT` build arg → Dockerfile → `import.meta.env`.

6. **Crash OOM** : Tentative de faire tourner les 2 stacks simultanément sur le VPS 961 MiB → OOM killer → reboot nécessaire. Ajout d'une règle dans l'agent deploy-fullstack : arrêter l'environnement opposé avant tout déploiement. `mem_limit` sur tous les services.

7. **Mise à jour de l'agent** : L'agent deploy-fullstack reçoit les commandes `inventory` (génération `inventory.yml`) et `dry-run` (analyse sans déploiement). La règle anti-OOM est codifiée avec les commandes exactes.
