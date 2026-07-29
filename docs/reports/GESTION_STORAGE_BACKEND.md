# Gestion du Storage Backend — ClickMart

> **Date** : 2026-07-29
> **Version** : 2.0
> **Contexte** : Stockage media multi-provider (local / S3 / Cloudinary), statics toujours servis par Nginx

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     FICHIERS CLICKMART                     │
│                          │                                │
│         ┌────────────────┴────────────────┐               │
│         │                                 │               │
│      STATIC                              MEDIA            │
│   (CSS, JS, fonts)                  (user uploads)        │
│         │                                 │               │
│    Nginx (local)              MEDIA_STORAGE_BACKEND       │
│    /app/static/               local | s3 | cloudinary     │
│         │                          │                      │
│    Toujours fixe          ┌───────┼───────┐               │
│                           │       │       │               │
│                         local    s3   cloudinary          │
│                      (filesystem) │  (dsrbll7qc)          │
│                           ┌───────┴───────┐               │
│                         MinIO         OVH S3              │
│                       (staging)      (fallback)           │
└──────────────────────────────────────────────────────────┘
```

**Principe** : les fichiers statiques (build React, CSS admin Django) sont toujours servis par Nginx depuis le disque local — rapide, zéro latence. Seuls les uploads utilisateurs (images, audio, vidéos, documents) passent par un backend configurable.

| Environnement | Media Backend | Provider |
|---|---|---|
| Dev standalone | `local` | `/app/uploads/` |
| Dev Docker | `local` | `/app/uploads/` |
| Staging | `s3` | MinIO (Docker) |
| Production | `cloudinary` | Cloudinary (dsrbll7qc) |
| Fallback prod | `s3` | OVH Object Storage |

---

## Configuration Django

```python
# backend/config/settings.py

# Static = ALWAYS local, served by Nginx
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'static'

# Media = configurable
MEDIA_STORAGE_BACKEND = config('MEDIA_STORAGE_BACKEND', default='local')

if MEDIA_STORAGE_BACKEND == 's3':
    INSTALLED_APPS += ['storages']
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default=None)
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

elif MEDIA_STORAGE_BACKEND == 'cloudinary':
    INSTALLED_APPS += ['cloudinary_storage', 'cloudinary']
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
        'API_KEY': config('CLOUDINARY_API_KEY'),
        'API_SECRET': config('CLOUDINARY_API_SECRET'),
    }
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

else:
    MEDIA_URL = "/uploads/"
    MEDIA_ROOT = BASE_DIR / "uploads"
```

**Clé** : `DEFAULT_FILE_STORAGE` ne contrôle que les uploads. `collectstatic` utilise toujours `STATIC_ROOT` local → Nginx.

---

## Fichiers d'environnement

### `.envs/.local` — Dev Docker

```bash
MEDIA_STORAGE_BACKEND=local
# Cloudinary (alternative)
# MEDIA_STORAGE_BACKEND=cloudinary
# CLOUDINARY_CLOUD_NAME=dsrbll7qc
```

### `.envs/.staging` — MinIO

```bash
MEDIA_STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_STORAGE_BUCKET_NAME=clickmart-staging
AWS_S3_ENDPOINT_URL=http://minio:9000
```

### `.envs/.prod` — Cloudinary (actif) + OVH S3 (fallback commenté)

```bash
# --- Actif ---
MEDIA_STORAGE_BACKEND=cloudinary
CLOUDINARY_CLOUD_NAME=dsrbll7qc
CLOUDINARY_API_KEY=changeme
CLOUDINARY_API_SECRET=changeme

