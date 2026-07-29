# Gestion des environnements — ClickMart

> - **Date** : 2026-07-29
> - **Version** : 1.0
> - **Contexte** : Restructuration multi-environnement (dev/staging/production)

---

## Architecture

```
dev  ──→ stg  ──→ main
 │        │        │
 ▼        ▼        ▼
tests    deploy   deploy
         :8080    :80/443
```

| Branche | CI/CD | Déploiement | Port | Projet Docker |
|---|---|---|---|---|
| `dev` | Tests (78) | Aucun | — | — |
| `stg` | Tests + déploiement | Linode | 8080 (HTTP) | `clickmart-stg` |
| `main` | Tests + déploiement | Linode | 80/443 (HTTPS) | `clickmart` |

---

## Fichiers d'environnement

```
backend/
├── .env                  ← standalone dev (gitignored)
├── .env.example          ← template de référence
└── .envs/
    ├── .local            ← Docker dev (gitignored)
    ├── .staging          ← staging (gitignored)
    └── .prod             ← production (gitignored)
```

| Variable | Dev | Staging | Production |
|---|---|---|---|
| `DEBUG` | True | True | False |
| `ENVIRONMENT` | development | staging | production |
| `SECURE_SSL_REDIRECT` | False | False | True |
| `ALLOWED_HOSTS` | localhost | IP serveur | webtech-dev.info |
| `DB_NAME` | clickmart | clickmart_staging | clickmart |

---

## Docker Compose — Architecture à 3 fichiers

```
docker-compose.yml           ← base neutre (db, redis, backend, celery-*, frontend, nginx)
docker-compose.prod.yml      ← override production (SSL, certbot, ports 80/443, .env.prod)
docker-compose.staging.yml   ← override staging (HTTP, port 8080, .env.staging)
```

**Règle** : la base ne contient **aucun `env_file`**. Chaque override déclare le sien pour tous les services (`db`, `backend`, `celery-worker`, `celery-beat`).

### Pourquoi la base est sans `env_file` ?

Docker Compose **fusionne** les listes (`env_file`, `ports`, `volumes`), il ne les **remplace pas**. Si la base contient `.envs/.local` et l'override `.envs/.prod`, le résultat est `.local` + `.prod` — Docker tente de lire les deux et échoue si `.local` est absent.

**Solution** : la base = 0 `env_file`. Chaque override = explicite pour tous les services.

---

## Isolation des stacks (-p project)

```bash
# Production
docker compose -p clickmart -f docker-compose.yml -f docker-compose.prod.yml up -d

# Staging
docker compose -p clickmart-stg -f docker-compose.yml -f docker-compose.staging.yml up -d
```

| Aspect | `-p clickmart` | `-p clickmart-stg` |
|---|---|---|
| Conteneurs | `clickmart-db-1`, `clickmart-backend-1`... | `clickmart-stg-db-1`, `clickmart-stg-backend-1`... |
| Volume Postgres | `postgres_data` | `staging_postgres_data` |
| Réseau | `clickmart_default` | `clickmart-stg_default` |

Les deux stacks sont **totalement isolées** : volumes, réseaux, conteneurs séparés.

---

## Règle de sécurité : un seul environnement à la fois

```
⚠️ NE JAMAIS lancer production + staging simultanément
   sur un VPS < 2 Go de RAM → OOM killer → serveur down.
```

| Action | Avant de déployer |
|---|---|
| `@deploy-fullstack production` | Arrêter `-p clickmart-stg` |
| `@deploy-fullstack staging` | Arrêter `-p clickmart` |

Le fichier `Makefile` et l'agent `deploy-fullstack` appliquent cette règle automatiquement.

---

## CI/CD — Workflow par branche

```yaml
# .github/workflows/automate.yml
on:
  push:
    branches: [main, stg, dev]

jobs:
  test-backend:    # toute branche
  test-frontend:   # toute branche
  deploy-staging:  # stg uniquement → -p clickmart-stg
  deploy-production: # main uniquement → -p clickmart
```

| Job | Condition | Commande |
|---|---|---|
| `deploy-staging` | `github.ref == 'refs/heads/stg'` | `docker compose -p clickmart-stg ... up -d` |
| `deploy-production` | `github.ref == 'refs/heads/main'` | `docker compose -p clickmart ... up -d` |

---

## Nginx — Configuration par environnement

| Environnement | Fichier | SSL | Port exposé |
|---|---|---|---|
| Production | `infra/nginx/prod.conf` | ✅ Let's Encrypt | 80 → 443 |
| Staging | `infra/nginx/staging.conf` | ❌ HTTP only | 8080 |

**DNS caching fix** : `resolver 127.0.0.11 valid=30s;` dans chaque bloc `server`. Sans cette directive, Nginx garde l'IP du backend en cache et obtient `Connection refused` après un rebuild.

---

## Badge d'environnement (Frontend)

Un badge coloré est affiché dans la navbar à côté du logo ClickMart :

| Environnement | Badge | Variable |
|---|---|---|
| Production | 🔴 PROD | `VITE_ENVIRONMENT=production` |
| Staging | 🟡 STG | `VITE_ENVIRONMENT=staging` |
| Dev | ⚫ DEV | (défaut) |

La variable est injectée au build Docker via `--build-arg VITE_ENVIRONMENT=...` et lue par React : `import.meta.env.VITE_ENVIRONMENT`.

---

## Commandes utiles

```bash
# Makefile
make up-staging        # Lancer staging (port 8080)
make up-prod           # Lancer production (ports 80/443)
make down-staging      # Arrêter staging
make down-prod         # Arrêter production
make logs-staging      # Logs staging
make logs-prod         # Logs production

# Agent OpenCode
@deploy-fullstack production   # Déploiement prod (arrête staging)
@deploy-fullstack staging      # Déploiement staging (arrête prod)
@deploy-fullstack dry-run      # Analyse sans déploiement

# Docker direct
docker compose -p clickmart ps
docker compose -p clickmart-stg ps
```

---

## Incidents documentés

### OOM — 2026-07-29

**Cause** : les deux stacks (prod + staging) tournaient simultanément sur un Linode 961 MiB. Le CI/CD a déclenché un rebuild → RAM saturée → OOM killer → serveur inaccessible (SSH + HTTP KO).

**Résolution** : reboot via dashboard Linode, déploiement prod seul, staging arrêté.

**Leçon** : règle "un seul environnement à la fois" ajoutée à l'agent et au Makefile.

### Merge env_file — 2026-07-29

**Cause** : Docker Compose fusionne les listes `env_file`. La base contenait `.envs/.local`, l'override `.envs/.prod` → résultat `.local` + `.prod` → erreur si `.local` absent.

**Résolution** : retrait de tous les `env_file` de la base. Chaque override déclare le sien explicitement.

### DNS caching Nginx — 2026-07-29

**Cause** : Nginx résout `backend:8000` une seule fois au démarrage. Après rebuild, le backend obtient une nouvelle IP → Nginx garde l'ancienne → `Connection refused` → 502.

**Résolution** : `resolver 127.0.0.11 valid=30s;` (DNS Docker) dans chaque bloc `server`.

---

## Prochaines évolutions

- [ ] Upgrade Linode à 2 Go pour permettre staging + prod simultanés
- [ ] Ajouter `django-celery-beat` pour les tâches planifiées
- [ ] Ajouter Flower pour le monitoring Celery
- [ ] Automatiser le déploiement staging via CI/CD lorsque la branche `stg` est pushée
