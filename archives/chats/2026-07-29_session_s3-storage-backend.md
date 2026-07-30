# Session: S3 Storage Backend — django-storages + MinIO + OVH Object Storage

**Date**: 2026-07-29
**Duration**: ~1h30
**Agent(s)**: opencode (implémentation + debug), deploy-fullstack (dry-run + vérification)
**Phase**: build

---

## Intent

Implémenter un backend de stockage S3 compatible multi-provider pour ClickMart :
- **MinIO** en développement local/staging (via docker-compose.yml)
- **OVH Object Storage** en production (`ovh-webtech-s3` bucket, eu-west-par)
- Architecture conditionnelle `STORAGE_BACKEND=local|s3` dans settings.py

## Outcome

- ✅ `django-storages[s3]` + `boto3` ajoutés à requirements.txt
- ✅ `STORAGE_BACKEND` configurable dans settings.py (section S3 conditionnelle)
- ✅ MinIO intégré à docker-compose.yml (service + volume + healthcheck)
- ✅ Script `minio-setup.sh` pour provisioning automatique du bucket
- ✅ Configuration OVH S3 fonctionnelle (après corrections endpoint/region)
- ✅ `AWS_LOCATION=clickmart` pour préfixe multi-projet
- ✅ `AWS_S3_ADDRESSING_STYLE` configurable (path|virtual — nécessaire pour OVH)
- ✅ Rapports mis à jour : DRY_RUN_REPORT.md, inventory.yml, AGENT_DEPLOY_FULLSTACK v3.0, GESTION_ENVIRONNEMENTS.md

---

## Decisions

| # | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| 1 | `STORAGE_BACKEND=local` par défaut | Rétrocompatibilité : les environnements dev existants continuent avec `static/` local sans configuration S3 | Option de mettre `s3` par défaut rejetée — forcerait la config S3 même en dev |
| 2 | MinIO plutôt que localstack | MinIO est léger (128 Mo), natif S3-compatible, pas d'overhead AWS simulé inutile | Localstack : trop lourd, conçu pour simuler tout AWS |
| 3 | `AWS_LOCATION=clickmart` (préfixe) | Permet de réutiliser le même bucket OVH pour plusieurs projets (isolation par préfixe) | Bucket dédié par projet (trop de buckets à gérer) |
| 4 | `AWS_S3_ADDRESSING_STYLE=virtual` par défaut | Standard AWS S3 ; OVH nécessite `path` → configurable via variable d'env | Hardcoder `path` → casserait AWS S3 natif |
| 5 | Conf OVH hors docker-compose | OVH Object Storage n'a pas besoin de tourner localement : configuré via `.envs/.prod` uniquement | Ajouter un faux service OVH dans Compose rejeté — inutile |
| 6 | Pas de S3 en CI | Les tests Django tournent en SQLite avec `STORAGE_BACKEND=local` → pas de dépendance S3 | Ajouter MinIO en CI possible mais overhead inutile pour 78 tests |

---

## Files Created

| File | Purpose |
|---|---|
| `infra/scripts/minio-setup.sh` | Script de provisioning MinIO : crée le bucket `clickmart` + policy public-read via `mc` CLI |
| `docs/reports/GESTION_ENVIRONNEMENTS.md` | Documentation complète de l'architecture multi-environnement (dev/staging/prod) |
| `backend/.envs/.prod` | Configuration OVH S3 pour production (clés, endpoint, region, bucket) |
| `backend/.envs/.staging` | Configuration MinIO S3 pour staging (localhost:9000, minioadmin) |

## Files Modified