# --- Alternative : OVH S3 ---
# MEDIA_STORAGE_BACKEND=s3
# AWS_ACCESS_KEY_ID=changeme
# AWS_SECRET_ACCESS_KEY=changeme
# AWS_STORAGE_BUCKET_NAME=ovh-webtech-s3
# AWS_S3_ENDPOINT_URL=https://s3.eu-west-par.io.cloud.ovh.net
# AWS_S3_REGION_NAME=eu-west-par
```

### `.env` — Dev standalone (sans Docker)

```bash
MEDIA_STORAGE_BACKEND=local
# MEDIA_STORAGE_BACKEND=cloudinary
# CLOUDINARY_CLOUD_NAME=dsrbll7qc
```

---

## Changement de provider

Le switch se fait en modifiant `MEDIA_STORAGE_BACKEND` dans le `.env` :

| Pour passer à... | Modifier |
|---|---|
| **Local** | `MEDIA_STORAGE_BACKEND=local` |
| **OVH S3** | Décommenter les 6 lignes S3, commenter Cloudinary |
| **Cloudinary** | Décommenter les 4 lignes Cloudinary, commenter S3 |
| **AWS S3** | Changer `AWS_S3_ENDPOINT_URL` et credentials |
| **Scaleway** | `AWS_S3_ENDPOINT_URL=https://s3.fr-par.scw.cloud` |

Aucun changement de code nécessaire. Redéployer le backend : `docker compose up -d --build backend`.

---

## Providers supportés

| Provider | `MEDIA_STORAGE_BACKEND` | Config |
|---|---|---|
| **Local** | `local` | Rien |
| **Cloudinary** | `cloudinary` | `CLOUDINARY_CLOUD_NAME`, `_API_KEY`, `_API_SECRET` |
| **OVH S3** | `s3` | `AWS_*` + endpoint spécifique |
| **AWS S3** | `s3` | `AWS_*` (endpoint par défaut) |
| **MinIO** | `s3` | `AWS_*` + `AWS_S3_ENDPOINT_URL=http://minio:9000` |
| **Scaleway** | `s3` | `AWS_*` + endpoint Scaleway |
| **IONOS S3** | `s3` | `AWS_*` + endpoint IONOS |
| **Hetzner** | `s3` | `AWS_*` + endpoint Hetzner |
| **Backblaze B2** | `s3` | `AWS_*` + endpoint B2 |
| **DigitalOcean** | `s3` | `AWS_*` + endpoint DO |

---

## Dépendances

```
django-storages[s3]==1.14.6    # S3-compatible
boto3==1.35.99                  # AWS SDK
django-cloudinary-storage==0.3.0  # Cloudinary
```

---

## Opérations courantes

### Migrer de S3 → Cloudinary

```bash
# 1. Commenter les lignes AWS_*, décommenter Cloudinary dans .envs/.prod
# 2. Redéployer
docker compose up -d --build backend

# 3. Les nouveaux uploads vont sur Cloudinary
# 4. Les anciens fichiers S3 restent accessibles (URLs stockées en base)
```

### Migrer les médias d'un provider à l'autre

```bash
docker compose exec backend python manage.py shell -c "
from images.models import Image
from django.core.files.base import ContentFile
import requests

for img in Image.objects.all():
    if img.file:
        data = requests.get(img.file.url).content
        img.file.save(img.original_filename, ContentFile(data))
        print(f'Migrated {img.id}')
"
```

---

## Incidents documentés

### celery + redis supprimés — 2026-07-29
**Cause** : édition de `requirements.txt` a remplacé les lignes au lieu d'ajouter. **Fix** : restaurer les lignes.

### Mauvais endpoint OVH — 2026-07-29
**Cause** : endpoint `s3.gra.io.cloud.ovh.net` au lieu de `s3.eu-west-par.io.cloud.ovh.net`. **Fix** : utiliser l'endpoint affiché dans l'interface OVH.

### collectstatic lent vers S3 — 2026-07-29
**Cause** : 163 fichiers à uploader → 60-90s. **Fix** : supprimé par la séparation static/media (collectstatic reste local).

### double https:// dans MEDIA_URL — 2026-07-29
**Cause** : `f'https://{AWS_S3_ENDPOINT_URL}/...'` alors que l'endpoint contient déjà `https://`. **Fix** : `f'{AWS_S3_ENDPOINT_URL}/...'`.
