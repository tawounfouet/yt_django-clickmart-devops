# INDEX.md — ClickMart

> Dernière mise à jour : 2026-07-30

---

## Arborescence du projet

```
clickmart/
├── backend/                          # Django 5.2 + DRF
│   ├── config/                       # settings.py, urls.py, celery.py, asgi.py, wsgi.py
│   ├── users/                        # Auth app (User, JWT, register, profile)
│   ├── products/                     # Products app (CRUD, list, detail)
│   ├── carts/                        # Cart app (add, manage items, view)
│   ├── orders/                       # Orders app (place, list, detail)
│   ├── apps/                         # Media apps (modular)
│   │   ├── core/                     # Mail backend (Resend)
│   │   ├── images/                   # Image upload/processing
│   │   ├── audio/                    # Audio upload/processing
│   │   ├── video/                    # Video upload/processing
│   │   └── documents/                # Document upload/processing
│   ├── .envs/                        # Environment files (.local, .staging, .prod)
│   ├── Dockerfile                    # Python 3.10 slim
│   ├── requirements.txt              # 18 packages
│   ├── manage.py
│   ├── pytest.ini                    # pytest config
│   ├── conftest.py                   # Shared fixtures
│   └── tests.py (per app)            # 67 tests (pytest)
│
├── frontend/                         # React 19 + Vite 7
│   ├── src/
│   │   ├── api/                      # Axios client (JWT interceptors, refresh queue)
│   │   ├── components/               # Navbar, Footer, ErrorBoundary, Sidebar, QuantitySelector, OrderDetail
│   │   ├── pages/                    # Home, Products, Cart, Checkout, Login, Register, Dashboard...
│   │   ├── Provider/                 # AuthProvider, CartProvider
│   │   ├── context/                  # AuthContext, CartContext
│   │   ├── hooks/                    # useAuth, useAxios
│   │   └── test/                     # 11 tests (vitest)
│   ├── Dockerfile                    # Node 18, Nginx serve
│   └── vite.config.js
│
├── infra/                            # Infrastructure
│   ├── ansible/                      # IaC (4 rôles : docker, clickmart_app, ssl_certbot, github_actions)
│   ├── nginx/                        # prod.conf, staging.conf
│   ├── certbot/                      # SSL volumes (conf + www)
│   └── scripts/                      # deploy-app.sh, backup-db.sh, setup-ssl.sh, certbot-deploy-hook.sh, minio-setup.sh
│
├── .github/
│   ├── workflows/                    # ci-cd.yml (6 jobs CI/CD)
│   ├── agents/                       # Agent déploiement fullstack
│   ├── instructions/                 # Instructions par phase (1-4)
│   └── skills/                       # 11 skills atomiques
│
├── docs/
│   ├── analyse/                      # 10 analyses techniques
│   ├── deploy/                       # 6 guides déploiement
│   ├── infra/ansible/                # 10 docs Ansible
│   ├── plans/                        # Plans d'implémentation
│   ├── reports/                      # Rapports de gestion
│   └── debug/                        # Rapports de bugs
│
├── docker-compose.yml                # Base (8 services)
├── docker-compose.prod.yml           # Production override
├── docker-compose.staging.yml        # Staging override
├── docker-compose.override.yml       # Dev override
├── Makefile                          # 18 cibles (docker, api, web, ci)
├── ARCHITECTURE.md                   # Architecture v2
├── CHANGELOG.md                      # Historique des versions
├── CONTRIBUTING.md                   # Guide contributeur
├── SDLC.md                           # Cycle de vie développement
├── TODO.md                           # Priorités et dette technique
├── INDEX.md                          # Ce fichier
└── README.md                         # README principal
```

---

## Index des endpoints API

> Base URL : `/api/v1/`

### Authentification

| Méthode | URL | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/register/` | Non | Création de compte |
| POST | `/api/v1/token/` | Non | Obtention JWT (access + refresh) |
| POST | `/api/v1/token/refresh/` | Non | Rafraîchissement access token |
| GET | `/api/v1/profile/` | Oui | Profil utilisateur |
| PATCH | `/api/v1/profile/` | Oui | Mise à jour profil |

### Produits

| Méthode | URL | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/products/` | Non | Liste produits (paginée, 20/page) |
| GET | `/api/v1/products/<id>/` | Non | Détail produit |

### Panier

| Méthode | URL | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/cart/` | Oui | Contenu du panier |
| POST | `/api/v1/cart/add/` | Oui | Ajouter un produit au panier |
| PATCH | `/api/v1/cart/items/<id>/` | Oui | Modifier quantité |
| DELETE | `/api/v1/cart/items/<id>/` | Oui | Supprimer un item |

### Commandes

| Méthode | URL | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/orders/place/` | Oui | Passer commande |
| GET | `/api/v1/orders/` | Oui | Mes commandes |
| GET | `/api/v1/orders/<id>/` | Oui | Détail commande |

