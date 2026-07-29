# Architecture — ClickMart v2.0

> Vue d'ensemble de l'architecture, des flux de données et des décisions de conception.
> Dernière mise à jour : 2026-07-29

---

## 1. Diagramme de déploiement

```
┌───────────┐     ┌──────────────────────────────────────────────────────┐
│ Client    │────▶│  Nginx (ports 80/443)                                │
│ Browser   │     │  reverse proxy + SSL termination + static files      │
└───────────┘     └──────┬──────────────────────┬────────────────────────┘
                         │                      │
                         ▼                      ▼
              ┌──────────────────┐   ┌───────────────────────────────────┐
              │  Frontend        │   │  Backend                          │
              │  ghcr.io image   │   │  ghcr.io image                   │
              │  React 19 + Vite │   │  Gunicorn × 3 + DRF 3.16         │
              └──────────────────┘   └──────────┬────────────────────────┘
                                                │
                            ┌───────────────────┼───────────────────┐
                            │                   │                   │
                            ▼                   ▼                   ▼
                   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
                   │  PostgreSQL  │   │  Redis       │   │  Cloudinary  │
                   │  49.13.239.42│   │  49.13.239.42│   │  dsrbll7qc   │
                   │  (distant)   │   │  (distant)   │   │  (media)     │
                   └──────────────┘   └──────────────┘   └──────────────┘
                            │                   │
                            ▼                   ▼
                   ┌──────────────┐   ┌──────────────┐
                   │ Celery Worker│   │ Celery Beat  │
                   │ (async tasks)│   │ (scheduler)  │
                   └──────────────┘   └──────────────┘

  Resend API ←── Backend ──→ OVH S3 (fallback media storage)
  (email)
```

---

## 2. Infrastructure Docker

### Production (6 conteneurs, 768 MB RAM)

| Service | Source | Rôle |
|---|---|---|
| `nginx` | `nginx:alpine` | Reverse proxy, SSL termination, static files |
| `backend` | `ghcr.io/tawounfouet/clickmart-backend:latest` | Django + Gunicorn, construit sur GitHub |
| `celery-worker` | `ghcr.io/tawounfouet/clickmart-backend:latest` | Tâches asynchrones (même image que backend) |
| `celery-beat` | `ghcr.io/tawounfouet/clickmart-backend:latest` | Planification périodique |
| `frontend` | `ghcr.io/tawounfouet/clickmart-frontend:latest` | React SPA, construit sur GitHub |
| `certbot` | `certbot/certbot` | Renouvellement SSL Let's Encrypt (12h) |

### Services désactivés en production

| Service | Raison |
|---|---|
| `db` | Remplacé par PostgreSQL distant (49.13.239.42) |
| `redis` | Remplacé par Redis distant (49.13.239.42) |
| `minio` | Inutile (Cloudinary en prod, MinIO en staging) |

### Docker Compose — 3 fichiers

```
docker-compose.yml           ← base partagée (services communs)
docker-compose.prod.yml      ← override production (images ghcr.io, SSL)
docker-compose.staging.yml   ← override staging (HTTP 8080, services locaux)
docker-compose.override.yml  ← dev local (ports, envs, non commité)
```

---

## 3. Flux de données

### 3.1 Navigation publique

```
Browser ──GET /──▶ Nginx ──proxy──▶ Frontend (SPA React)
                                           │
                              ┌────────────┴────────────┐
                              │ axios.get /api/v1/products/
                              ▼
                         Backend ──▶ PostgreSQL distant
                              │
                              ▼
                         JSON → Browser (render React)
```

### 3.2 Upload média

```
Browser ──POST /api/v1/media/images/──▶ Backend
        { file, title }                    │
                                           │ save to Cloudinary
                                           ▼
                                      post_save signal
                                           │
                                           ▼
                                      Celery Worker
                                      process_image.delay()
                                           │
                                           ├── SHA256 hash
                                           ├── extract metadata (Pillow)
                                           └── generate thumbnail
```

