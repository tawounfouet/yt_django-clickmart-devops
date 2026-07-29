# INDEX — ClickMart

> Plan du dépôt et guide de navigation.
> Dernière mise à jour : 29 juillet 2026

---

## Fichiers racine

| Fichier | Rôle |
|---------|------|
| `README.md` | Présentation du projet, stack, démarrage rapide |
| `ARCHITECTURE.md` | Architecture complète (v2.0) |
| `CONTRIBUTING.md` | Guide de contribution (workflow, conventions) |
| `SDLC.md` | Cycle de développement (7 phases, outils par phase) |
| `TODO.md` | Tâches restantes par priorité |
| `CHANGELOG.md` | Historique des versions |
| `DRY_RUN_REPORT.md` | État de l'infrastructure (auto-généré) |
| `inventory.yml` | Inventaire machine-readable |
| `docker-compose.yml` | Base Docker Compose |
| `docker-compose.prod.yml` | Override production |
| `docker-compose.staging.yml` | Override staging |
| `Makefile` | Commandes rapides (up-staging, up-prod...) |
| `.github/workflows/automate.yml` | Pipeline CI/CD (tests → build ghcr.io → deploy) |

---

## Backend (`backend/`)

```
backend/
├── manage.py                    # Entrypoint Django
├── requirements.txt             # Dépendances Python
├── Dockerfile                   # Image Docker (python:3.10-slim → gunicorn)
├── config/                      # Configuration projet Django
│   ├── settings.py              # Settings + fallback DB (PostgreSQL→SQLite)
│   ├── urls.py                  # URLs racine (admin + api/v1 + media)
│   ├── wsgi.py                  # Production entrypoint (gunicorn)
│   └── asgi.py                  # ASGI entrypoint (inutilisé)
├── api/                         # Hub de routage (pas de modèles)
│   └── urls.py                  # Toutes les routes API (14 endpoints)
├── users/                       # App auth
│   ├── models.py                # User(AbstractUser), email-based
│   ├── views.py                 # RegisterView, ProfileView
│   └── serializers.py           # UserRegisterSerializer, UserSerializer
├── products/                    # Catalogue
│   ├── models.py                # Product (name, price, stock, tax_percent)
│   ├── views.py                 # ProductListView, ProductDetailView
│   └── serializers.py           # ProductSerializer
├── carts/                       # Panier
│   ├── models.py                # Cart (OneToOne), CartItem
│   ├── views.py                 # CartView, AddToCartView, ManageCartItemView
│   └── serializers.py           # CartSerializer, CartItemSerializer
├── orders/                      # Commandes
│   ├── models.py                # Order (PENDING/CONFIRMED/DELIVERED), OrderItem
│   ├── views.py                 # PlaceOrderView, MyOrdersView, OrderDetailView
│   ├── serializers.py           # OrderSerializer, OrderItemSerializer
│   └── utils.py                 # send_order_notification (email)
├── static/                      # Vendored (collectstatic output)
└── media/                       # Uploads produits
```

### Key endpoints (tous dans `api/urls.py`)

| Endpoint | Vue | Auth |
|----------|-----|------|
| `POST /api/v1/register/` | `RegisterView` | ❌ |
| `POST /api/v1/token/` | `TokenObtainPairView` | ❌ |
| `GET/PATCH /api/v1/profile/` | `ProfileView` | ✅ |
| `GET /api/v1/products/` | `ProductListView` | ❌ |
| `POST /api/v1/cart/add/` | `AddToCartView` | ✅ |
| `POST /api/v1/orders/place/` | `PlaceOrderView` | ✅ |
| ... | (14 endpoints au total) | |

---

## Frontend (`frontend/`)

```
frontend/
├── package.json                 # React 19, Vite 7, Bootstrap 5
├── vite.config.js               # Minimal (plugin React uniquement)
├── eslint.config.js             # Flat config (React Hooks + Refresh)
├── Dockerfile                   # Multi-stage (Node 18 → nginx:alpine)
├── index.html                   # Entry HTML (titre "Vite + React" à changer)
├── src/
│   ├── main.jsx                 # Root: AuthProvider > CartProvider > App
│   ├── App.jsx                  # Routes + Header + Footer
│   ├── api/index.js             # Instance Axios (baseURL)
│   ├── hooks/
│   │   ├── useAuth.js           # Context consumer (AuthContext)
│   │   └── useAxios.js          # Intercepteurs JWT + refresh token
│   ├── Provider/
│   │   ├── AuthProvider.jsx     # Auth state (localStorage → context)
│   │   └── CartProvider.jsx     # Cart state (useReducer)
│   ├── context/                 # CartContext + AuthContext
│   ├── pages/                   # 14 pages (Home, Cart, Login, Checkout, etc.)
│   ├── components/              # 5 composants (Navbar, Footer, Sidebar, etc.)
│   └── data/products.js         # Données mock — **mort** (jamais importé)
```

---

## Infrastructure (`nginx/` + `docker-compose.yml`)

| Service | Rôle | Dockerfile |
|---------|------|------------|
| `db` | PostgreSQL 16-alpine | Image officielle |
| `backend` | Django + Gunicorn | `backend/Dockerfile` |
| `frontend` | Nginx sert `dist/` | `frontend/Dockerfile` |
| `nginx` | Reverse proxy HTTP/HTTPS | Image officielle |

Reverse proxy Nginx (`nginx/default.conf`) :
```
/            → frontend:80       (SPA React)
/api/        → backend:8000      (API Django)
/admin/      → backend:8000      (Admin Django)
/static/     → backend:8000      (Fichiers statiques)
/media/      → alias /media/     (Uploads)
/.well-known → certbot           (Let's Encrypt)
```

---

## États spéciaux

| État | Description |
|------|-------------|
| **Mid-restructure** | `backend-drf/` supprimé (git), `backend/` non tracké. `git add backend/` nécessaire avant commit. |
| **Dockerfiles gitignorés** | `Dockerfile`, `docker-compose.yml` dans `.gitignore` — pas présents dans le checkout CI. |
| **Tests à zéro** | 5 fichiers `tests.py` vides. `python manage.py test` = 0 tests. |
| **CI/CD absent** | `.github/workflows/` existe mais vide. |
| **gunicorn manquant** | Dans le CMD Docker mais pas dans `requirements.txt`. |

---

## Pour commencer

```bash
# Backend
cd backend && source .venv/bin/activate  # Python 3.11
python manage.py migrate
python manage.py runserver

# Frontend (autre terminal)
cd frontend && npm install && npm run dev
```