### Media (DRF ViewSets)

| Méthode | URL | Auth | Description |
|---|---|---|---|
| GET/POST | `/api/v1/media/images/` | Oui | Images upload/list |
| GET/PATCH/DELETE | `/api/v1/media/images/<id>/` | Oui | Image detail |
| GET/POST | `/api/v1/media/audio/` | Oui | Audio upload/list |
| GET | `/api/v1/media/audio/<id>/` | Oui | Audio detail |
| GET/POST | `/api/v1/media/video/` | Oui | Video upload/list |
| GET | `/api/v1/media/video/<id>/` | Oui | Video detail |
| GET/POST | `/api/v1/media/documents/` | Oui | Document upload/list |
| GET | `/api/v1/media/documents/<id>/` | Oui | Document detail |

### Documentation API

| Méthode | URL | Auth | Description |
|---|---|---|---|
| GET | `/api/schema/` | Non | OpenAPI schema |
| GET | `/api/docs/` | Non | Swagger UI |

### Admin

| URL | Description |
|---|---|
| `/admin/` | Django admin interface |

---

## Index des composants React

| Composant | Fichier | Rôle |
|---|---|---|
| `App` | `src/App.jsx` | Racine + routeur |
| `Navbar` | `src/components/Navbar.jsx` | Barre de navigation |
| `Footer` | `src/components/Footer.jsx` | Pied de page |
| `Sidebar` | `src/components/Sidebar.jsx` | Menu latéral dashboard |
| `ErrorBoundary` | `src/components/ErrorBoundary.jsx` | Capture erreurs React |
| `QuantitySelector` | `src/components/QuantitySelector.jsx` | Sélecteur quantité panier |
| `OrderDetail` | `src/components/OrderDetail.jsx` | Résumé commande |
| `AuthProvider` | `src/Provider/AuthProvider.jsx` | Contexte auth (JWT) |
| `CartProvider` | `src/Provider/CartProvider.jsx` | Contexte panier |
| `PrivateRoute` | `src/pages/PrivateRoute.jsx` | Garde route auth |
| `GuestRoute` | `src/pages/GuestRoute.jsx` | Garde route invité |

## Index des pages React

| Page | Route | Auth |
|---|---|---|
| `Home` | `/` | Non |
| `ProductDetails` | `/product/:id` | Non |
| `Cart` | `/cart` | Non |
| `Checkout` | `/checkout` | Oui |
| `Login` | `/login` | Guest |
| `Register` | `/signup` | Guest |
| `Dashboard` | `/dashboard` | Oui |
| `DashboardHome` | `/dashboard/` (index) | Oui |
| `ProfileSettings` | `/dashboard/profile` | Oui |
| `Orders` | `/dashboard/orders` | Oui |
| `OrderSuccess` | `/order/success/:id` | Oui |

## Index des hooks React

| Hook | Fichier | Rôle |
|---|---|---|
| `useAuth` | `src/hooks/useAuth.js` | Contexte d'authentification |
| `useAxios` | `src/hooks/useAxios.js` | Axios interceptors (déprécié par api/index.js) |

## Index des scripts d'infrastructure

| Script | Fichier | Rôle |
|---|---|---|
| `deploy-app.sh` | `infra/scripts/deploy-app.sh` | Déploiement staging/production |
| `backup-db.sh` | `infra/scripts/backup-db.sh` | Backup PostgreSQL |
| `setup-ssl.sh` | `infra/scripts/setup-ssl.sh` | Configuration SSL initiale |
| `certbot-deploy-hook.sh` | `infra/scripts/certbot-deploy-hook.sh` | Hook renouvellement certificat |
| `minio-setup.sh` | `infra/scripts/minio-setup.sh` | Configuration bucket MinIO |

## Index des documents

| Document | Contenu |
|---|---|
| `README.md` | Guide de démarrage rapide |
| `ARCHITECTURE.md` | Architecture complète (v2.0) |
| `CONTRIBUTING.md` | Workflow de contribution |
| `CHANGELOG.md` | Historique des versions |
| `SDLC.md` | Cycle de vie du développement |
| `TODO.md` | Priorités et dette technique |
| `docs/analyse/ANALYSE_VOCALFIT_CLICKMART.md` | Analyse comparative VocalFit |
| `docs/plans/PLAN_AMELIORATIONS_VOCALFIT.md` | Plan d'implémentation améliorations |
| `docs/plans/PLAN_ANSIBLE.md` | Plan d'implémentation Ansible |
| `docs/infra/ansible/` | Documentation Ansible (10 fichiers) |
| `docs/deploy/` | Guides déploiement (6 fichiers) |
| `docs/debug/2026-07-30_CI-CD_bugs.md` | Rapport de bugs CI/CD |
| `docs/reports/GESTION_CICD.md` | Gestion CI/CD (v3.0) |
| `.github/agents/HOWTO.md` | Guide agent déploiement fullstack |
