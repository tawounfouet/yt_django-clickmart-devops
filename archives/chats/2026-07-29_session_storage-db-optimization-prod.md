# Session: Optimisation Production — Séparation Static/Media, Cloudinary, DB Distante

**Date**: 2026-07-29
**Duration**: ~2h
**Agent(s)**: opencode (implémentation + debug), deploy-fullstack (vérification)
**Phase**: build + deploy + maintain

---

## Intent

Optimiser l'architecture de production ClickMart en cinq volets : (1) séparer strictement le stockage des statics (Nginx local) des médias (provider configurable), (2) intégrer Cloudinary comme backend media de production, (3) migrer PostgreSQL et Redis vers un serveur distant, (4) simplifier radicalement `settings.py` en remplaçant 60 lignes de fallback SQLite par `dj-database-url`, (5) réduire l'empreinte RAM en désactivant les conteneurs inutiles en production.

## Outcome

- ✅ Statics : toujours servis localement par Nginx (`STATIC_ROOT` + `collectstatic`), jamais S3/Cloudinary
- ✅ Media : 3 backends configurables via `MEDIA_STORAGE_BACKEND=local|s3|cloudinary`
- ✅ Cloudinary actif en production (upload testé : 201 Created, fichier sur dsrbll7qc) — OVH S3 conservé en commentaire comme fallback
- ✅ PostgreSQL distant (`49.13.239.42`) configuré via `dj-database-url` au format 12-factor `DATABASE_URL`
- ✅ Redis distant (`49.13.239.42`) pour Celery broker/results
- ✅ `db`, `redis`, `minio` désactivés en prod via `profiles: [disabled]`
- ✅ 9 conteneurs (1 160 MB réservés) → 6 conteneurs (768 MB), 286 MB de marge
- ✅ `settings.py` : `use_sqlite_fallback()` 60 lignes → `dj_database_url` 10 lignes
- ✅ Rapports : `GESTION_STORAGE_BACKEND.md` v2, `GESTION_BASES_DE_DONNEES.md` nouveau

---

## Decisions

| # | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| 1 | Static = toujours local (Nginx), Media = configurable | Évite `collectstatic` lent vers S3 (163 fichiers → 60-90s), supprime le risque de latence pour les assets critiques. Seuls les uploads utilisateurs justifient un backend distant. | Tout sur S3 (rejeté : `collectstatic` trop lent, `STATIC_ROOT` vide oblige S3 pour les statics Django) |
| 2 | `DEFAULT_FILE_STORAGE` au lieu du dict `STORAGES` | `STORAGES['default']` contrôle à la fois static et media si mal configuré. `DEFAULT_FILE_STORAGE` ne touche que les uploads — plus sûr. | `STORAGES` dict (rejeté : confusion possible static/media) |
| 3 | Cloudinary en production, OVH S3 en fallback | Cloudinary = CDN global + transformations d'image intégrées. OVH S3 = fournisseur européen, déjà testé fonctionnel, gardé en commentaire pour switch rapide. | Rester sur OVH S3 (rejeté car pas de CDN/transformations), AWS S3 (rejeté car hors Europe) |
| 4 | `dj-database-url` pour la config DB | Standard 12-factor, 10 lignes au lieu de 60. SQLite automatique si `DATABASE_URL` vide. `conn_max_age=600` pour connection pooling. | Garder `use_sqlite_fallback()` (rejeté : code mort complexe, `is_running_in_docker`, `psycopg2.connect` avec timeout) |
| 5 | PostgreSQL/Redis distants (49.13.239.42) | Réduit la charge Docker sur le Linode (961 MiB RAM), évite les conflits de ressources build-vs-runtime, facilite les backups centralisés. | Tout local Docker (rejeté : OOM fréquents, 9 conteneurs sur 961 MiB) |
| 6 | `profiles: [disabled]` dans docker-compose.prod.yml | Désactive les conteneurs locaux sans modifier le fichier de base. Élégant et réversible. | Supprimer les services de la base (rejeté : casse staging qui en a besoin), `docker compose up backend frontend nginx certbot` (rejeté : verbeux, fragile) |

---

## Files Created

| File | Purpose |
|---|---|
| `docs/reports/GESTION_BASES_DE_DONNEES.md` | Documentation complète de la stratégie DB (dj-database-url, SQLite fallback, PostgreSQL distant, migration, backup, incidents) |

## Files Modified

