# Session: Architecture Modulaire des Apps Media — DRF + Celery + S3

**Date**: 2026-07-29
**Duration**: ~2h30 (estimé)
**Agent(s)**: opencode (implémentation + debug), deploy-fullstack (dry-run)
**Phase**: build + deploy

---

## Intent

Créer une architecture modulaire de gestion de médias pour ClickMart avec 5 apps Django séparées par type de média, des endpoints DRF RESTful, un traitement asynchrone via Celery, le tout stocké sur OVH S3 en production et MinIO en staging.

## Outcome

- ✅ 5 apps modulaires créées sous `backend/apps/` : `core` (AbstractMedia), `images` (full), `audio`, `video`, `documents` (skeletons)
- ✅ 4 endpoints DRF : `/api/v1/media/images/`, `/audio/`, `/video/`, `/documents/`
- ✅ `apps/images/` entièrement implémenté : Pillow processors, Celery task, post_save signal
- ✅ `apps/audio/`, `video/`, `documents/` en skeletons avec API + Celery tasks stubs
- ✅ Renommage `MEDIA_ROOT` : `media/` → `uploads/` (évite conflit de nom avec les apps media)
- ✅ Toute la stack mise à jour : docker-compose (×3), nginx (×2), .gitignore
- ✅ `sys.path.insert` dans manage.py, wsgi.py, celery.py pour résolution du module `apps/`
- ✅ Upload d'image testé en production : **201 Created**, fichier présent sur OVH S3
- ✅ Bucket S3 nettoyé : 327 anciens objets supprimés, seul `clickmart/` subsiste
- ✅ Rapport `docs/reports/GESTION_STORAGE_BACKEND.md` créé

---

## Decisions

| # | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| 1 | Placer toutes les apps media dans `backend/apps/` plutôt que `backend/` racine | Séparation claire des apps media des apps métier (users, products, carts, orders) | Garder à la racine → pollution du namespace |
| 2 | Utiliser `sys.path.insert` dans manage.py, wsgi.py, celery.py | Évite les imports `from apps.core.models import...` ; permet `from core.models import...` | Package namespace, `sys.path` dans settings, PYTHONPATH Docker |
| 3 | Renommer `MEDIA_ROOT` de `media/` à `uploads/` | `media` est ambigu : nom d'apps + chemin physique. `uploads` est explicite | Garder `media`, utiliser un sous-dossier `media_files/` |
| 4 | Images en implémentation FULL, audio/video/documents en skeletons | Prioriser le cas d'usage principal (images produit) ; les autres types attendront l'installation de leurs dépendances (pydub, ffmpeg, pypdf) | Tout implémenter d'un coup → bloqué par dépendances lourdes |
| 5 | `file_size` et `mime_type` rendus `null=True` dans la migration 0002 | L'upload S3 rend le fichier indisponible sur le filesystem local au moment du post_save ; ces champs sont remplis par la Celery task après coup | Pré-remplir dans le modèle → impossible avec S3 (pas de .path local) |
| 6 | `AWS_LOCATION=clickmart` plutôt que `static` | Permet de multiples projets dans le même bucket OVH (préfixe par projet) | `static` → confusion avec static files |
| 7 | Nettoyage du bucket OVH (327 objets racine supprimés) | Supprimer les artefacts de l'ancienne config où `AWS_LOCATION=static` remplissait la racine | Laisser les objets → pollution, coût de stockage inutile |

---

## Files Created

### Apps media (19 fichiers sous `backend/apps/`)

| File | Purpose |
|---|---|
| `backend/apps/__init__.py` | Package apps |
| `backend/apps/core/__init__.py` | Package core |
| `backend/apps/core/models.py` | `AbstractMedia` — UUID, file, size, mime, sha256, uploaded_at |
| `backend/apps/images/__init__.py` | Package images |
| `backend/apps/images/apps.py` | `ImagesConfig` avec `ready()` → import signals |
| `backend/apps/images/models.py` | `Image(AbstractMedia)` — width, height, thumbnail, exif_data |
| `backend/apps/images/processors.py` | Pillow : extract_metadata, generate_thumbnail, resize_to_fit, convert_to_webp |
| `backend/apps/images/signals.py` | `post_save` → `process_image.delay()` |
| `backend/apps/images/tasks.py` | Celery task : SHA256 + metadata Pillow + thumbnail |
| `backend/apps/images/api/__init__.py` | Package API images |
| `backend/apps/images/api/serializers.py` | `ImageSerializer` avec read_only_fields |
| `backend/apps/images/api/views.py` | `ImageViewSet` — override `create()` pour `original_filename` |
| `backend/apps/images/api/urls.py` | Router DRF → `/images/` |
| `backend/apps/images/migrations/0001_initial.py` | Migration initiale Image |
| `backend/apps/images/migrations/0002_alter_*.py` | Nullable file_size + mime_type |
| `backend/apps/audio/models.py` | `Audio(AbstractMedia)` — duration, sample_rate, bitrate, channels |
| `backend/apps/audio/processors.py` | Stubs pydub (NotImplementedError) |
| `backend/apps/audio/tasks.py` | Celery task : SHA256 + file_size (metadata TODO) |
| `backend/apps/audio/api/{serializers,views,urls}.py` | DRF ViewSet + router |
| `backend/apps/audio/migrations/0001_initial.py` + `0002_*.py` | Migration initiale Audio + nullable fix |
| `backend/apps/video/models.py` | `Video(AbstractMedia)` — duration, width, height, fps, codec, thumbnail |
| `backend/apps/video/processors.py` | Stubs ffmpeg-python (NotImplementedError) |
| `backend/apps/video/tasks.py` | Celery task : SHA256 + file_size (metadata + thumbnail TODO) |
| `backend/apps/video/api/{serializers,views,urls}.py` | DRF ViewSet + router |
| `backend/apps/video/migrations/0001_initial.py` + `0002_*.py` | Migration initiale Video + nullable fix |
| `backend/apps/documents/models.py` | `Document(AbstractMedia)` — page_count, author, is_encrypted |
| `backend/apps/documents/processors.py` | Stubs pypdf/pdf2image (NotImplementedError) |
| `backend/apps/documents/tasks.py` | Celery task : SHA256 + file_size (metadata TODO) |
| `backend/apps/documents/api/{serializers,views,urls}.py` | DRF ViewSet + router |
| `backend/apps/documents/migrations/0001_initial.py` + `0002_*.py` | Migration initiale Document + nullable fix |

