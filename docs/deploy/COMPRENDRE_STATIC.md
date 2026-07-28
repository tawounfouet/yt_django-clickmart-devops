# Comprendre les fichiers statiques — Django en production

> Pourquoi l'admin CSS ne chargeait pas, et comment c'est résolu
> Projet ClickMart — `webtech-dev.info`

---

## Table des matières

1. [Le problème en 10 secondes](#1-le-problème-en-10-secondes)
2. [Comment Django gère les statics](#2-comment-django-gère-les-statics)
3. [Pourquoi `proxy_pass` ne marche pas en prod](#3-pourquoi-proxy_pass-ne-marche-pas-en-prod)
4. [La solution : volume partagé + alias Nginx](#4-la-solution--volume-partagé--alias-nginx)
5. [Configuration complète](#5-configuration-complète)
6. [Diagramme de flux](#6-diagramme-de-flux)
7. [Checklist : débugger les statics](#7-checklist--débugger-les-statics)

---

## 1. Le problème en 10 secondes

```
En développement (runserver) : Django sert les statics → ✅
En production (gunicorn)    : Django NE sert PAS les statics → ❌
En production (nginx)       : Nginx DOIT servir les statics → ✅
```

Gunicorn est un serveur WSGI. Il exécute du code Python (vues, API, etc.). Il ne sait pas servir des fichiers statiques. C'est le travail d'un serveur web comme Nginx.

---

## 2. Comment Django gère les statics

### 2.1 En développement (`runserver`)

```python
# config/urls.py
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    ...
]

# En dev, Django ajoute automatiquement une vue pour servir les statics
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

```
┌──────────────────────────────────────────────────────────────┐
│  python manage.py runserver                                  │
│                                                              │
│  GET /static/admin/css/login.css                             │
│       │                                                      │
│       ▼                                                      │
│  django.contrib.staticfiles → lit le fichier sur le disque   │
│       │                                                      │
│       ▼                                                      │
│  Retourne le contenu du fichier CSS                          │
│                                                              │
│  ✅ Fonctionne en dev                                        │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 En production (`gunicorn`)

```
┌──────────────────────────────────────────────────────────────┐
│  gunicorn config.wsgi:application                            │
│                                                              │
│  GET /static/admin/css/login.css                             │
│       │                                                      │
│       ▼                                                      │
│  Gunicorn ne trouve pas de vue pour cette URL               │
│       │                                                      │
│       ▼                                                      │
│  404 Not Found                                               │
│                                                              │
│  ❌ Gunicorn = code Python uniquement, pas de fichiers       │
└──────────────────────────────────────────────────────────────┘
```

### 2.3 `collectstatic` — le pont entre dev et prod

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  $ python manage.py collectstatic                            │
│                                                              │
│  Cherche les statics dans :                                  │
│    • django/contrib/admin/static/     (admin CSS/JS)         │
│    • rest_framework/static/           (DRF CSS/JS)           │
│    • config/static/                   (projet)               │
│                                                              │
│  Copie tout dans :                                           │
│    STATIC_ROOT = backend/static/                             │
│                                                              │
│  Résultat :                                                  │
│    backend/static/                                           │
│    ├── admin/                                                │
│    │   ├── css/         ← CSS de l'admin Django             │
│    │   ├── js/          ← JS de l'admin Django              │
│    │   └── img/         ← Images de l'admin Django           │
│    └── rest_framework/                                       │
│        ├── css/         ← CSS de DRF (browsable API)        │
│        └── js/          ← JS de DRF                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 2.4 Pourquoi `backend/static/` n'est pas dans git

```gitignore
backend/static/
```

C'est un dossier **généré**, pas du code source. Il est recréé à chaque déploiement par `python manage.py collectstatic --noinput` (dans le `command` du docker-compose). Le commiter serait comme commiter `node_modules/` ou `dist/`.

---

## 3. Pourquoi `proxy_pass` ne marche pas en prod

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  APPROCHE 1 : proxy_pass http://backend:8000                     │
│  ─────────────────────────────────────                            │
│                                                                  │
│  Navigateur → Nginx → /static/ → proxy_pass → backend:8000       │
│                                                    │             │
│                                                    ▼             │
│                                              Gunicorn            │
│                                              → Cherche une vue   │
│                                              → Aucune vue pour   │
│                                                /static/...       │
│                                              → 404               │
│                                                                  │
│  ❌ Gunicorn ne sert pas les fichiers, il exécute du Python      │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  APPROCHE 2 : alias /static/ (volume partagé)                    │
│  ─────────────────────────────────────────                        │
│                                                                  │
│  Navigateur → Nginx → /static/ → alias → /static/ (disque)       │
│                                                    │             │
│                                                    ▼             │
│                                              Volume Docker :      │
│                                              backend/static/      │
│                                              → lit le fichier     │
│                                              → retourne le CSS    │
│                                                                  │
│  ✅ Nginx lit directement sur le disque, pas de Python           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. La solution : volume partagé + alias Nginx

### 4.1 Principe

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  docker-compose.yml                                              │
│  ═══════════════                                                 │
│                                                                  │
│  backend:                                                        │
│    volumes:                                                      │
│      - ./backend/static:/app/static   ← collectstatic écrit ICI  │
│                                                                  │
│  nginx:                                                          │
│    volumes:                                                      │
│      - ./backend/static:/static:ro   ← Nginx lit ICI             │
│                                                                  │
│  Résultat :                                                      │
│    backend/static/ (sur l'hôte)                                  │
│        ▲                   ▲                                     │
│        │                   │                                     │
│    backend écrit      nginx lit                                  │
│    (collectstatic)    (alias /static/)                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 Volume `:ro` (read-only)

```yaml
nginx:
  volumes:
    - ./backend/static:/static:ro   # ← ro = read-only
```

Le `:ro` signifie que nginx peut **lire** les fichiers, mais pas les modifier. C'est un principe de sécurité : seul le backend a besoin d'écrire (via `collectstatic`), nginx n'a besoin que de lire.

---

## 5. Configuration complète

### 5.1 Django (`backend/config/settings.py`)

```python
# Où chercher les statics pendant le développement
STATIC_URL = 'static/'

# Où collectstatic rassemble tout pour la production
STATIC_ROOT = BASE_DIR / 'static'

# Dossiers supplémentaires à inclure dans collectstatic
STATICFILES_DIRS = [
    'config/static'
]
```

### 5.2 Docker Compose

```yaml
services:
  backend:
    volumes:
      - ./backend/static:/app/static    # Backend écrit les statics ICI
      - ./backend/media:/app/media

  nginx:
    volumes:
      - ./backend/static:/static:ro     # Nginx lit les statics ICI (read-only)
      - ./backend/media:/media
```

### 5.3 Nginx (`infra/nginx/default.conf`)

```nginx
server {
    listen 443 ssl;

    # Les fichiers statiques sont servis directement par Nginx
    location /static/ {
        alias /static/;     # ← Le volume monté dans le container nginx
    }

    # Les médias (uploads) aussi
    location /media/ {
        alias /media/;
    }

    # Tout le reste → Gunicorn
    location / {
        proxy_pass http://frontend:80;
    }
    location /api/ {
        proxy_pass http://backend:8000;
    }
    location /admin/ {
        proxy_pass http://backend:8000;
    }
}
```

### 5.4 Ordre de démarrage (dans `docker-compose.yml`)

```yaml
backend:
  command: >
    sh -c "python manage.py collectstatic --noinput &&    # 1. Rassembler les statics
           python manage.py migrate &&                      # 2. Appliquer les migrations
           gunicorn ..."                                    # 3. Démarrer le serveur
```

`collectstatic` s'exécute **avant** gunicorn. Les fichiers sont donc prêts quand le serveur démarre.

---

## 6. Diagramme de flux

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  1. DÉMARRAGE                                                            │
│     ────────                                                             │
│     docker compose up                                                    │
│       │                                                                  │
│       ▼                                                                  │
│     backend : collectstatic                                              │
│       │                                                                  │
│       │  django/contrib/admin/static/  ──┐                               │
│       │  rest_framework/static/         ──┤                               │
│       │  config/static/                 ──┼──► backend/static/            │
│       │                                   │    ├── admin/css/login.css   │
│       │                                   │    ├── admin/js/...          │
│       │                                   │    └── rest_framework/...    │
│       ▼                                                                  │
│     backend : gunicorn ──► prêt sur :8000                                │
│                                                                          │
│                                                                          │
│  2. REQUÊTE NAVIGATEUR                                                   │
│     ─────────────────                                                    │
│     GET https://webtech-dev.info/admin/login/                            │
│       │                                                                  │
│       ▼                                                                  │
│     Nginx :443                                                            │
│       │                                                                  │
│       │  /admin/  ──► proxy_pass → backend:8000                          │
│       │                Django sert le HTML de la page login              │
│       │                                                                  │
│       │  Le HTML contient :                                              │
│       │  <link href="/static/admin/css/login.css" rel="stylesheet">     │
│       │                                                                  │
│       ▼                                                                  │
│     Navigateur fait une 2ème requête :                                   │
│     GET https://webtech-dev.info/static/admin/css/login.css              │
│       │                                                                  │
│       ▼                                                                  │
│     Nginx :443                                                            │
│       │                                                                  │
│       │  /static/ ──► alias /static/                                     │
│       │              → backend/static/admin/css/login.css (sur l'hôte)   │
│       │              → Nginx lit le fichier directement                  │
│       │              → Retourne le CSS (200 OK)                          │
│       │                                                                  │
│       ▼                                                                  │
│     Navigateur applique le CSS → Admin s'affiche correctement 🎨         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Checklist : débugger les statics

Quand l'admin Django n'a pas de CSS, vérifier dans l'ordre :

```
[ ] 1. Les fichiers existent dans le container backend ?
    $ docker exec clickmart-backend-1 ls /app/static/admin/css/login.css

[ ] 2. Nginx peut accéder aux fichiers ?
    $ docker exec clickmart-nginx-1 ls /static/admin/css/login.css

[ ] 3. Nginx renvoie 200 sur le CSS ?
    $ curl -I https://domaine/static/admin/css/login.css

[ ] 4. La config Nginx est correcte ?
    $ docker exec clickmart-nginx-1 cat /etc/nginx/conf.d/default.conf
    → location /static/ { alias /static/; }

[ ] 5. Le volume est bien monté dans docker-compose ?
    $ docker inspect clickmart-nginx-1 | grep -A5 static
    → Doit montrer le bind mount vers ./backend/static
```

| Symptôme | Cause probable | Solution |
|---|---|---|
| CSS 404 | collectstatic pas exécuté | Rebuild backend |
| CSS 404 | Volume pas monté dans nginx | `./backend/static:/static:ro` |
| CSS 403 | Permissions | `chown -R` ou rebuild |
| CSS OK mais pas de design | Cache navigateur | Ctrl+Shift+R |
| HTML OK, CSS 404 | `proxy_pass` au lieu de `alias` | Remplacer par `alias /static/` |

---

*Document créé le 29 juillet 2026.*
