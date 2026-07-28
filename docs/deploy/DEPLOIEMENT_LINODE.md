# Déploiement ClickMart sur Linode — Guide complet

> Date du déploiement : 28 juillet 2026
> Serveur : Linode (Ubuntu 24.04) — 172.239.20.14
> État : ✅ Fonctionnel (HTTP 200 sur tous les endpoints)

---

## Table des matières

1. [Architecture de déploiement](#1-architecture-de-déploiement)
2. [Les 2 couches de firewall](#2-les-2-couches-de-firewall)
3. [Pourquoi seuls les ports 80 et 443 sont nécessaires](#3-pourquoi-seuls-les-ports-80-et-443-sont-nécessaires)
4. [Procédure de déploiement](#4-procédure-de-déploiement)
5. [Variables d'environnement](#5-variables-denvironnement)
6. [Fichiers gitignorés — problème et solution](#6-fichiers-gitignorés--problème-et-solution)
7. [Flux réseau complet](#7-flux-réseau-complet)
8. [Vérification et tests](#8-vérification-et-tests)

---

## 1. Architecture de déploiement

### 1.1 Vue d'ensemble

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           INTERNET                                        │
│                                                                          │
│   Utilisateur ──► http://172.239.20.14                                   │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   │ Port 80 (HTTP) / 443 (HTTPS)
                                   │
┌──────────────────────────────────┼───────────────────────────────────────┐
│                          LINODE VPS                                       │
│                                                                          │
│  ┌──────────────────────────────┴─────────────────────────────────────┐ │
│  │                     FIREWALL CLOUD LINODE                          │ │
│  │                  (géré via dashboard ou API)                        │ │
│  │                                                                     │ │
│  │  ✅ TCP 22   (SSH)     ──► Accepté                                 │ │
│  │  ✅ TCP 80   (HTTP)    ──► Accepté                                 │ │
│  │  ✅ TCP 443  (HTTPS)   ──► Accepté                                 │ │
│  │  ❌ TCP 8000 (Django)  ──► NON UTILE (bloqué = plus sûr)          │ │
│  │  ❌ TCP 5173 (React)   ──► NON UTILE (bloqué = plus sûr)          │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                   │                                       │
│  ┌────────────────────────────────┴───────────────────────────────────┐ │
│  │                       UBUNTU 24.04 SERVER                           │ │
│  │                                                                     │ │
│  │  ┌───────────────────────────────────────────────────────────────┐ │ │
│  │  │                    DOCKER COMPOSE                              │ │ │
│  │  │                                                               │ │ │
│  │  │  ┌─────────────────────────────────────────────────────────┐ │ │ │
│  │  │  │            NGINX (reverse proxy)                        │ │ │ │
│  │  │  │            nginx:alpine                                 │ │ │ │
│  │  │  │            ports exposés : 80:80, 443:443               │ │ │ │
│  │  │  │                                                        │ │ │ │
│  │  │  │  /            ──► frontend:80     (React SPA)           │ │ │ │
│  │  │  │  /api/*       ──► backend:8000    (Django DRF)          │ │ │ │
│  │  │  │  /admin/*     ──► backend:8000    (Django Admin)        │ │ │ │
│  │  │  │  /static/*    ──► backend:8000    (Fichiers statiques)  │ │ │ │
│  │  │  │  /media/*     ──► /media/          (Uploads)             │ │ │ │
│  │  │  └────────────┬──────────────┬─────────────────────────────┘ │ │ │
│  │  │               │              │                                │ │ │
│  │  │               ▼              ▼                                │ │ │
│  │  │  ┌──────────────────┐  ┌──────────────────┐                  │ │ │
│  │  │  │    FRONTEND      │  │     BACKEND      │                  │ │ │
│  │  │  │  nginx:alpine    │  │  python:3.10-slim│                  │ │ │
│  │  │  │  (sert dist/)    │  │  Gunicorn ×3     │                  │ │ │
│  │  │  │  Port :80 (int)  │  │  Port :8000 (int)│                  │ │ │
│  │  │  │                  │  │                  │                  │ │ │
│  │  │  │  React 19 SPA    │  │  Django 5.2      │                  │ │ │
│  │  │  │  Vite 7 build    │  │  DRF 3.16        │                  │ │ │
│  │  │  └──────────────────┘  └────────┬─────────┘                  │ │ │
│  │  │                                 │                             │ │ │
│  │  │                                 ▼                             │ │ │
│  │  │                     ┌──────────────────┐                     │ │ │
│  │  │                     │       DB         │                     │ │ │
│  │  │                     │ postgres:16      │                     │ │ │
│  │  │                     │ Port :5432 (int) │                     │ │ │
│  │  │                     │ Volume persistant│                     │ │ │
│  │  │                     └──────────────────┘                     │ │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Tableau des containers

| Service | Image | Port interne | Port exposé | Rôle |
|---|---|---|---|---|
| **nginx** | nginx:alpine | 80 | **80:80, 443:443** | Reverse proxy — seul point d'entrée |
| **frontend** | clickmart-frontend | 80 | _aucun_ | Sert le build React (`dist/`) |
| **backend** | clickmart-backend | 8000 | _aucun_ | API Django via Gunicorn |
| **db** | postgres:16-alpine | 5432 | _aucun_ | Base de données |

---

## 2. Les 2 couches de firewall

Il y a **deux niveaux de filtrage** qu'il ne faut pas confondre :

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│    COUCHE 1 : Firewall Cloud Linode                         │
│    ───────────────────────────────────                       │
│    · Géré depuis le dashboard Linode ou l'API               │
│    · Se situe AVANT le serveur (hyperviseur)                │
│    · Filtre les paquets AVANT qu'ils arrivent sur la VM     │
│    · NON accessible en SSH (le serveur ne le voit pas)      │
│    · Configurable via :                                     │
│      - Dashboard web : cloud.linode.com → Firewalls         │
│      - API REST    : curl -H "Authorization: Bearer $TOKEN" │
│      - linode-cli  : linode-cli firewalls rules-update      │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│    COUCHE 2 : UFW / iptables (sur le serveur)               │
│    ─────────────────────────────────────                     │
│    · Géré en SSH directement sur le serveur                 │
│    · Filtre les paquets QUI ARRIVENT sur le serveur         │
│    · Commandes : ufw allow 80, ufw status, iptables -L      │
│    · Sur notre serveur : INACTIF (non nécessaire car        │
│      Docker gère ses propres règles iptables)               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 2.1 Analogie

```
┌─────────────────────┐
│   Portail immeuble   │  ← Firewall Cloud Linode
│  (gardien extérieur) │     On ne peut pas l'ouvrir
│                      │     depuis l'appartement
└─────────┬───────────┘
          │
┌─────────┴───────────┐
│  Porte appartement   │  ← UFW / iptables
│  (gardien intérieur) │     On peut l'ouvrir en SSH
└──────────────────────┘
```

---

## 3. Pourquoi seuls les ports 80 et 443 sont nécessaires

### 3.1 Version initiale (obsolète) — sans Nginx

```
Internet
    │
    ├── port 8000 ──► backend (Django runserver)
    │                 ALLOWED_HOSTS doit inclure l'IP
    │                 CORS doit autoriser l'IP
    │
    └── port 5173 ──► frontend (Vite dev server)
                      VITE_SERVER_BASE_URL = http://<IP>:8000/api/v1
```

❌ Problèmes : ports multiples, pas de SSL, Django exposé directement, pas de static files.

### 3.2 Version actuelle (avec Nginx reverse proxy)

```
Internet
    │
    └── port 80 (et 443) ──► NGINX ──┬── /          ──► frontend:80    (interne)
                                      ├── /api/*     ──► backend:8000   (interne)
                                      ├── /admin/*   ──► backend:8000   (interne)
                                      ├── /static/*  ──► backend:8000   (interne)
                                      └── /media/*   ──► /media/        (volume)
```

✅ Avantages :
- Un seul port d'entrée (80 puis 443 en HTTPS)
- Backend et frontend **inaccessibles** depuis l'extérieur
- SSL plus simple (un seul certificat)
- Static files servis par whitenoise ou nginx directement
- `VITE_SERVER_BASE_URL = "/api/v1"` (relatif, pas d'IP dure)

### 3.3 Règles firewall recommandées

```
┌──────────┬──────────┬──────────┬─────────────────────┐
│  Action  │ Protocole│  Port    │  Utilité            │
├──────────┼──────────┼──────────┼─────────────────────┤
│ ACCEPT   │ TCP      │ 22       │ SSH                 │
│ ACCEPT   │ TCP      │ 80       │ HTTP (frontend+API) │
│ ACCEPT   │ TCP      │ 443      │ HTTPS (SSL)         │
├──────────┼──────────┼──────────┼─────────────────────┤
│  DELETE  │ TCP      │ 8000     │ Plus utile (nginx)  │
│  DELETE  │ TCP      │ 5173     │ Plus utile (nginx)  │
└──────────┴──────────┴──────────┴─────────────────────┘
```

---

## 4. Procédure de déploiement

### 4.1 État initial du serveur

```bash
ssh root@172.239.20.14
# Ubuntu 24.04 vierge — rien installé
```

### 4.2 Installation des dépendances

```bash
# Mise à jour du système
apt update && apt upgrade -y

# Git (déjà présent sur Ubuntu 24.04)
apt install git -y

# Docker
curl -fsSL https://get.docker.com | sh

# Docker Compose (plugin)
apt install docker-compose-plugin -y

# Vérification
docker --version      # Docker 29.6.2
docker compose version # Docker Compose v5.3.1
git --version         # git 2.43.0
```

### 4.3 Correction du code source (faite localement)

Avant le déploiement, 2 modifications ont été faites dans `backend/config/settings.py` :

```python
# AVANT (ligne 30) — bloquant en production
ALLOWED_HOSTS = []

# APRÈS — lit depuis les variables d'environnement
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')


# AVANT (lignes 221-223) — limité au dev local
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
]

# APRÈS — lit depuis les variables d'environnement
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173'
).split(',')
```

Ces modifications ont été commitées et pushées sur GitHub.

### 4.4 Déploiement sur le serveur

```bash
# 1. Créer le répertoire et cloner
ssh root@172.239.20.14
mkdir -p /opt/clickmart
git clone https://github.com/tawounfouet/yt_django-clickmart-devops.git /opt/clickmart

# 2. Copier les fichiers gitignorés (Dockerfiles + docker-compose.yml)
#    → faire depuis la machine locale :
scp backend/Dockerfile root@172.239.20.14:/opt/clickmart/backend/
scp frontend/Dockerfile root@172.239.20.14:/opt/clickmart/frontend/
scp docker-compose.yml root@172.239.20.14:/opt/clickmart/

# 3. Créer les fichiers .env sur le serveur
cat > /opt/clickmart/backend/.env.docker << 'EOF'
SECRET_KEY=django-insecure-change-me-in-production
DEBUG=True
DB_NAME=clickmart
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
ALLOWED_HOSTS=172.239.20.14,localhost,127.0.0.1,backend
CORS_ALLOWED_ORIGINS=http://172.239.20.14,http://localhost:5173
EMAIL_HOST_USER=test@test.com
EMAIL_HOST_PASSWORD=test
EOF

cat > /opt/clickmart/backend/.env.production << 'EOF'
POSTGRES_DB=clickmart
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
EOF

# 4. Démarrer les containers
cd /opt/clickmart
docker compose up --build -d
```

### 4.5 Ouverture des ports (dashboard Linode)

Aller dans **Linode Cloud Manager → Firewalls** et ajouter les règles entrantes :

```
TCP 80  (HTTP)   → All IPv4, All IPv6
TCP 443 (HTTPS)  → All IPv4, All IPv6
```

Supprimer les règles obsolètes (8000, 5173).

---

## 5. Variables d'environnement

### 5.1 `.env.docker` (backend — chargé par docker-compose)

| Variable | Valeur exemple | Rôle |
|---|---|---|
| `SECRET_KEY` | `django-insecure-...` | Clé secrète Django |
| `DEBUG` | `True` ou `False` | Mode debug |
| `DB_NAME` | `clickmart` | Nom de la base |
| `DB_USER` | `postgres` | Utilisateur PostgreSQL |
| `DB_PASSWORD` | `postgres` | Mot de passe PostgreSQL |
| `DB_HOST` | `db` | Nom du service Docker |
| `DB_PORT` | `5432` | Port PostgreSQL |
| `ALLOWED_HOSTS` | `IP,localhost,127.0.0.1,backend` | Hosts autorisés (séparés par `,`) |
| `CORS_ALLOWED_ORIGINS` | `http://IP,http://localhost:5173` | Origines CORS autorisées |
| `EMAIL_HOST_USER` | `email@gmail.com` | Email expéditeur |
| `EMAIL_HOST_PASSWORD` | `app-password` | Mot de passe app Gmail |

### 5.2 `.env.production` (PostgreSQL)

| Variable | Valeur | Rôle |
|---|---|---|
| `POSTGRES_DB` | `clickmart` | Nom de la base |
| `POSTGRES_USER` | `postgres` | Superutilisateur |
| `POSTGRES_PASSWORD` | `postgres` | Mot de passe |

### 5.3 Chaîne de chargement

```
docker-compose.yml
    │
    ├── service db :
    │   └── env_file: ./backend/.env.production
    │       └── POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    │
    └── service backend :
        └── env_file: ./backend/.env.docker
            └── Toutes les variables sont lues par :
                └── config('NOM_VARIABLE')  ← python-decouple
                    └── settings.py
```

---

## 6. Fichiers gitignorés — problème et solution

### 6.1 Le problème

Ces 4 fichiers sont dans `.gitignore` :

```gitignore
# .gitignore lignes 175-180
frontend/Dockerfile
backend/.env.docker
backend/.env.production
backend/.env.development
backend/Dockerfile
docker-compose.yml
```

Un simple `git clone` ne les télécharge pas. Le serveur ne peut pas builder les images.

### 6.2 Le flux actuel

```
┌─────────────────────┐     git push      ┌─────────────────────┐
│   Machine locale    │ ────────────────► │      GitHub         │
│                     │                   │                     │
│ ✅ Dockerfiles      │                   │ ❌ PAS de Dockerfiles│
│ ✅ docker-compose   │                   │ ❌ PAS de compose   │
│ ✅ .env (non pushé) │                   │ ✅ Code source      │
└─────────────────────┘                   └──────────┬──────────┘
                                                     │ git pull
                          ┌──────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Serveur Linode                               │
│                                                                 │
│  git clone → ❌ PAS de Dockerfiles, PAS de docker-compose       │
│                                                                 │
│  SOLUTION : SCP manuel des fichiers gitignorés                  │
│                                                                 │
│  $ scp backend/Dockerfile root@IP:/opt/clickmart/backend/       │
│  $ scp frontend/Dockerfile root@IP:/opt/clickmart/frontend/     │
│  $ scp docker-compose.yml root@IP:/opt/clickmart/               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 Pourquoi ce choix ?

La stratégie « server-managed » est documentée dans le README : les Dockerfiles et docker-compose sont des **fichiers de configuration serveur**, pas de code applicatif. Le code change souvent, la config d'infra moins.

Alternatives possibles :
- **Tracker les fichiers** : les sortir du `.gitignore` → un `git pull` suffit
- **Template gitignoré** : créer `docker-compose.example.yml` tracké, et le copier manuellement
- **CI/CD automatise le SCP** : le pipeline GitHub Actions copie les fichiers avant le deploy

---

## 7. Flux réseau complet

### 7.1 Requête HTTP : `GET /api/v1/products/`

```
ÉTAPE 1 : Du navigateur au serveur
─────────────────────────────────────
Navigateur ── GET /api/v1/products/ ──► DNS ──► 172.239.20.14:80


ÉTAPE 2 : Firewall Cloud Linode
─────────────────────────────────────
Paquet TCP port 80 → Règle "accept-inbound-HTTP" → ACCEPT
Paquet transmis à la VM


ÉTAPE 3 : Docker (iptables)
─────────────────────────────────────
Port 80 sur l'hôte → mappé vers container nginx:80
Paquet transmis au container nginx


ÉTAPE 4 : Nginx (reverse proxy)
─────────────────────────────────────
nginx lit la requête :
  GET /api/v1/products/ Host: 172.239.20.14

La règle location /api/ correspond :
  proxy_pass http://backend:8000;

Nginx ajoute les headers :
  Host: $host
  X-Real-IP: $remote_addr
  X-Forwarded-Proto: $scheme

Transmet la requête au container backend:8000


ÉTAPE 5 : Django (Gunicorn)
─────────────────────────────────────
Gunicorn reçoit la requête sur 0.0.0.0:8000

Django vérifie ALLOWED_HOSTS :
  "172.239.20.14" est dans la liste → OK

Django vérifie CORS :
  Requête same-origin (pas de cross-origin) → OK

Route /api/v1/products/ → ProductListView
  → Query: Product.objects.filter(is_active=True)
  → Sérialisation: ProductSerializer
  → Réponse: [] (base vide)


ÉTAPE 6 : Retour
─────────────────────────────────────
Django → Gunicorn → Nginx → Hôte:80 → Firewall → Navigateur

Le navigateur reçoit :
  HTTP 200 OK
  Content-Type: application/json
  []
```

### 7.2 Résolution DNS interne Docker

```
┌─────────────────────────────────────────────┐
│           Docker Network : clickmart_default │
│                                             │
│  DNS interne Docker :                       │
│                                             │
│  "backend"  → 172.18.0.x  (container IP)    │
│  "frontend" → 172.18.0.y  (container IP)    │
│  "db"       → 172.18.0.z  (container IP)    │
│  "nginx"    → 172.18.0.w  (container IP)    │
│                                             │
│  Quand Nginx fait proxy_pass http://backend:8000 │
│  Docker résout "backend" automatiquement     │
└─────────────────────────────────────────────┘
```

---

## 8. Vérification et tests

### 8.1 Commandes de vérification

```bash
# Depuis le serveur (SSH)
cd /opt/clickmart

# État des containers
docker compose ps

# Logs du backend
docker compose logs backend

# Test interne — frontend
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:80

# Test interne — API via nginx
curl -s http://localhost:80/api/v1/products/

# Test interne — backend direct (depuis nginx)
docker exec clickmart-nginx-1 curl -s http://backend:8000/api/v1/products/

# Créer un superuser
docker compose exec backend python manage.py createsuperuser
```

### 8.2 Depuis l'extérieur

```bash
# Frontend
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://172.239.20.14/

# API produits
curl -s http://172.239.20.14/api/v1/products/

# Inscription
curl -s -X POST http://172.239.20.14/api/v1/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","username":"test","password":"Test1234!"}'

# Connexion (obtenir le token JWT)
curl -s -X POST http://172.239.20.14/api/v1/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test1234!"}'
```

### 8.3 Résultat attendu

```
HTTP 200 ── Frontend
HTTP 200 ── API Products (tableau vide [])
HTTP 201 ── Register (succès)
HTTP 200 ── Token (retourne access + refresh)
```

---

## Annexe : Commandes utiles

```bash
# Redémarrer après modification du code
ssh root@172.239.20.14 "cd /opt/clickmart && git pull && docker compose up --build -d"

# Voir les logs en temps réel
ssh root@172.239.20.14 "cd /opt/clickmart && docker compose logs -f"

# Accéder au shell Django
ssh root@172.239.20.14 "cd /opt/clickmart && docker compose exec backend python manage.py shell"

# Backup de la base
ssh root@172.239.20.14 "cd /opt/clickmart && docker compose exec db pg_dump -U postgres clickmart > backup.sql"

# Arrêter tous les services
ssh root@172.239.20.14 "cd /opt/clickmart && docker compose down"

# Arrêter ET supprimer les volumes (reset complet)
ssh root@172.239.20.14 "cd /opt/clickmart && docker compose down -v"
```

---

*Document créé le 28 juillet 2026 — session de déploiement initial.*