| File | Change summary |
|---|---|
| `backend/config/settings.py` | 3 refactors : (1) `use_sqlite_fallback()` 60 lignes → `dj_database_url` 10 lignes, (2) static/media séparés (`STATIC_URL`/`STATIC_ROOT` fixes, `MEDIA_STORAGE_BACKEND` configurable), (3) `STORAGES` dict → `DEFAULT_FILE_STORAGE` |
| `backend/requirements.txt` | +`dj-database-url==3.1.2` et +`django-cloudinary-storage==0.3.0` (version 2.3.2 corrigée → 3.1.2 après erreur) |
| `backend/.env.example` | `POSTGRES_*` + `DB_*` → `DATABASE_URL`, `STORAGE_BACKEND` → `MEDIA_STORAGE_BACKEND`, ajout commentaires Cloudinary |
| `docker-compose.yml` | Retrait des 3 blocs `depends_on` (3× backend, celery-worker, celery-beat = 9 lignes) — dépendances déplacées dans les overrides |
| `docker-compose.prod.yml` | `db`, `redis`, `minio` → `profiles: [disabled]` (3 blocs), `env_file` conservé pour backend |
| `docker-compose.staging.yml` | Ajout `depends_on: condition: service_healthy` sur `backend`, `celery-worker`, `celery-beat` (3× db + redis = 6 directives) |
| `backend/.envs/.prod` | `DATABASE_URL=postgres://...@49.13.239.42:5432/clickmart?sslmode=require`, Cloudinary config actif, OVH S3 en commentaire |
| `backend/.envs/.local` | `DATABASE_URL` aligné, `MEDIA_STORAGE_BACKEND=local` |
| `backend/.envs/.staging` | `DATABASE_URL=postgres://...@db:5432/clickmart_staging`, `MEDIA_STORAGE_BACKEND=s3` (MinIO) |
| `backend/.env` | Dev standalone : `DATABASE_URL` vide (→ SQLite), `MEDIA_STORAGE_BACKEND=local` |
| `docs/reports/GESTION_STORAGE_BACKEND.md` | v1 → v2 : ajout Cloudinary, séparation static/media, incident `double https://`, table providers supportés |
| `DRY_RUN_REPORT.md` | Mise à jour 16h15 : RAM recalculée, services distants documentés |
| `inventory.yml` | Mise à jour : specs RAM, services distants, nouvelle architecture DB |

---

## Key Context

- **Linode 172.239.20.14** : 961 MiB RAM, 25 GB disque. La marge est critique — chaque conteneur compte.
- **Serveur distant 49.13.239.42** : héberge PostgreSQL (port 5432, SSL required) + Redis (port 6379, auth password). Même fournisseur que le VPS web.
- **`conn_max_age=600`** : 10 minutes de connection pooling PostgreSQL (vs. nouvelle connexion par requête).
- **Cloudinary `dsrbll7qc`** : cloud name, API key/secret configurés. Upload testé avec succès via `curl -X POST /api/v1/media/images/`.
- **OVH S3** : endpoint `s3.eu-west-par.io.cloud.ovh.net`, bucket `ovh-webtech-s3`, prefix `clickmart/`. Conservé en commentaire dans `.envs/.prod` pour fallback instantané.
- **`depends_on` déplacé** : base compose n'a plus de dépendances → chaque override gère les siennes. Staging garde les healthchecks, prod n'en a pas besoin (services distants).
- **Profiles Docker** : mécanisme natif pour conditionner les services. `profiles: [disabled]` = le service n'est jamais lancé sauf invocation explicite avec `--profile disabled`.
- **Risque OOM éliminé** : 1 160 MB réservés (mem_limits) sur 961 MB physiques → OOM garanti. 768 MB sur 961 MB = 193 MB de marge opérationnelle.

---

## Commands Run

| Command | Purpose | Result |
|---|---|---|
| `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` | Redéploiement prod après migration DB distante | 6/6 conteneurs healthy |
| `docker compose ps` | Vérifier les conteneurs actifs en prod | backend, celery-worker, celery-beat, frontend, nginx, certbot (db/redis/minio absents) |
| `curl -X POST https://webtech-dev.info/api/v1/media/images/ -F "file=@test.jpg"` | Tester upload vers Cloudinary | 201 Created, URL Cloudinary dans la réponse |
| `python manage.py migrate` (via SSH Linode) | Appliquer migrations sur PostgreSQL distant | Succès, tables créées sur 49.13.239.42 |
| `docker compose logs backend \| grep -i "cloudinary\|storage\|database"` | Vérifier logs backend après déploiement | Cloudinary Storage utilisé, PostgreSQL connecté |

---

## Patterns Established

- **12-factor DATABASE_URL** : format unique `postgres://user:pass@host:port/db?sslmode=require` pour toutes les configs DB
- **Static toujours local** : règle inviolable — `STATIC_ROOT` et `STATIC_URL` sont toujours filesystem, `collectstatic` ne touche jamais au stockage distant
- **`DEFAULT_FILE_STORAGE` vs `STORAGES`** : préférer `DEFAULT_FILE_STORAGE` pour le stockage media (ne contrôle que les uploads), `STORAGES` dict réservé aux cas où static + media doivent être sur le même backend
- **Fallback en commentaire** : plutôt que supprimer une config fonctionnelle, la commenter avec `# --- Alternative ---` permet un switch rapide sans consulter la doc
- **`depends_on` dans les overrides, pas la base** : la base compose définit la topologie statique, les overrides ajoutent les contraintes de démarrage propres à chaque environnement

---

## Issues & Workarounds