### Rapports

| File | Purpose |
|---|---|
| `docs/reports/GESTION_STORAGE_BACKEND.md` | Architecture S3 multi-provider, config Django, MinIO local, OVH prod, troubleshooting |

---

## Files Modified

| File | Change summary |
|---|---|
| `backend/manage.py` | + `sys.path.insert` pour `apps/` |
| `backend/config/wsgi.py` | + `sys.path.insert` pour `apps/` |
| `backend/config/celery.py` | + `sys.path.insert` pour `apps/` |
| `backend/config/settings.py` | + `INSTALLED_APPS` (core, images, audio, video, documents) ; renommé MEDIA_ROOT `media`→`uploads` ; `AWS_LOCATION` → `clickmart` ; + `AWS_S3_ADDRESSING_STYLE` |
| `backend/config/urls.py` | + 4 routes API media : `api/v1/media/{images,audio,video,documents}/` |
| `backend/requirements.txt` | + `django-storages[s3]` + `boto3` |
| `docker-compose.yml` | Volume `media`→`uploads` |
| `docker-compose.prod.yml` | Volume `media`→`uploads` |
| `docker-compose.staging.yml` | Volume `media`→`uploads` |
| `infra/nginx/prod.conf` | `location /media/` → `location /uploads/` |
| `infra/nginx/staging.conf` | `location /media/` → `location /uploads/` |
| `.gitignore` | `media` → `uploads` |
| `docs/reports/AGENT_DEPLOY_FULLSTACK.md` | v2.0 → v3.0 (ajout du support S3, MinIO, media apps) |

---

## Key Context

- **Structure** : `backend/apps/` contient 5 apps media + `core/` (modèle abstrait). Les apps métier (users, products, carts, orders) restent à la racine `backend/`.
- **sys.path** : Le `sys.path.insert(0, str(BASE_DIR / 'apps'))` est nécessaire dans manage.py, wsgi.py, **et** celery.py car Celery a son propre processus et ne lit pas manage.py.
- **MEDIA_ROOT `uploads/`** : Le nom `media` posait problème car `media` est aussi le nom d'un dossier d'apps. `uploads/` est sans ambiguïté.
- **file_size/mime_type nullable** : Remplis par la Celery task après l'upload S3. Sans `null=True`, l'upload échoue car les champs sont requis au moment du save initial.
- **S3 OVH** : `AWS_S3_ADDRESSING_STYLE=virtual` obligatoire pour OVH (ne supporte pas le path-style). `AWS_LOCATION=clickmart` préfixe tous les objets.
- **Bucket nettoyé** : `aws s3 rm s3://ovh-webtech-s3 --recursive --exclude "clickmart/*"` → 327 objets supprimés.
- **Image upload testé en prod** : `POST /api/v1/media/images/` → 201 Created → fichier `clickmart/uploads/2026/07/29/<uuid>.jpg` présent sur OVH S3. Thumbnail généré par Celery.
- **Dépendances skeleton** : `pydub` (audio), `ffmpeg-python` + ffmpeg système (video), `pypdf` + `pdf2image` (documents) — non installées, stubs `NotImplementedError`.

---

## Commands Run

| Command | Purpose | Result |
|---|---|---|
| `python manage.py makemigrations images audio video documents` | Générer migrations initiales pour les 4 apps | 4× 0001_initial.py créés |
| `python manage.py makemigrations images audio video documents` | Migration 0002 (nullable fix) | 4× 0002_alter_*.py créés |
| `docker compose -f docker-compose.prod.yml up -d --build` | Déploiement production | Succès, image upload testé |
| `aws s3 ls s3://ovh-webtech-s3/ --recursive --endpoint-url https://s3.eu-west-par.io.cloud.ovh.net` | Lister objets bucket OVH | 327 objets racine + clickmart/ |
| `aws s3 rm s3://ovh-webtech-s3/ --recursive --exclude "clickmart/*" --endpoint-url ...` | Nettoyer racine bucket | 327 objets supprimés |
| `curl -X POST https://webtech-dev.info/api/v1/media/images/ -F "file=@test.jpg" -F "title=Test"` | Test upload production | 201 Created ✅ |

