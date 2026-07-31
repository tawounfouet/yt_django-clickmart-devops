# Plan d'implémentation — Patterns django-pro-core → ClickMart

> Basé sur l'analyse : `docs/analyse/2026-07-31_ANALYSE_DJANGO_PRO_CORE.md`
> **Objectif** : Adopter les patterns d'architecture professionnelle d'un expert Django
> **Durée estimée** : ~3h30

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Session 1 — Architecture settings + Transactions](#2-session-1--architecture-settings--transactions)
3. [Session 2 — Robustesse + Outillage](#3-session-2--robustesse--outillage)
4. [Quick wins isolés](#4-quick-wins-isolés)
5. [Estimation d'effort](#5-estimation-deffort)
6. [Checklist de suivi](#6-checklist-de-suivi)

---

## 1. Vue d'ensemble

```
┌─────────────────────────────────────────────────────────┐
│           Analyse django-pro-core → ClickMart            │
│                                                          │
│  14 patterns identifiés dans le projet de l'expert       │
│                 ↓                                        │
│  Session 1 (Architecture + Intégrité)                    │
│  ┌─────────────────────────────────────────┐            │
│  │ 1. django-split-settings    (1h30)      │            │
│  │ 2. select_for_update()      (30 min)    │            │
│  │ 3. transaction.on_commit()  (30 min)    │            │
│  └─────────────────────────────────────────┘            │
│                 ↓                                        │
│  Session 2 (Robustesse + Outillage)                     │
│  ┌─────────────────────────────────────────┐            │
│  │ 4. Poetry                   (30 min)    │            │
│  │ 5. ValidateFieldsMixin      (15 min)    │            │
│  │ 6. deep_update env vars     (15 min)    │            │
│  │ 7. Pre-commit mypy          (15 min)    │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  Quick wins (< 5 min chacun)                             │
│  ┌─────────────────────────────────────────┐            │
│  │ 8. Concurrency CI           (1 min)     │            │
│  │ 9. get_or_none()            (5 min)     │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  Patterns non retenus (non applicables)                  │
│  ┌─────────────────────────────────────────┐            │
│  │ FieldTracker (doublon avec signals)     │            │
│  │ Pydantic (doublon avec DRF serializers) │            │
│  │ Channels/WebSocket (hors scope)         │            │
│  │ Ed25519 crypto (hors scope)             │            │
│  │ CRITIQUE.md (déjà couvert par TODO/debug)│           │
│  └─────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Session 1 — Architecture settings + Transactions

**Durée** : 2h30 | **Impact** : 🔴 Critique

### 2.1 django-split-settings (1h30)

**Objectif** : Remplacer le `settings.py` monolithique de 290 lignes par 8 fichiers composables.

#### Arborescence cible

```
backend/config/settings/
├── __init__.py       # include() chain + détection env
├── base.py           # INSTALLED_APPS, MIDDLEWARE, ROOT_URLCONF, TEMPLATES, AUTH_USER_MODEL
├── database.py       # DATABASES (env.db())
├── rest_framework.py # DRF + SimpleJWT + Spectacular + Throttling
├── storage.py        # Media (S3/Cloudinary/local)
├── email.py          # Email (console/SMTP/Resend)
├── celery.py         # Celery + Redis
├── security.py       # CORS, HSTS, SSL redirect, SECURE_* flags
├── sentry.py         # Sentry init conditionnel
├── logging.py        # LOGGING dict
└── local/
    ├── dev.py        # DEBUG=True, SQLite, console email
    ├── unittests.py  # SQLite in-memory, fast password hasher
    └── prod.py       # DEBUG=False, secure flags
```

#### Fichier `__init__.py`

```python
import os
import sys
from pathlib import Path
from split_settings.tools import include

BASE_DIR = Path(__file__).resolve().parent.parent.parent

ENVVAR_SETTINGS_PREFIX = 'CLICKMART_SETTING_'

def is_pytest_running():
    return os.getenv('PYTEST_RUNNING') == 'true' or 'pytest' in sys.argv[0]

if is_pytest_running():
    local_settings = 'local/unittests.py'
else:
    env = os.getenv('ENVIRONMENT', 'development')
    local_settings = {
        'production': 'local/prod.py',
        'staging': 'local/prod.py',
    }.get(env, 'local/dev.py')

include(
    'base.py',
    'database.py',
    'rest_framework.py',
    'storage.py',
    'email.py',
    'celery.py',
    'security.py',
    'sentry.py',
    'logging.py',
    local_settings,
)
```

#### Migration des settings

| Ancien bloc (settings.py) | Nouveau fichier |
|---|---|
| Lignes 1-54 (imports, BASE_DIR, SECRET_KEY, DEBUG, ALLOWED_HOSTS, INSTALLED_APPS, MIDDLEWARE, ROOT_URLCONF, TEMPLATES, WSGI, AUTH_USER_MODEL) | `base.py` |
| Lignes 90-104 (DATABASES) | `database.py` |
| Lignes 193-262 (REST_FRAMEWORK, SIMPLE_JWT, SPECTACULAR, Throttling) | `rest_framework.py` |
| Lignes 151-184 (MEDIA_STORAGE_BACKEND, S3/Cloudinary/local) | `storage.py` |
| Lignes 214-229 (EMAIL_BACKEND_TYPE, Resend/SMTP/console) | `email.py` |
| Lignes 248-253 (CELERY) | `celery.py` |
| Lignes 231-246 (CORS, HSTS, SSL, SECURE_*) | `security.py` |
| Lignes 46-55 (Sentry) | `sentry.py` |
| Lignes 264-290 (LOGGING) | `logging.py` |
| env-dependent overrides | `local/dev.py`, `local/unittests.py`, `local/prod.py` |

#### Vérification

```bash
pip install django-split-settings
python manage.py check
python -m pytest -q  # 64 tests doivent passer
python manage.py runserver  # Dev doit fonctionner
```

**Risques** : Import circulaire si mal ordonné, settings_test non couvert.

---

### 2.2 select_for_update() — Anti race-condition (30 min)

**Objectif** : Empêcher les commandes concurrentes de créer un stock négatif.

#### Scénario corrigé

```python
# orders/api/views.py
from django.db import transaction
from django.db.models import F

class PlaceOrderView(APIView):
    @transaction.atomic
    def post(self, request):
        cart = request.user.cart
        
        if not cart.items.exists():
            return Response({'error': 'Cart is empty'}, status=400)
        
        for item in cart.items.select_related('product'):
            # Verrouille la ligne produit jusqu'à la fin de la transaction
            product = Product.objects.select_for_update().get(pk=item.product.pk)
            
            if product.stock < item.quantity:
                raise ValidationError(f"Stock insuffisant pour {product.name}")
            
            Product.objects.filter(pk=product.pk).update(
                stock=F('stock') - item.quantity
            )
        
        # Créer la commande...
        order = Order.objects.create(user=request.user, ...)
        
        transaction.on_commit(lambda: send_order_confirmation_email.delay(order.id))
        
        return Response(OrderSerializer(order).data, status=201)
```

#### Test ajouté

```python
def test_concurrent_orders_no_negative_stock(db, authenticated_client, product):
    """Deux commandes simultanées sur stock=5 ne doivent pas créer stock<0."""
    product.stock = 1
    product.save()
    # ... simuler deux requêtes concurrentes ...
```

**Fichiers modifiés** : `orders/api/views.py`

---

### 2.3 transaction.on_commit() — Celery tasks (30 min)

**Objectif** : Les tâches Celery ne s'exécutent qu'après le commit de la transaction.

#### Pattern

```python
# AVANT (risqué — la tâche peut s'exécuter avant le commit)
order = Order.objects.create(...)
send_order_confirmation_email.delay(order.id)

# APRÈS (sûr — la tâche attend le commit)
from django.db import transaction

order = Order.objects.create(...)
transaction.on_commit(lambda: send_order_confirmation_email.delay(order.id))
```

#### Fichiers à auditer

```bash
grep -rn "\.delay\|\.apply_async" backend/orders/ backend/carts/ backend/users/
```

**Fichiers modifiés** : `orders/api/views.py`, tout fichier avec appel Celery après une écriture DB.

---

## 3. Session 2 — Robustesse + Outillage

**Durée** : 1h15 | **Impact** : 🟡 Qualité

### 3.1 Poetry (30 min)

**Objectif** : Remplacer `requirements.txt` par Poetry pour la reproductibilité.

```bash
cd backend
pip install poetry
poetry init --name clickmart-backend --python "^3.11"
poetry add django@^5.2 djangorestframework@^3.16 django-cors-headers ...
poetry add --group dev pytest@^9.1 pytest-django@^4.12 model-bakery@^1.24 ruff
poetry lock
```

#### Adaptation Dockerfile

```dockerfile
# AVANT
COPY requirements.txt .
RUN pip install -r requirements.txt

# APRÈS
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev --no-root
```

**Fichiers modifiés** : `pyproject.toml` (nouveau), `poetry.lock` (nouveau), `Dockerfile`, CI workflow.

---

### 3.2 ValidateFieldsMixin (15 min)

**Objectif** : Rejeter les champs inconnus dans les requêtes API (typo detection).

#### Implémentation

```python
# backend/core/mixins.py (créer)
from rest_framework import serializers

class ValidateFieldsMixin:
    """Reject unknown fields in API requests."""
    
    def validate(self, attrs):
        attrs = super().validate(attrs)
        unknown = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown:
            raise serializers.ValidationError({
                serializers.NON_FIELD_ERRORS_KEY: 
                f'Unknown field(s): {", ".join(sorted(unknown))}'
            })
        return attrs

# Utilisation
class ProductSerializer(ValidateFieldsMixin, serializers.ModelSerializer):
    ...
```

#### Serializers à mettre à jour

Tous les serializers d'API (users, products, carts, orders). Priorité : ceux qui acceptent des writes (POST/PATCH).

**Fichiers modifiés** : `core/mixins.py` (nouveau), tous les `*/api/serializers.py`.

---

### 3.3 deep_update + env var overrides (15 min)

**Objectif** : Permettre la surcharge de n'importe quel setting via `CLICKMART_*`.

```python
# config/settings/__init__.py (ajout après le include())
import json

def apply_env_overrides(prefix='CLICKMART_SETTING_'):
    for key, value in os.environ.items():
        if key.startswith(prefix):
            setting_name = key[len(prefix):]
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                pass
            globals()[setting_name] = value

apply_env_overrides()
```

Usage :
```bash
CLICKMART_SETTING_DEBUG=false
CLICKMART_SETTING_DATABASES='{"default":{"HOST":"custom-db"}}'
```

**Fichier modifié** : `config/settings/__init__.py`.

---

### 3.4 Pre-commit mypy + hooks supplémentaires (15 min)

**Objectif** : Ajouter le typage statique et des checks de sécurité.

```yaml
# .pre-commit-config.yaml — ajouts

- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v4.6.0
  hooks:
    - id: detect-private-key
    - id: check-merge-conflict
    - id: check-yaml

- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.10.0
  hooks:
    - id: mypy
      args: [--ignore-missing-imports]
      additional_dependencies: [django-stubs, djangorestframework-stubs]
```

**Fichier modifié** : `.pre-commit-config.yaml`.

---

## 4. Quick wins isolés

### 4.1 Concurrency CI (1 min)

```yaml
# .github/workflows/ci-cd.yml — ajout en haut après 'on:'
concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: true
```

**Effet** : Si deux pushs arrivent sur `main`, le premier déploiement est annulé, seul le dernier s'exécute.

### 4.2 get_or_none() (5 min)

```python
# backend/core/managers.py (créer)
from django.db import models

class BaseQuerySet(models.QuerySet):
    def get_or_none(self, **kwargs):
        try:
            return self.get(**kwargs)
        except self.model.DoesNotExist:
            return None

class BaseManager(models.Manager):
    def get_queryset(self):
        return BaseQuerySet(self.model, using=self._db)
```

**Fichiers modifiés** : `core/managers.py` (nouveau), tous les modèles (hériter de `BaseManager`).

---

## 5. Estimation d'effort

| Session | # | Tâche | Effort | Risque |
|---|---|---|---|---|
| **1** | 2.1 | django-split-settings | 1h30 | Moyen |
| **1** | 2.2 | select_for_update() | 30 min | Faible |
| **1** | 2.3 | transaction.on_commit() | 30 min | Faible |
| | | **Sous-total S1** | **2h30** | |
| **2** | 3.1 | Poetry | 30 min | Faible |
| **2** | 3.2 | ValidateFieldsMixin | 15 min | Nul |
| **2** | 3.3 | deep_update env vars | 15 min | Nul |
| **2** | 3.4 | Pre-commit mypy | 15 min | Nul |
| | | **Sous-total S2** | **1h15** | |
| **Quick** | 4.1 | Concurrency CI | 1 min | Nul |
| **Quick** | 4.2 | get_or_none() | 5 min | Nul |
| | | **Sous-total Quick** | **6 min** | |
| | | **TOTAL** | **~3h50** | |

---

## 6. Checklist de suivi

### Session 1 — Architecture + Intégrité

| # | Tâche | Effort | Statut |
|---|---|---|---|
| 1.1 | `pip install django-split-settings` | 5 min | ⬜ |
| 1.2 | Créer `config/settings/__init__.py` avec `include()` | 15 min | ⬜ |
| 1.3 | Splitter `settings.py` → 8 fichiers | 45 min | ⬜ |
| 1.4 | Créer `local/dev.py`, `unittests.py`, `prod.py` | 15 min | ⬜ |
| 1.5 | Vérifier `python manage.py check` + `pytest` | 10 min | ⬜ |
| 1.6 | Ajouter `select_for_update()` dans PlaceOrderView | 20 min | ⬜ |
| 1.7 | Ajouter test de race condition | 10 min | ⬜ |
| 1.8 | Wrapper les appels Celery avec `transaction.on_commit()` | 20 min | ⬜ |
| 1.9 | Auditer les appels `.delay()` restants | 10 min | ⬜ |

### Session 2 — Robustesse + Outillage

| # | Tâche | Effort | Statut |
|---|---|---|---|
| 2.1 | `poetry init` + `poetry add` toutes les dépendances | 15 min | ⬜ |
| 2.2 | Adapter `Dockerfile` (poetry install) | 10 min | ⬜ |
| 2.3 | Mettre à jour CI (poetry au lieu de pip) | 5 min | ⬜ |
| 2.4 | Créer `core/mixins.py` — `ValidateFieldsMixin` | 10 min | ⬜ |
| 2.5 | Appliquer le mixin aux serializers d'API | 5 min | ⬜ |
| 2.6 | Ajouter `apply_env_overrides()` dans settings | 10 min | ⬜ |
| 2.7 | Tester avec `CLICKMART_SETTING_DEBUG=false` | 5 min | ⬜ |
| 2.8 | Ajouter mypy au pre-commit | 10 min | ⬜ |
| 2.9 | Tester `pre-commit run --all-files` | 5 min | ⬜ |

### Quick wins

| # | Tâche | Effort | Statut |
|---|---|---|---|
| 3.1 | Ajouter `concurrency` dans `ci-cd.yml` | 1 min | ⬜ |
| 3.2 | Créer `core/managers.py` — `get_or_none()` | 5 min | ⬜ |
| 3.3 | Appliquer `get_or_none()` dans les vues | 5 min | ⬜ |

---

**Progression** : 0/21 tâches (0%)
