# Plan d'implémentation — Améliorations VocalFit → ClickMart

> Basé sur l'analyse : `docs/analyse/ANALYSE_VOCALFIT_CLICKMART.md`
> **Périmètre** : 13 patterns identifiés, 12 proposés à l'implémentation
> **Dashboards** : `TODO.md` (dette technique), `docs/reports/GESTION_CICD.md` (CI/CD)

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Session 1 — Quick wins : Sécurité & Monitoring](#2-session-1--quick-wins--sécurité--monitoring)
   - [1.1 Sentry](#11-sentry-backend--frontend)
   - [1.2 AuthGuard / GuestGuard](#12-authguard--guestguard)
   - [1.3 apiClient refresh queue](#13-apiclient-avec-refresh-token-intelligent)
   - [1.4 Makefile CI](#14-makefile-cibles-ci)
   - [1.5 django-environ](#15-django-environ)
3. [Session 2 — Qualité : Tests & Documentation](#3-session-2--qualité--tests--documentation)
   - [2.1 pytest + model_bakery](#21-pytest--model_bakery)
   - [2.2 conftest.py fixtures partagées](#22-conftestpy-fixtures-partagées)
   - [2.3 INDEX.md](#23-indexmd)
4. [Session 3 — Architecture : UUID & Ops](#4-session-3--architecture--uuid--ops)
   - [3.1 UUID PKs](#31-uuid-pks-tous-les-modèles)
   - [3.2 fail2ban](#32-fail2ban-rôle-ansible)
   - [3.3 DB backup rétention](#33-db-backup-avec-rétention)
5. [Estimation d'effort](#5-estimation-deffort)
6. [Ordre d'exécution recommandé](#6-ordre-dexécution-recommandé)

---

## 1. Vue d'ensemble

```
┌─────────────────────────────────────────────────────────┐
│              Analysis VocalFit → ClickMart               │
│                                                          │
│  13 patterns identifiés dans le projet de référence      │
│                 ↓                                        │
│   Session 1 (Quick Wins)   Session 2 (Qualité)          │
│   ┌─────────────────────┐ ┌─────────────────────┐       │
│   │ • Sentry            │ │ • pytest            │       │
│   │ • AuthGuard         │ │ • model_bakery      │       │
│   │ • apiClient refresh │ │ • conftest.py       │       │
│   │ • Makefile CI       │ │ • INDEX.md          │       │
│   │ • django-environ    │ │                     │       │
│   └─────────────────────┘ └─────────────────────┘       │
│                 ↓                      ↓                 │
│           Session 3 (Architecture)                      │
│           ┌─────────────────────┐                       │
│           │ • UUID PKs          │                       │
│           │ • fail2ban          │                       │
│           │ • DB backup         │                       │
│           └─────────────────────┘                       │
│                 ↓                                        │
│     ClickMart production-grade / large-échelle          │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Session 1 — Quick wins : Sécurité & Monitoring

**Durée estimée** : 2h
**Impact** : 🔴 Critique (monitoring, sécurité, UX)

### 1.1 Sentry (backend + frontend)

**Objectif** : Capturer toutes les erreurs Django + React en production.

#### Backend

```bash
pip install sentry-sdk[django]
```

**Fichier** : `backend/config/settings.py`

```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

SENTRY_DSN = config("SENTRY_DSN", default="")

if SENTRY_DSN and not DEBUG:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
```

**Fichier** : `backend/.envs/.prod` (via Ansible template J2)

```bash
SENTRY_DSN=https://xxxxx@ingest.sentry.io/xxxxx
```

**Fichier** : `infra/ansible/group_vars/secrets.yml`

```yaml
sentry_dsn: "https://xxxxx@ingest.sentry.io/xxxxx"
```

**Fichier** : `infra/ansible/roles/clickmart_app/templates/.env.prod.j2`

```jinja2
SENTRY_DSN={{ sentry_dsn }}
```

#### Frontend

```bash
cd frontend && npm install @sentry/react
```

**Fichier** : `frontend/src/main.jsx`

```jsx
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  integrations: [Sentry.browserTracingIntegration()],
  tracesSampleRate: 0.1,
  enabled: import.meta.env.PROD,
});

// Wrapper le <App /> dans Sentry.ErrorBoundary
```

**Vérification** : Provoquer une erreur délibérée, vérifier qu'elle apparaît dans le dashboard Sentry.

---

### 1.2 AuthGuard / GuestGuard

**Objectif** : Protéger les routes React de façon centralisée, sans `useEffect` dispersés.

**Fichier** : `frontend/src/components/AuthGuard.jsx` (créer)

```jsx
import { Navigate, useLocation } from "react-router-dom";

export function AuthGuard({ children }) {
  const token = localStorage.getItem("accessToken");
  const location = useLocation();
  
  if (!token) return <Navigate to="/login" state={{ from: location }} replace />;
  return children;
}

export function GuestGuard({ children }) {
  const token = localStorage.getItem("accessToken");
  if (token) return <Navigate to="/" replace />;
  return children;
}
```

**Utilisation** : Wrapper les routes dans le routeur.

```jsx
// Routes protégées
<Route path="/cart" element={<AuthGuard><CartPage /></AuthGuard>} />
<Route path="/checkout" element={<AuthGuard><CheckoutPage /></AuthGuard>} />

// Routes publiques uniquement
<Route path="/login" element={<GuestGuard><LoginPage /></GuestGuard>} />
<Route path="/register" element={<GuestGuard><RegisterPage /></GuestGuard>} />
```

**Nettoyage** : Supprimer les `useEffect` de vérification de token dans les pages individuelles.

**Fichiers modifiés** :
- `frontend/src/components/AuthGuard.jsx` (nouveau)
- `frontend/src/App.jsx` (wrapper les routes)
- Toutes les pages avec vérification manuelle (nettoyage)

---

### 1.3 apiClient avec refresh token intelligent

**Objectif** : Remplacer la redirection brutale sur 401 par un refresh token automatique avec singleton queue.

**Fichier** : `frontend/src/api/index.js`

```javascript
import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_SERVER_BASE_URL || "http://localhost:8000/api/v1",
  headers: { "Content-Type": "application/json" },
});

// ── Request interceptor (inject token) ──
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("accessToken");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Response interceptor (refresh on 401) ──
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const refresh = localStorage.getItem("refreshToken");
      const { data } = await axios.post(
        `${api.defaults.baseURL}/auth/token/refresh/`,
        { refresh }
      );
      localStorage.setItem("accessToken", data.access);
      processQueue(null, data.access);
      originalRequest.headers.Authorization = `Bearer ${data.access}`;
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      window.location.href = "/login";
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export { api };
```

**Note** : Vérifier l'URL de refresh correcte (`/api/v1/auth/token/refresh/` ou autre selon la config JWT de ClickMart).

---

### 1.4 Makefile cibles CI

**Objectif** : Ajouter des cibles Makefile pour exécuter le CI en local (sans GitHub Actions).

```makefile
# ─── API ───
api-test:
	cd backend && python manage.py test --verbosity=2

api-lint:
	cd backend && ruff check . --ignore F401,E501,E402,B017,BLE001,I001,RUF012,RUF100,S110

api-shell:
	cd backend && python manage.py shell

api-migrate:
	cd backend && python manage.py migrate

# ─── Web ───
web-dev:
	cd frontend && npm run dev

web-test:
	cd frontend && npx vitest run

web-lint:
	cd frontend && npm run lint

web-build:
	cd frontend && npm run build

# ─── CI local ───
ci: api-lint api-test web-lint web-test
	@echo "✅ All CI checks passed"
```

---

### 1.5 django-environ

**Objectif** : Remplacer `python-decouple` + `dj-database-url` par `django-environ` (solution unifiée).

```bash
pip uninstall python-decouple dj-database-url
pip install django-environ
```

**Fichier** : `backend/config/settings.py`

```python
import environ

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".envs" / ".prod")  # ou .local selon ENVIRONMENT

# Database
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}

# Cache (si Redis)
CACHE_URL = env("CACHE_URL", default="")
if CACHE_URL:
    CACHES = {"default": env.cache("CACHE_URL")}

# Remplace config("KEY") → env("KEY")
DEBUG = env.bool("DEBUG", default=False)
SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
```

**Fichiers modifiés** :
- `backend/requirements.txt` (retirer `python-decouple`, `dj-database-url`, ajouter `django-environ`)
- `backend/config/settings.py` (remplacer `config()` → `env()`)

**Vérification** : `python manage.py check` + `python manage.py test`

---

## 3. Session 2 — Qualité : Tests & Documentation

**Durée estimée** : 3h
**Impact** : 🟡 DX (Developer Experience)

### 2.1 pytest + model_bakery

**Objectif** : Remplacer Django `TestCase` par pytest.

```bash
pip install pytest pytest-django pytest-cov model_bakery
```

**Fichier** : `backend/pytest.ini` (créer)

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py
addopts = --reuse-db --tb=short -v --strict-markers
```

**Fichier** : `backend/conftest.py` (créer) — voir section 2.2.

**Migration des tests** :

| Étape | Détail |
|---|---|
| 1 | Installer pytest (rétrocompatible avec `unittest.TestCase`) |
| 2 | Créer `pytest.ini` |
| 3 | Lancer `pytest` — les tests existants passent déjà |
| 4 | Créer `conftest.py` avec fixtures |
| 5 | Migrer 1 app à la fois vers les fixtures `model_bakery` |

**Migration d'un test** :

```python
# AVANT (Django TestCase)
class ProductTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com", password="pass")
        self.client = Client()
        self.client.login(email="test@test.com", password="pass")
        self.product = Product.objects.create(seller=self.user, name="Test", price=10)

    def test_product_list(self):
        response = self.client.get("/api/v1/products/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

# APRÈS (pytest + model_bakery)
def test_product_list(authenticated_client, product):
    response = authenticated_client.get("/api/v1/products/")
    assert response.status_code == 200
    assert len(response.json()) == 1
```

---

### 2.2 conftest.py fixtures partagées

**Fichier** : `backend/conftest.py` (créer)

```python
import pytest
from model_bakery import baker
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return baker.make(User, email="test@example.com")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def product(user):
    return baker.make("products.Product", seller=user, name="Test Product", price=10.00)


@pytest.fixture
def cart(user):
    return baker.make("carts.Cart", user=user)


@pytest.fixture
def order(user):
    return baker.make("orders.Order", user=user)
```

---

### 2.3 INDEX.md

**Fichier** : `INDEX.md` (créer)

Structure à reproduire (basée sur VocalFit) :
- Arborescence complète du projet
- Index des endpoints API (méthode + URL + auth + description)
- Index des composants React
- Index des scripts d'infrastructure
- Index des documents de référence

---

## 4. Session 3 — Architecture : UUID & Ops

**Durée estimée** : 4h
**Impact** : 🔴 Sécurité (UUID), 🟢 Production (fail2ban, backup)

### 3.1 UUID PKs (tous les modèles)

**Objectif** : Remplacer les IDs auto-increment par des UUIDs (non énumérables, distributed-system ready).

#### Stratégie de migration (par modèle)

| Étape | Action | Fichiers |
|---|---|---|
| 1 | Ajouter `uuid = UUIDField(null=True, unique=True)` | `models.py` de chaque app |
| 2 | Générer la migration | `python manage.py makemigrations` |
| 3 | Data migration : peupler `uuid` des instances existantes | Fichier migration custom |
| 4 | Rendre `uuid` non-nullable | Seconde migration |
| 5 | Ajouter vue URL alternative `/api/v1/products/<uuid>/` | `urls.py` + `views.py` |
| 6 | Mise à jour du frontend (utiliser UUID dans les URLs) | Composants React |
| 7 | Après validation, rendre `uuid` PK, supprimer `id` | Migration finale |

#### Exemple de data migration

```python
# backend/products/migrations/00xx_populate_product_uuid.py
from django.db import migrations
import uuid

def populate_uuid(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    for product in Product.objects.filter(uuid__isnull=True):
        product.uuid = uuid.uuid4()
        product.save(update_fields=["uuid"])

class Migration(migrations.Migration):
    dependencies = [("products", "00xx_previous")]
    operations = [migrations.RunPython(populate_uuid)]
```

#### Modèles concernés

| App | Modèles |
|---|---|
| `users` | `User` |
| `products` | `Product` |
| `carts` | `Cart`, `CartItem` |
| `orders` | `Order`, `OrderItem` |

#### Impact sur l'API

```python
# AVANT
GET /api/v1/products/1/

# APRÈS (transition)
GET /api/v1/products/1/          # ancien ID continue de fonctionner
GET /api/v1/products/a3f2b1c4-/  # UUID

# APRÈS (final)
GET /api/v1/products/a3f2b1c4-/  # UUID uniquement
```

#### Vue Django avec support UUID

```python
# backend/products/api/views.py
from django.shortcuts import get_object_or_404
import uuid

class ProductDetailView(APIView):
    def get_object(self, pk):
        try:
            uid = uuid.UUID(pk)
            return get_object_or_404(Product, uuid=uid)
        except ValueError:
            return get_object_or_404(Product, pk=int(pk))
```

**Risques** : Migration de données, URLs frontend, relations FK, external consumers.

---

### 3.2 fail2ban (rôle Ansible)

**Objectif** : Protéger le serveur contre les attaques brute-force SSH.

**Fichier** : `infra/ansible/roles/docker/tasks/main.yml`

```yaml
- name: Install fail2ban
  apt:
    name: fail2ban
    state: present

- name: Configure fail2ban SSH jail
  copy:
    dest: /etc/fail2ban/jail.local
    content: |
      [sshd]
      enabled = true
      port = ssh
      filter = sshd
      logpath = /var/log/auth.log
      maxretry = 3
      bantime = 3600
    mode: 0644

- name: Enable fail2ban
  service:
    name: fail2ban
    state: started
    enabled: yes
```

---

### 3.3 DB backup avec rétention

**Objectif** : Ajouter une rétention différenciée (quotidienne 7j + hebdomadaire 30j).

**Fichier** : `infra/scripts/backup-db.sh`

```bash
#!/bin/bash
# Ajout après le pg_dump existant :

# Rotation quotidienne (7 jours)
find "$BACKUP_DIR" -name "clickmart_*.sql.gz" -mtime +7 -delete

# Rotation hebdomadaire (dimanche → copie, 30 jours)
if [ "$(date +%u)" = "7" ]; then
    mkdir -p "$BACKUP_DIR/weekly"
    cp "$BACKUP_FILE" "$BACKUP_DIR/weekly/"
    find "$BACKUP_DIR/weekly/" -name "clickmart_*.sql.gz" -mtime +30 -delete
fi
```

---

## 5. Estimation d'effort

| Session | # | Tâche | Effort | Risque |
|---|---|---|---|---|
| **1** | 1.1 | Sentry backend + frontend | 30 min | Nul |
| **1** | 1.2 | AuthGuard / GuestGuard | 15 min | Nul |
| **1** | 1.3 | apiClient refresh queue | 30 min | Nul |
| **1** | 1.4 | Makefile CI | 20 min | Nul |
| **1** | 1.5 | django-environ | 20 min | Faible |
| | | **Sous-total S1** | **1h55** | |
| **2** | 2.1 | pytest + model_bakery | 1h | Faible |
| **2** | 2.2 | conftest.py fixtures | 30 min | Faible |
| **2** | 2.3 | INDEX.md | 1h | Nul |
| | | **Sous-total S2** | **2h30** | |
| **3** | 3.1 | UUID PKs | 3h | Élevé |
| **3** | 3.2 | fail2ban | 10 min | Nul |
| **3** | 3.3 | DB backup rétention | 10 min | Nul |
| | | **Sous-total S3** | **3h20** | |
| | | **TOTAL** | **~7h45** | |

---

## 6. Ordre d'exécution recommandé

```
Session 1 (Quick Wins, 2h)
│
├── 1.5 django-environ     ← prérequis pour Sentry (SENTRY_DSN)
├── 1.1 Sentry             ← via django-environ
├── 1.4 Makefile CI        ← indépendant
├── 1.2 AuthGuard          ← indépendant
├── 1.3 apiClient refresh  ← dépend conceptuellement d'AuthGuard
│
Session 2 (Qualité, 2h30)
│
├── 2.1 pytest + model_bakery
├── 2.2 conftest.py        ← dépend de pytest
├── 2.3 INDEX.md           ← indépendant
│
Session 3 (Architecture, 3h20)
│
├── 3.1 UUID PKs           ← le plus lourd, à faire en premier
├── 3.2 fail2ban           ← indépendant
├── 3.3 DB backup          ← indépendant

---

## 7. Checklist de suivi

### Phase 1 — Quick Wins (Sécurité & Monitoring)

| # | Tâche | Statut | Date |
|---|---|---|---|
| 1.1 | Sentry — backend (`sentry-sdk[django]`, `settings.py`) | ✅ Fait | 30/07 |
| 1.1 | Sentry — frontend (`@sentry/react`, `main.jsx`) | ✅ Fait | 30/07 |
| 1.1 | Sentry — Ansible template (`SENTRY_DSN` dans `.env.prod.j2`) | ✅ Fait | 30/07 |
| 1.2 | AuthGuard — vérification (PrivateRoute existait déjà) | ✅ Fait | 30/07 |
| 1.2 | GuestGuard — création `GuestRoute.jsx` + wrapper login/register | ✅ Fait | 30/07 |
| 1.3 | apiClient — singleton refresh queue | ✅ Fait | 30/07 |
| 1.4 | Makefile — cibles `api-test`, `api-lint`, `web-test`, `web-lint`, `web-build`, `ci` | ✅ Fait | 30/07 |
| 1.5 | django-environ — remplacer `python-decouple` + `dj-database-url` | ✅ Fait | 30/07 |
| 1.5 | django-environ — vérification tests (67/67 pass) | ✅ Fait | 30/07 |

### Phase 2 — Qualité (Tests & Documentation)

| # | Tâche | Statut | Date |
|---|---|---|---|
| 2.1 | pytest — installer (`pytest`, `pytest-django`, `pytest-cov`) | ✅ Fait | 30/07 |
| 2.1 | pytest — créer `backend/pytest.ini` | ✅ Fait | 30/07 |
| 2.1 | model_bakery — installer + intégrer dans conftest | ✅ Fait | 30/07 |
| 2.2 | conftest.py — fixtures partagées (`user`, `api_client`, `authenticated_client`, `product`, `cart`, `order`) | ✅ Fait | 30/07 |
| 2.2 | Tests — migrer 1 app pilote vers pytest + model_bakery (users) | ✅ Fait | 30/07 |
| 2.2 | Tests — migrer les 3 autres apps (products, carts, orders) | ✅ Fait | 30/07 |
| 2.3 | INDEX.md — arborescence complète du repo | ✅ Fait | 30/07 |
| 2.3 | INDEX.md — index des endpoints API (méthode, URL, auth, description) | ✅ Fait | 30/07 |

### Phase 3 — Architecture (UUID & Ops)

| # | Tâche | Statut | Date |
|---|---|---|---|
| 3.1 | UUID — remplacer `id` par UUIDField PK sur 6 modèles | ✅ Fait | 30/07 |
| 3.1 | UUID — URLs `<uuid:pk>`, serializers nettoyés | ✅ Fait | 30/07 |
| 3.1 | UUID — suppression totale de l'auto-increment (pas de fallback) | ✅ Fait | 30/07 |
| 3.2 | fail2ban — installation + config SSH jail dans rôle Ansible docker | ✅ Fait | 30/07 |
| 3.3 | DB backup — rétention quotidienne 7j + hebdomadaire 30j | ✅ Fait | 30/07 |

### Post-déploiement (après chaque phase)

| # | Tâche | Statut | Date |
|---|---|---|---|
| P1 | Push + vérifier pipeline CI/CD (tests + build + deploy) | ✅ Fait | 30/07 |
| P2 | Mettre à jour `TODO.md` | ✅ Fait | 30/07 |
| P3 | Mettre à jour `GESTION_CICD.md` | ✅ Fait | 30/07 |

---

**Progression globale** : 24/24 tâches (100%) — Toutes les phases complètes ✅
```