### 3.3 Envoi email (commande)

```
Backend ──send_mail()──▶ ResendEmailBackend ──▶ Resend API
                                                    │
                                                    ▼
                                               hello@webtech-dev.info
                                               → thomas.awounfouet@yahoo.com
```

---

## 4. Architecture backend — Apps modulaires

```
backend/
├── config/                 ← settings.py, urls.py, wsgi.py, celery.py
├── apps/                   ← sys.path (manage.py, wsgi.py, celery.py)
│   ├── core/               ← AbstractMedia + ResendEmailBackend
│   ├── images/             ← Pillow processors + Celery tasks + DRF API
│   ├── audio/              ← Skeleton (pydub à installer)
│   ├── video/              ← Skeleton (ffmpeg à installer)
│   └── documents/          ← Skeleton (pypdf à installer)
├── users/                  ← User custom + management commands
├── products/               ← Catalogue produits
├── carts/                  ← Panier
├── orders/                 ← Commandes + Celery tasks
├── uploads/                ← MEDIA_ROOT (local dev uniquement)
├── static/                 ← collectstatic → Nginx
└── .envs/                  ← .local, .staging, .prod
```

---

## 5. Multi-environnement

| Aspect | Dev | Staging | Production |
|---|---|---|---|
| **Branche** | `dev` | `stg` | `main` |
| **CI/CD** | Tests uniquement | Tests + déploiement | Tests + build + déploiement |
| **Port** | 80 | 8080 (HTTP) | 80/443 (HTTPS) |
| **PostgreSQL** | SQLite ou Docker local | Docker local | Distant (49.13.239.42) |
| **Redis** | Docker local | Docker local | Distant (49.13.239.42) |
| **Media storage** | Local | MinIO (S3) | Cloudinary |
| **Email** | Console | SMTP (Gmail) | Resend API |
| **SSL / Certbot** | ❌ | ❌ | ✅ |
| **DEBUG** | True | True | False |

---

## 6. CI/CD Pipeline

```
git push main|stg|dev
        │
        ▼
┌─────────────────────────────────────────────┐
│              GitHub Actions                   │
│                                               │
│  test-backend (67 tests)  test-frontend (11)  │
│              │                  │              │
│              └──────┬───────────┘              │
│                     ▼                          │
│  build-and-push (main/stg only)               │
│  ghcr.io/tawounfouet/clickmart-backend        │
│  ghcr.io/tawounfouet/clickmart-frontend       │
│                     │                          │
│                     ▼                          │
│  deploy (Linode : pull + up -d)               │
│  nginx -s reload                              │
└─────────────────────────────────────────────┘
```

**Optimisations** :
- Images construites sur GitHub (cache GHA, `type=gha,mode=max`)
- Linode fait uniquement `docker pull` + `docker up` (~8s)
- Backend image partagée par 3 services (backend + celery ×2)
- `gcc` + `libpq-dev` retirés du Dockerfile

---

## 7. Storage backend

| Type | Backend | Stockage |
|---|---|---|
| **Statics** (CSS, JS) | Nginx local | `/app/static/` (volume) |
| **Media** (uploads) | Configurable | `MEDIA_STORAGE_BACKEND` |

```
MEDIA_STORAGE_BACKEND=local      → /app/uploads/
MEDIA_STORAGE_BACKEND=s3         → OVH S3 / MinIO / AWS...
MEDIA_STORAGE_BACKEND=cloudinary → Cloudinary (actif en prod)
```

---

## 8. Email backend

```
EMAIL_BACKEND_TYPE=console → stdout (dev, CI)
EMAIL_BACKEND_TYPE=smtp    → Gmail SMTP (staging)
EMAIL_BACKEND_TYPE=resend  → Resend API (production)
```

Backend custom : `apps/core/mail.py` → `ResendEmailBackend` (CC, BCC, HTML, Reply-To)

---

## 9. Sécurité

