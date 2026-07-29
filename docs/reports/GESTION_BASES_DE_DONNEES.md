# Gestion des Bases de Données — ClickMart

> **Date** : 2026-07-29
> **Version** : 1.0
> **Contexte** : Migration de PostgreSQL local Docker → PostgreSQL distant + dj-database-url

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    DATABASE_URL                          │
│                        │                                 │
│         ┌──────────────┴──────────────┐                  │
│         │                             │                  │
│      Absente                       Présente              │
│         │                             │                  │
│    SQLite locale              PostgreSQL distant         │
│    (dev standalone, CI)       (staging, production)      │
│         │                             │                  │
│    BASE_DIR / 'db.sqlite3'    dj_database_url.parse()   │
│                               conn_max_age=600           │
└─────────────────────────────────────────────────────────┘
```

| Environnement | Moteur | Hôte | Base |
|---|---|---|---|
| Dev standalone | SQLite | Fichier local | `db.sqlite3` |
| CI (GitHub Actions) | SQLite | Fichier local | `db.sqlite3` |
| Staging (Docker) | PostgreSQL | `db` (conteneur local) | `clickmart_staging` |
| Production | PostgreSQL | `49.13.239.42` (distant) | `clickmart` |

---

## Configuration

### settings.py — Simplification radicale

```python
# Avant : 60 lignes (use_sqlite_fallback, is_running_in_docker, psycopg2.connect...)
# Après : 10 lignes

import dj_database_url

DATABASE_URL = config('DATABASE_URL', default='')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

**Avantages** :
- Une seule variable `DATABASE_URL` gère tout
- `conn_max_age=600` → connection pooling (10 minutes)
- SQLite automatique si `DATABASE_URL` vide (CI, dev standalone)
- Format standard 12-factor : `postgres://user:pass@host:port/db?sslmode=require`

### Fichiers d'environnement

#### `.envs/.prod` — Production

```bash
DATABASE_URL=postgres://postgres:<password>@49.13.239.42:5432/clickmart?sslmode=require
```

#### `.envs/.staging` — Staging (PostgreSQL local Docker)

```bash
DATABASE_URL=postgres://postgres:postgres@db:5432/clickmart_staging
```

#### `.env` — Dev standalone

```bash
# Laisser vide → SQLite automatique
# DATABASE_URL=postgres://postgres:postgres@localhost:5432/clickmart
```

---

## Dépendances

```
dj-database-url==3.1.2
psycopg2-binary==2.9.11
```

---

## Serveur PostgreSQL distant

| Propriété | Valeur |
|---|---|
| **Hôte** | `49.13.239.42` |
| **Port** | `5432` |
| **User** | `postgres` |
| **Base** | `clickmart` |
| **SSL** | `require` |
| **Pooling** | `conn_max_age=600` (10 min) |

### Création initiale de la base

```python
import psycopg2
conn = psycopg2.connect(host='49.13.239.42', database='postgres', user='postgres', password='...')
conn.autocommit = True
conn.cursor().execute("CREATE DATABASE clickmart")
```

---

## Serveur Redis distant

| Propriété | Valeur |
|---|---|
| **Hôte** | `49.13.239.42` |
| **Port** | `6379` |
| **User** | `default` |
| **DB Broker** | `0` |
| **DB Results** | `1` |

```bash
CELERY_BROKER_URL=redis://default:<password>@49.13.239.42:6379/0
CELERY_RESULT_BACKEND=redis://default:<password>@49.13.239.42:6379/1
```

---

## Docker Compose — Services désactivés en production

En production, `db`, `redis` et `minio` sont désactivés via `profiles` :

```yaml
# docker-compose.prod.yml
services:
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

Le staging conserve tous les services locaux avec `depends_on: condition: service_healthy`.

---

## Opérations courantes

### Migration : SQLite → PostgreSQL

```bash
# 1. Dump SQLite
python manage.py dumpdata --natural-foreign --natural-primary > db_dump.json

# 2. Configurer DATABASE_URL
DATABASE_URL=postgres://postgres:postgres@localhost:5432/clickmart

# 3. Appliquer les migrations + charger les données
python manage.py migrate
python manage.py loaddata db_dump.json
```

### Reset de la base de données

```bash
# Sur le serveur distant
python manage.py reset_db --noinput  # django-extensions
python manage.py migrate
python manage.py createsuperuser
```

### Backup

Le script `infra/scripts/backup-db.sh` gère les backups :

```bash
pg_dump -h 49.13.239.42 -U postgres -d clickmart | gzip > backup_$(date +%Y%m%d).sql.gz
```

---

## Incidents documentés

### OOM lors du build Docker — 2026-07-29

**Cause** : 9 conteneurs (db + redis + minio inclus) + build Docker = saturation des 961 MiB.

**Fix** : désactiver db/redis/minio en production → 6 conteneurs, 286 MB de marge.

### Import circulaire celery.py — 2026-07-29

**Cause** : fichier `celery.py` parasite dans `/opt/clickmart/backend/` importait `from celery import Celery` en boucle.

**Fix** : supprimer le fichier parasite.

### dj-database-url version inexistante — 2026-07-29

**Cause** : `dj-database-url==2.3.2` n'existe pas (dernière version : 3.1.2).

**Fix** : corriger la version dans requirements.txt.