| Issue | Workaround | Status |
|---|---|---|
| `dj-database-url==2.3.2` inexistante → `pip install` échoue | Corrigé en `3.1.2` (dernière version stable). Commit `e999c5c`. | resolved |
| `celery + redis` supprimés accidentellement de `requirements.txt` (édition avait remplacé les lignes au lieu d'ajouter) | Restauré manuellement. Commit antérieur `88f63a1`. | resolved |
| Double `https://` dans `MEDIA_URL` S3 : `f'https://{AWS_S3_ENDPOINT_URL}/...'` alors que l'endpoint OVH contient déjà `https://` | `f'{AWS_S3_ENDPOINT_URL}/...'` sans préfixe. Commit `a313945`. | resolved |
| `collectstatic` lent vers S3 (60-90s pour 163 fichiers) | Résolu par la séparation static/media : `collectstatic` reste local → quasi-instantané. | resolved |
| Fichier `celery.py` parasite dans `/opt/clickmart/backend/` causant un import circulaire | Supprimé manuellement sur le serveur. | resolved |
| OOM lors du build Docker (9 conteneurs + build = saturation 961 MiB) | db/redis/minio désactivés en prod → 6 conteneurs, 768 MB max. | resolved |

---

## Action Items

- [ ] Monitorer la RAM Linode sur 48h avec les 6 conteneurs (vérifier qu'aucun OOM ne survient)
- [ ] Configurer un backup automatique du PostgreSQL distant (script `backup-db.sh` à adapter pour hôte distant)
- [ ] Tester le fallback OVH S3 en décommentant la config dans `.envs/.prod` et en redéployant
- [ ] Documenter la procédure de migration Cloudinary → OVH S3 (et vice-versa) dans `GESTION_STORAGE_BACKEND.md`
- [ ] Ajouter un healthcheck HTTP pour les services distants (PostgreSQL + Redis) dans le backend
- [ ] Mettre à jour `inventory.yml` avec les nouvelles valeurs RAM (6 conteneurs, 768 MB) — actuellement encore à 8 conteneurs/1032 MiB

---

## Related Sessions

- `archives/chats/2026-07-29_session_s3-storage-backend.md` — Implémentation initiale du storage S3 (MinIO + OVH), `STORAGE_BACKEND=local|s3`
- `archives/chats/2026-07-29_session_media-apps-architecture.md` — Apps media modulaires (DRF + Celery), upload testé sur OVH S3
- `archives/chats/2026-07-29_session_multi-env-restructuration.md` — Split docker-compose en base + overrides, `.env` dans `backend/.envs/`
- `archives/chats/2026-07-29_session_finalisation-clickmart.md` — Finalisation globale (SSL, CI/CD, P3-P6)
- `archives/chats/2026-07-29_session_agent-deploy-fullstack.md` — Agent de déploiement fullstack (utilisé pour vérifier l'infra)

---

## Full Conversation Summary

1. La session a démarré sur le constat que le `STORAGE_BACKEND` unique contrôlait à la fois statics et media — problématique car `collectstatic` vers S3 prenait 60-90s pour 163 fichiers, et les statics n'ont pas besoin d'être distants.

2. **Refactor Static/Media** : `STORAGE_BACKEND` split en `STATIC_*` (fixe, local) + `MEDIA_STORAGE_BACKEND` (configurable). `DEFAULT_FILE_STORAGE` utilisé au lieu du dict `STORAGES` pour éviter toute confusion.

3. **Intégration Cloudinary** : `django-cloudinary-storage==0.3.0` ajouté à `requirements.txt`, configuré dans `settings.py` comme troisième branche de `MEDIA_STORAGE_BACKEND`. Upload testé en production → 201 Created, fichier visible sur le dashboard Cloudinary (`dsrbll7qc`). OVH S3 conservé en commentaire comme fallback dans `.envs/.prod`.

4. **Migration services distants** : PostgreSQL et Redis migrés vers `49.13.239.42`. `dj-database-url` remplace `use_sqlite_fallback()` (60 lignes → 10). `DATABASE_URL` vide → SQLite automatique (dev standalone, CI). `CELERY_BROKER_URL` pointe vers Redis distant.

5. **Optimisation RAM** : `db`, `redis`, `minio` désactivés en production via `profiles: [disabled]` dans `docker-compose.prod.yml`. `depends_on` retiré de `docker-compose.yml` (base) et ajouté uniquement dans `docker-compose.staging.yml`. Résultat : 9 conteneurs (1 160 MB) → 6 conteneurs (768 MB), 286 MB de marge.

6. **Rapports mis à jour** : `GESTION_STORAGE_BACKEND.md` v2 (ajout Cloudinary, séparation static/media, table providers, procédures de migration), `GESTION_BASES_DE_DONNEES.md` créé (architecture DB, dj-database-url, serveur distant, Redis, procédures), `DRY_RUN_REPORT.md` et `inventory.yml` synchronisés.

7. **Corrections d'incidents** : version `dj-database-url` corrigée (2.3.2 → 3.1.2), double `https://` dans MEDIA_URL S3, fichier celery.py parasite supprimé, dépendances celery+redis restaurées dans requirements.txt.

6 commits atomiques poussés sur `main` : `66568d0` → `a313945` → `362f4b0` → `e999c5c` → `8d9db2d` → `ab38374` → `b43245b`.