```
[Nginx]                    ← Terminaison SSL, resolver DNS, reload auto
  │
[CORS Headers]             ← https://webtech-dev.info, www
  │
[Django ALLOWED_HOSTS]     ← webtech-dev.info, IP Linode
  │
[SECURE_SSL_REDIRECT]      ← not DEBUG and ENVIRONMENT == 'production'
  │
[SECURE_PROXY_SSL_HEADER]  ← X-Forwarded-Proto: https
  │
[HSTS / Cookies Secure]    ← 31536000s, include subdomains
  │
[JWTAuthentication]        ← Access 15min + Refresh 7d
  │
[Throttling DRF]           ← anon 20/min, user 60/min, auth 5/min
  │
[SECRET_KEY]               ← Forte, stockée dans .envs/.prod
```

---

## 10. Modèle de données

```
User (AbstractUser)
├── email (unique, USERNAME_FIELD)
├── Cart ──1:N── CartItem → Product
├── Order ──1:N── OrderItem → Product (PROTECT)

Product
├── name, description, price, stock
├── image (Cloudinary/S3)
└── is_active (soft delete)

AbstractMedia (core)
├── id (UUID), file, original_filename
├── file_size, mime_type, sha256
├── uploaded_at, updated_at
│
├── Image    (width, height, thumbnail, exif)
├── Audio    (duration, sample_rate, bitrate)
├── Video    (duration, fps, codec, thumbnail)
└── Document (page_count, author, is_encrypted)
```

---

## 11. Dépendances externes

| Service | Usage | Configuration |
|---|---|---|
| PostgreSQL 49.13.239.42 | Base de données | `DATABASE_URL` via dj-database-url |
| Redis 49.13.239.42 | Broker Celery + Cache | `CELERY_BROKER_URL` |
| Cloudinary | Media storage | `MEDIA_STORAGE_BACKEND=cloudinary` |
| Resend | Email API | `EMAIL_BACKEND_TYPE=resend` |
| OVH S3 | Media fallback | Commenté dans `.envs/.prod` |
| Let's Encrypt | SSL | Certbot Docker |
| GitHub Actions | CI/CD | `automate.yml` |
| ghcr.io | Registry Docker | `docker pull` sur Linode |

---

## 12. Agent deploy-fullstack v3.0

Subagent OpenCode qui automatise tout le cycle de déploiement :

```
@deploy-fullstack              → déploiement (détection auto)
@deploy-fullstack production   → prod (arrête staging)
@deploy-fullstack staging      → staging (arrête prod)
@deploy-fullstack dry-run      → analyse + DRY_RUN_REPORT.md + inventory.yml
@deploy-fullstack inventory    → générer inventory.yml uniquement
```

Phases : preflight → ssh-bootstrap → server-setup → code-deploy → cicd → ssl

---

## 13. Résumé — Décisions architecturales

| Décision | Choisi | Raison |
|---|---|---|
| Base de données | PostgreSQL distant + SQLite fallback | Séparation DB/app, pas de conteneur DB sur le VPS |
| Cache/Broker | Redis distant | Même serveur que PostgreSQL, pas de conteneur local |
| Media storage | Cloudinary (prod), MinIO (staging) | S3-compatible, pas de disque VPS pour les uploads |
| Email | Resend API | Pas de SMTP, dashboard, logs, webhooks |
| CI/CD | GitHub Actions → ghcr.io → Linode pull | Build sur GitHub (gratuit), Linode pull only (~8s) |
| Auth | JWT simplejwt (15min/7d) | Stateless, compatible SPA |
| Frontend state | Context API (useReducer) | Suffisant pour la complexité actuelle |
| UI Framework | Bootstrap 5 | Rapide, pas de dépendance lourde |
| API documentation | drf-spectacular (Swagger) | Auto-généré depuis DRF |
| Infrastructure as Code | Docker Compose 3 fichiers | Base + override prod/staging |
| Déploiement | Agent OpenCode + CI/CD | Automatisation complète du cycle |