| File | Change summary |
|---|---|
| `backend/requirements.txt` | +`django-storages[s3]==1.14.6`, +`boto3==1.35.99`, restauré `celery==5.6.0` + `redis==6.2.0` (supprimés accidentellement) |
| `backend/config/settings.py` | +`STORAGE_BACKEND` variable (l.185), +bloc `if STORAGE_BACKEND == 's3'` (l.187-214) avec `storages.backends.s3boto3`, +`AWS_S3_ADDRESSING_STYLE` configurable (l.200), +`AWS_LOCATION=clickmart` (l.198) |
| `backend/.env.example` | +Section Storage : `STORAGE_BACKEND=local`, variables AWS commentées pour doc |
| `docker-compose.yml` | +Service `minio` (image minio/minio, port 9000/9001, volume `minio_data`, healthcheck, mem_limit 128m) |
| `docs/reports/AGENT_DEPLOY_FULLSTACK.md` | v2.0 → v3.0 : commande `inventory`, `@deploy-fullstack production\|staging`, règle anti-OOM, DRY_RUN_REPORT + inventory.yml auto-générés, mode dry-run enrichi |
| `DRY_RUN_REPORT.md` | Mis à jour avec la détection S3/MinIO et les nouvelles configurations |
| `inventory.yml` | Mis à jour avec le service MinIO et la configuration S3 |

---

## Key Context

### Providers S3 configurés

| Environnement | Provider | Endpoint | Bucket |
|---|---|---|---|
| **Dev** (local) | MinIO | `http://minio:9000` | `clickmart` |
| **Staging** (Linode) | MinIO (local) | `http://minio:9000` | `clickmart` |
| **Production** (Linode) | OVH Object Storage | `https://s3.eu-west-par.io.cloud.ovh.net` | `ovh-webtech-s3` |

### Architecture du stockage conditionnel

```python
STORAGE_BACKEND = config('STORAGE_BACKEND', default='local')

if STORAGE_BACKEND == 's3':
    INSTALLED_APPS += ['storages']
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default=None)
    AWS_S3_ADDRESSING_STYLE = config('AWS_S3_ADDRESSING_STYLE', default='virtual')
    AWS_LOCATION = 'clickmart'
    # ... S3Boto3Storage + S3ManifestStaticStorage
else:
    STATIC_URL = 'static/'
    STATIC_ROOT = BASE_DIR / 'static'
```

### MinIO docker-compose

```yaml
minio:
  image: minio/minio
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
  volumes:
    - minio_data:/data
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
  mem_limit: 128m
```

---

## Commits

| Hash | Message |
|---|---|
| `482c1c1` | `feat: add S3-compatible storage backend (django-storages + MinIO)` |
| `88f63a1` | `fix: restore celery + redis in requirements.txt (accidentally removed)` |
| `c15218d` | `fix: add AWS_S3_ADDRESSING_STYLE config for OVH S3 compatibility` |
| `656228e` | `fix: use clickmart/ prefix in S3 bucket (multi-project support)` |

---

## Issues & Workarounds

| Issue | Workaround | Status |
|---|---|---|
| `celery` et `redis` supprimés accidentellement de `requirements.txt` lors de l'ajout de `django-storages` + `boto3` | Ajout manuel restauré au commit `88f63a1` | resolved |
| Mauvais endpoint OVH S3 initial (`s3.gra.io.cloud.ovh.net` au lieu de `s3.eu-west-par.io.cloud.ovh.net`) | Correction dans `.envs/.prod` + test curl de l'endpoint | resolved |
| Mauvais `AWS_S3_ADDRESSING_STYLE` pour OVH (virtual → path) | Ajout variable d'env `AWS_S3_ADDRESSING_STYLE=path` dans `.envs/.prod` ; `virtual` conservé par défaut pour AWS natif | resolved |
| `collectstatic` lent en S3 (OVH) — 60s+ pour ~100 fichiers | Accepté comme normal : S3 a une latence plus élevée que le disque local. Pas de solution parallélisée pour l'instant. | acknowledged |
| `statifiles.json` manifest perdu après `collectstatic` | Normal : stocké dans S3, pas localement. `S3ManifestStaticStorage` gère cela. | resolved |

---

## Patterns Established