---

## Patterns Established

- **App media = `models.py` + `processors.py` + `tasks.py` + `api/` + `signals.py` (optionnel)** — structure canonique pour chaque type de média
- **`AbstractMedia` dans `core`** — modèle abstrait partagé par tous les types de médias (DRY)
- **`sys.path.insert` dans 3 fichiers** — manage.py, wsgi.py, celery.py ; tout oubli casse l'app
- **Skeletons avec `NotImplementedError`** — les apps non prioritaires ont des stubs documentés prêts à être activés
- **`media/` → `uploads/`** — convention de nommage physique distincte du nom logique des apps
- **Celery task pull-based** — la task lit le fichier depuis S3 après l'upload (ne présuppose pas un chemin local)

---

## Issues & Workarounds

| Issue | Workaround | Status |
|---|---|---|
| `file_size` et `mime_type` required → échec upload S3 (pas de .path local) | Rendre nullable (`null=True, blank=True`) en 0002, remplissage par Celery task | resolved |
| `sys.path` manquant dans celery.py → `ModuleNotFoundError: No module named 'core'` | Ajouté `sys.path.insert` dans celery.py | resolved |
| 327 objets à la racine du bucket S3 (ancienne config `AWS_LOCATION=static`) | `aws s3 rm --exclude "clickmart/*"` | resolved |
| OVH S3 rejette le path-style addressing | `AWS_S3_ADDRESSING_STYLE=virtual` dans les .env | resolved |

---

## Action Items

- [ ] Installer `pydub` et implémenter les vrais processors audio
- [ ] Installer `ffmpeg-python` + ffmpeg système et implémenter les vrais processors video
- [ ] Installer `pypdf` + `pdf2image` et implémenter les vrais processors documents
- [ ] Ajouter des tests unitaires pour les processors images (Pillow)
- [ ] Ajouter des tests d'intégration API pour les 4 endpoints media
- [ ] Ajouter la pagination et le filtrage sur les ViewSets media
- [ ] Documenter l'API media dans le Swagger (drf-spectacular)

---

## Related Sessions

- `archives/chats/2026-07-29_session_s3-storage-backend.md` — Implémentation S3 (django-storages + MinIO + OVH) — prérequis direct de cette session
- `archives/chats/2026-07-29_session_multi-env-restructuration.md` — Restructuration Docker Compose multi-environnement — contexte infra
- `archives/chats/2026-07-29_session_agent-deploy-fullstack.md` — Agent de déploiement fullstack v3.0 — mis à jour pour supporter S3 + MinIO

---

## Full Conversation Summary

1. **Création de l'architecture modulaire** : L'utilisateur a demandé une séparation propre des apps media par type (images, audio, vidéo, documents) sous `backend/apps/`, avec un modèle abstrait `AbstractMedia` dans `apps/core/`.

2. **Implémentation d'apps/images/** : Modèle `Image` avec champs spécifiques (width, height, thumbnail, exif_data), processors Pillow (extract_metadata, generate_thumbnail, resize_to_fit, convert_to_webp), Celery task asynchrone, et signal post_save déclenchant le processing. ImageViewSet avec override de `create()` pour capturer `original_filename`.

3. **Skeletons audio/video/documents** : Mêmes patterns que images mais avec stubs NotImplementedError dans les processors. Les Celery tasks calculent SHA256 + file_size uniquement pour l'instant.

4. **sys.path.insert** : Ajouté dans manage.py, wsgi.py, et celery.py pour que `from core.models import AbstractMedia` fonctionne sans le préfixe `apps.`.

5. **Renommage media → uploads** : MEDIA_ROOT, MEDIA_URL, volumes docker-compose, locations nginx, et .gitignore tous mis à jour. Raison : `media` est ambigu (nom d'apps + chemin physique).

6. **Problème file_size/mime_type nullable** : L'upload S3 empêche l'accès à `file.path` au moment du post_save. Correction par migration 0002 (nullable) + remplissage différé dans la Celery task.

7. **Nettoyage bucket OVH** : 327 objets à la racine du bucket (ancienne config `AWS_LOCATION=static`) supprimés. `AWS_LOCATION` définitivement fixé à `clickmart`.

8. **Test production** : Upload d'image via `POST /api/v1/media/images/` → 201 Created, fichier + thumbnail présents sur OVH S3 dans `clickmart/uploads/2026/07/29/`.

9. **Documentation** : Rapport `docs/reports/GESTION_STORAGE_BACKEND.md` créé (architecture S3, config Django, MinIO, OVH, troubleshooting). Agent deploy-fullstack mis à jour en v3.0.