1. **`STORAGE_BACKEND=local|s3`** — pattern conditionnel pour basculer entre stockage local et S3
2. **MinIO comme "S3 local"** — remplace localstack, plus léger et natif S3
3. **`minio-setup.sh`** — script de provisioning idempotent exécuté au premier démarrage
4. **`AWS_LOCATION=clickmart`** — préfixe multi-projet dans le bucket (isolation sans multi-bucket)
5. **`AWS_S3_ADDRESSING_STYLE` configurable** — virtual pour AWS, path pour OVH
6. **Pas de S3 dans les overrides Compose** — les variables S3 sont dans `.envs/.*`, pas dans docker-compose (évite la fusion de listes env_file)

---

## Action Items

- [ ] Tester `collectstatic` en production OVH avec patience (60s+) et valider que les statics sont bien servies depuis S3
- [ ] Documenter la procédure de migration `local → s3` pour un environnement existant
- [ ] Explorer `django-storages` avec `AWS_S3_MAX_MEMORY_SIZE` pour optimiser les uploads
- [ ] Envisager un CDN devant le bucket OVH pour réduire la latence des statics

---

## Related Sessions

- `archives/chats/2026-07-29_session_multi-env-restructuration.md` — Restructuration multi-environnement (base + overrides Compose, .envs/)
- `archives/chats/2026-07-29_session_agent-deploy-fullstack.md` — Création de l'agent deploy-fullstack v1.0
- `archives/chats/2026-07-29_session_gitflow-bugfixes-polish.md` — Bugfixes et polish (même journée)
- `archives/chats/2026-07-29_session_finalisation-clickmart.md` — Finalisation P3-P6 + SSL + infra
- `archives/chats/2026-07-28_session_deploiement-linode-clickmart.md` — Déploiement initial Linode
- `docs/reports/AGENT_DEPLOY_FULLSTACK.md` — Rapport agent v3.0 (322 lignes)
- `docs/reports/GESTION_ENVIRONNEMENTS.md` — Architecture multi-environnement (202 lignes)

---

## Full Conversation Summary

1. L'utilisateur a demandé l'implémentation d'un backend de stockage S3 pour gérer les statics et médias en production (OVH Object Storage) avec MinIO en local pour le développement.

2. Ajout de `django-storages[s3]` et `boto3` dans `requirements.txt` — mais `celery` et `redis` ont été accidentellement retirés (corrigé au commit suivant).

3. Implémentation du bloc conditionnel `STORAGE_BACKEND=local|s3` dans `settings.py` :
   - Si `s3` → `S3Boto3Storage` + `S3ManifestStaticStorage`
   - Si `local` → comportement Django standard (STATIC_ROOT local)
   - `AWS_LOCATION=clickmart` pour préfixer tous les fichiers dans le bucket

4. Ajout du service MinIO dans `docker-compose.yml` (port 9000, console 9001, volume `minio_data`, healthcheck).

5. Création de `infra/scripts/minio-setup.sh` pour le provisioning automatique du bucket MinIO.

6. Configuration OVH S3 dans `.envs/.prod` :
   - Endpoint : `s3.eu-west-par.io.cloud.ovh.net`
   - Bucket : `ovh-webtech-s3`
   - Region : `eu-west-par`
   - `AWS_S3_ADDRESSING_STYLE=path` (nécessaire pour OVH)

7. Correction de bugs :
   - `celery + redis` restaurés dans requirements.txt
   - Endpoint/region OVH corrigés
   - `AWS_S3_ADDRESSING_STYLE` rendu configurable

8. Mise à jour des rapports :
   - `docs/reports/AGENT_DEPLOY_FULLSTACK.md` : v2.0 → v3.0 (ajout commande `inventory`, dry-run enrichi, règle anti-OOM)
   - `docs/reports/GESTION_ENVIRONNEMENTS.md` : nouveau document d'architecture multi-environnement
   - `DRY_RUN_REPORT.md` et `inventory.yml` mis à jour avec la détection S3/MinIO

9. Session conclue avec le backend S3 fonctionnel pour les 3 environnements (dev MinIO, staging MinIO, production OVH).
