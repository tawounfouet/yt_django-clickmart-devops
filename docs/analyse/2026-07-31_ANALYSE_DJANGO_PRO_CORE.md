# Analyse comparative — django-pro-core → ClickMart

> - **Date** : 2026-07-31
> - **Source** : django-pro-core (`/Users/awf/workspace/learning/openclassrooms/02-parcours-formations/DA. Python _ OCR/P13 - Django CI_CD - Architecture Modulaire  /yt_django-pro-core`)
> - **Cible** : ClickMart (`yt_django-clickmart-devops`)
> - **Auteur** : Expert Django (YouTube), projet éducatif mais architecture avancée

---

## Résumé exécutif

django-pro-core est un projet éducatif conçu par un expert Django pour démontrer une architecture professionnelle. Malgré ses défauts (secrets dans le repo, `DEBUG=True`, tests quasi absents), il met en œuvre des patterns de qualité production que ClickMart peut adopter. L'auteur a lui-même documenté ses lacunes dans `CRITIQUE.md` (664 lignes).

**14 patterns identifiés**, dont **6 prioritaires** pour ClickMart.

---

## Tableau comparatif global

| Dimension | django-pro-core | ClickMart | Gap |
|---|---|---|---|
| **Settings** | `django-split-settings` (8 fichiers) | `settings.py` monolithique (290 lignes) | 🔴 Architecture |
| **Dépendances** | Poetry + `poetry.lock` | `requirements.txt` sans lock | 🟡 Reproductibilité |
| **Lint** | isort + yapf + flake8 + mypy (pre-commit) | Ruff seul | 🟡 Qualité |
| **Serializers** | `ValidateFieldsMixin` (unknown/readonly) | DRF standard | 🟢 Robustesse |
| **Transactions** | `select_for_update()` + `on_commit()` | Aucune gestion transactionnelle | 🔴 Intégrité |
| **Env vars** | `SRC_SETTING_*` → `deep_update()` | `config()` individuel (decouple → environ) | 🟡 Flexibilité |
| **Django model utils** | `FieldTracker`, `get_or_none()` | Non utilisé | 🟡 Utilitaires |
| **Types** | Pydantic `constr(regex=...)` | Pas de validation de types | 🟢 Validation |
| **CI/CD** | `concurrency: cancel-in-progress` | Pas de concurrency | 🟡 CI |
| **Critique** | `CRITIQUE.md` (auto-audit) | Aucun | 🟢 Qualité |
| **Tests** | 1 test (mais infra pytest-xdist) | 64 tests pytest | ✅ ClickMart gagne |
| **WebSocket** | Django Channels + Daphne | Aucun | — |
| **Crypto** | Ed25519 signatures | Aucun | — |

---

## 1. django-split-settings — 🔴 Priorité HAUTE

### Contexte

django-pro-core :
```python
# src/project/settings/__init__.py
from split_settings.tools import include

ENVVAR_SETTINGS_PREFIX = 'SRC_SETTING_'

include(
    'base.py',           # 1. Django defaults
    'logging.py',        # 2. Logging
    'rest_framework.py', # 3. DRF + JWT
    'channels.py',       # 4. Channels
    'aws.py',            # 5. S3 stubs
    'custom.py',         # 6. App constants
    local_settings_path, # 7. Dev/unittests overrides
    'envvars.py',        # 8. Environment variable overrides
    'docker.py',         # 9. Auto-detect Docker
)
```

ClickMart : un seul fichier `config/settings.py` de 290 lignes qui mélange tout.

### Pourquoi c'est important

| Problème | Monolithique | Split-settings |
|---|---|---|
| **Lisibilité** | 290 lignes à scroller | 8 fichiers de ~30 lignes chacun |
| **Environnements** | Conditions `if DEBUG` partout | Fichier par environnement |
| **Revue de code** | Toute modif touche 1 gros fichier | Modif isolée dans le fichier concerné |
| **Onboarding** | "Lis settings.py" (290 lignes) | "Lis base.py, puis ce qui t'intéresse" |

### Implémentation pour ClickMart

```bash
pip install django-split-settings
```

```
backend/config/settings/
├── __init__.py       # include() chain
├── base.py           # Django core (INSTALLED_APPS, MIDDLEWARE, AUTH_USER_MODEL)
├── database.py       # DATABASES (env.db())
├── rest_framework.py # DRF + SimpleJWT + Spectacular
├── storage.py        # Media (S3/Cloudinary/local)
├── email.py          # Email backends (console/SMTP/Resend)
├── celery.py         # Celery + Redis
├── security.py       # CORS, HSTS, SSL redirect
├── sentry.py         # Sentry init
├── logging.py        # LOGGING dict
└── local/
    ├── dev.py        # DEBUG=True, SQLite
    ├── unittests.py  # SQLite, task_always_eager
    └── prod.py       # DEBUG=False, PostgreSQL
```

### Ordre d'inclusion

```python
# __init__.py
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
    local_settings_path,  # dev/unittests/prod
)
```

**Effort** : 1 session (~1h30). **Risque** : Refactoring, nécessite test complet.

---

## 2. Poetry — 🟡 Priorité MOYENNE

### Contexte

django-pro-core :
```toml
[tool.poetry.dependencies]
python = "^3.11"
django = "^4.2"
djangorestframework = "^3.14.0"
# ... 20 packages avec versions exactes
```

ClickMart :
```
Django>=5.2,<6.0
djangorestframework==3.16.1
# ... mix de >= et ==, pas de lock file
```

### Avantages Poetry

| Fonctionnalité | requirements.txt | Poetry |
|---|---|---|
| **Lock file** | Non (`pip freeze` manuel) | `poetry.lock` (hashé, reproductible) |
| **Dev dependencies** | Mélangé ou fichier séparé | `[tool.poetry.group.dev.dependencies]` |
| **Résolution de dépendances** | Manuelle | Automatique (SAT solver) |
| **Virtual env** | Manuel | Automatique |
| **Publication** | setup.py séparé | Intégré |

### Migration

```bash
pip install poetry
cd backend && poetry init
poetry add django djangorestframework ...
poetry add --group dev pytest model-bakery ruff
```

**Effort** : 30 min. **Risque** : Changement d'outil, Dockerfile à adapter.

---

## 3. ValidateFieldsMixin — 🟢 Priorité MOYENNE

### Contexte

django-pro-core :
```python
class ValidateUnknownFieldsMixin:
    """Rejette les champs inconnus dans la requête (typo detection)."""
    def validate(self, attrs):
        attrs = super().validate(attrs)
        unknown_fields = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown_fields:
            raise ValidationError({'non_field_errors': f'Unknown field(s): {", ".join(sorted(unknown_fields))}'})
        return attrs

class ValidateReadonlyFieldsMixin:
    """Rejette les écritures sur les champs read-only."""
    def validate(self, attrs):
        attrs = super().validate(attrs)
        readonly_fields = {
            field for field in self.initial_data
            if field in self.fields and self.fields[field].read_only
        }
        if readonly_fields:
            raise ValidationError(...)
        return attrs

class ValidateFieldsMixin(ValidateUnknownFieldsMixin, ValidateReadonlyFieldsMixin):
    pass
```

ClickMart : Serializers DRF standards, aucune validation de champs inconnus/readonly.

### Pourquoi c'est utile

| Scénario | Sans le mixin | Avec le mixin |
|---|---|---|
| `{"emial": "test@..."}` (typo) | Accepté silencieusement, email pas mis à jour | `400: Unknown field: emial` |
| `{"id": "hacked-value"}` | Accepté si pas explicitement bloqué | `400: Readonly field: id` |

### Implémentation

```python
# backend/core/mixins.py
class ValidateFieldsMixin:
    def validate(self, attrs):
        attrs = super().validate(attrs)
        unknown = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown:
            raise serializers.ValidationError(
                {serializers.NON_FIELD_ERRORS_KEY: f'Unknown field(s): {", ".join(sorted(unknown))}'}
            )
        return attrs
```

**Effort** : 15 min (créer + appliquer aux serializers). **Risque** : Nul.

---

## 4. select_for_update() + transaction.on_commit() — 🔴 Priorité HAUTE

### Contexte

django-pro-core (malgré son bug — pas de `transaction.atomic()` englobant) :
```python
# blocks/models/block.py
def save(self, **kwargs):
    sender = Account.objects.select_for_update().get(account_number=self.sender)
    recipient = Account.objects.select_for_update().get(account_number=self.recipient)
    # ... atomic balance update ...
    super().save()
```

ClickMart : `PlaceOrderView` déduit le stock sans `select_for_update()`. Si deux utilisateurs passent commande simultanément sur le même produit, le stock peut devenir négatif (race condition).

### Scénario de race condition sur ClickMart

```
T1: User A lit stock=5 → commande de 3 → stock=2
T2: User B lit stock=5 → commande de 4 → stock=1
Résultat: stock=-1 (incohérent !)
```

### Solution

```python
# orders/api/views.py
from django.db import transaction

class PlaceOrderView(APIView):
    @transaction.atomic
    def post(self, request):
        cart = request.user.cart
        for item in cart.items.all():
            product = Product.objects.select_for_update().get(pk=item.product.pk)
            if product.stock < item.quantity:
                raise ValidationError(f"Stock insuffisant pour {product.name}")
            product.stock -= item.quantity
            product.save()
        # ... créer la commande ...
```

**Effort** : 30 min. **Risque** : Faible, changement localisé.

---

## 5. `deep_update` + env var overrides — 🟡 Priorité MOYENNE

### Contexte

django-pro-core :
```python
# envvars.py
deep_update(globals(), get_settings_from_environment('SRC_SETTING_'))
```

Permet de surcharger N'IMPORTE QUEL setting via variable d'environnement :

```bash
SRC_SETTING_DATABASES='{"default":{"HOST":"custom-db"}}'
SRC_SETTING_DEBUG='false'
```

ClickMart : `config('KEY')` pour chaque variable, impossible de surcharger un setting imbriqué.

### Implémentation simplifiée

```python
# config/settings.py (avec django-environ déjà en place)
import json

def apply_env_overrides(prefix='CLICKMART_'):
    """Override any Django setting via CLICKMART_* env vars."""
    for key, value in os.environ.items():
        if key.startswith(prefix):
            setting_name = key[len(prefix):].lower()
            try:
                value = json.loads(value)  # Parse JSON (dict, list, bool, int)
            except (json.JSONDecodeError, ValueError):
                pass  # Keep as string
            globals()[setting_name] = value

apply_env_overrides()
```

Usage :
```bash
CLICKMART_DEBUG=false
CLICKMART_DATABASES='{"default":{"HOST":"backup-db"}}'
```

**Effort** : 15 min. **Risque** : Nul.

---

## 6. FieldTracker pour les signaux — 🟢 Priorité BASSE

### Contexte

django-pro-core :
```python
from model_utils import FieldTracker

class Account(models.Model):
    balance = models.PositiveBigIntegerField(default=0)
    tracker = FieldTracker(fields=['balance'])

    def save(self, **kwargs):
        if self.tracker.has_changed('balance'):
            transaction.on_commit(lambda: send(MessageType.UPDATE_ACCOUNT, self.account_number, {...}))
        super().save()
```

ClickMart pourrait l'utiliser pour :
- Notifier l'admin quand une commande change de statut
- Logger les changements de prix
- Déclencher des tâches Celery conditionnelles

**Effort** : 15 min. **Risque** : Nul.

---

## 7. Pre-commit hooks avancés — 🟡 Priorité MOYENNE

### Contexte

django-pro-core :
```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: isort
    - id: yapf
    - id: flake8
    - id: mypy
```

ClickMart :
```yaml
# .pre-commit-config.yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  hooks:
    - id: ruff
    - id: ruff-format
```

### Ajouts recommandés

1. **mypy** — typage statique, détecte les erreurs avant l'exécution
2. **check for forbidden imports** — empêche `from decouple import config` (déjà en CI, à ajouter en pre-commit)

```yaml
- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v4.6.0
  hooks:
    - id: check-added-large-files
    - id: detect-private-key
    - id: check-yaml
    - id: check-merge-conflict
```

**Effort** : 15 min. **Risque** : Nul.

---

## 8. Concurrency CI — 🟡 Priorité BASSE

### Contexte

django-pro-core :
```yaml
# master.yml
concurrency:
  group: master
  cancel-in-progress: true
```

ClickMart n'a pas de `concurrency` dans `ci-cd.yml`. Si deux pushs arrivent rapidement, deux déploiements concurrents peuvent s'exécuter.

### Implémentation

```yaml
# ci-cd.yml
concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: true
```

**Effort** : 1 ligne. **Risque** : Nul.

---

## 9. `get_or_none()` — 🟢 Priorité BASSE

### Contexte

django-pro-core :
```python
class CustomQuerySet(models.QuerySet):
    def get_or_none(self, **kwargs):
        try:
            return self.get(**kwargs)
        except self.model.DoesNotExist:
            return None
```

Utilisation :
```python
product = Product.objects.filter(is_active=True).get_or_none(pk=uuid)
if product is None:
    raise Http404
```

Plus propre que :
```python
try:
    product = Product.objects.get(pk=uuid, is_active=True)
except Product.DoesNotExist:
    raise Http404
```

**Effort** : 5 min. **Risque** : Nul.

---

## 10. Pydantic pour la validation de types — 🟢 Priorité BASSE

### Contexte

django-pro-core :
```python
from pydantic import constr

hexstr64 = constr(regex=r'^[0-9a-f]{64}$')
class AccountNumber(hexstr64):
    """64-char hex Ed25519 public key."""
```

Pour ClickMart, Pydantic pourrait valider :
```python
from pydantic import BaseModel, constr, condecimal

class ProductCreate(BaseModel):
    name: constr(min_length=1, max_length=200)
    price: condecimal(max_digits=6, decimal_places=2, gt=0)
    stock: int = Field(ge=0)
```

Mais DRF serializers font déjà ce travail. Pydantic serait redondant.

**Effort** : Non applicable à ClickMart.

---

## 11. CRITIQUE.md — 🟢 Priorité BASSE

### Contexte

django-pro-core a un `CRITIQUE.md` de 664 lignes où l'auteur documente lui-même les failles de son projet (9 critiques, 12 hautes, 9 moyennes, 9 basses). C'est un exercice d'humilité technique et de transparence.

ClickMart pourrait bénéficier d'un audit similaire, mais le `TODO.md` et `docs/debug/` remplissent déjà partiellement ce rôle.

---

## 12. Settings templates par environnement — 🟡 Priorité MOYENNE

### Contexte

django-pro-core :
```
templates/
├── settings.dev.py        # DEBUG=True, colored logs, Django Debug Toolbar
├── settings.unittests.py  # task_always_eager, fast password hasher
└── settings.github.py     # CI-specific
```

ClickMart utilise déjà `.envs/.local`, `.envs/.staging`, `.envs/.prod` pour les variables d'environnement, mais les settings Python (hôtes, debug toolbar, etc.) sont dans le `settings.py` monolithique.

Avec `django-split-settings`, on pourrait avoir :
```
local/
├── dev.py        # DEBUG=True, INTERNAL_IPS, Debug Toolbar
├── unittests.py  # PASSWORD_HASHERS, task_always_eager
└── prod.py       # DEBUG=False, SECURE_SSL_REDIRECT
```

**Effort** : Inclus dans le split-settings (#1).

---

## 13. `transaction.on_commit()` pour les side effects — 🔴 Priorité HAUTE

### Contexte

django-pro-core :
```python
# Après sauvegarde d'un block :
transaction.on_commit(lambda: send(MessageType.CREATE_BLOCK, recipient, message))
```

ClickMart : les tâches Celery sont appelées directement dans les vues, sans `on_commit()`. Si la transaction échoue après l'appel Celery, la tâche s'exécute quand même sur des données inconsistantes.

### Implémentation

```python
# orders/api/views.py
from django.db import transaction

@transaction.atomic
def post(self, request):
    order = Order.objects.create(...)
    # La tâche ne sera exécutée que si la transaction commit
    transaction.on_commit(lambda: send_order_confirmation_email.delay(order.id))
    return Response(...)
```

**Effort** : 30 min (identifier + wrapper les appels Celery). **Risque** : Faible, pattern standard Django.

---

## 14. Un appel Makefile unifié — 🟢 Priorité BASSE

### Contexte

django-pro-core :
```makefile
make install              # poetry install
make lint                 # pre-commit run --all-files
make test                 # pytest -v -rs -n auto
make up-dependencies-only # Docker PostgreSQL uniquement
```

ClickMart a déjà `make ci`, `make api-test`, `make api-lint`, etc. Le pattern est déjà adopté.

---

## Synthèse : Plan d'action

### Session 1 — Architecture settings + Transactions (effort 2h)

| # | Action | Pattern source | Effort | Impact |
|---|---|---|---|---|
| 1 | **django-split-settings** | #1 | 1h30 | 🔴 Architecture |
| 2 | **select_for_update()** sur PlaceOrderView | #4 | 30 min | 🔴 Intégrité |
| 3 | **transaction.on_commit()** pour Celery | #13 | 30 min | 🔴 Intégrité |

### Session 2 — Robustesse + Outillage (effort 1h30)

| # | Action | Pattern source | Effort | Impact |
|---|---|---|---|---|
| 4 | **Poetry** | #2 | 30 min | 🟡 Reproductibilité |
| 5 | **ValidateFieldsMixin** | #3 | 15 min | 🟢 Robustesse |
| 6 | **deep_update + env vars** | #5 | 15 min | 🟡 Flexibilité |
| 7 | **Pre-commit mypy + hooks** | #7 | 15 min | 🟡 Qualité |
| 8 | **Concurrency CI** | #8 | 1 ligne | 🟡 CI |
| 9 | **get_or_none()** | #9 | 5 min | 🟢 DX |

### Quick wins (< 30 min, tout impact)

- `select_for_update()` — 30 min, 🔴
- `transaction.on_commit()` — 30 min, 🔴
- `ValidateFieldsMixin` — 15 min, 🟢
- `Concurrency CI` — 1 min, 🟡
- `get_or_none()` — 5 min, 🟢

---

## Ce que ClickMart fait déjà mieux

| Aspect | ClickMart | django-pro-core |
|---|---|---|
| **Tests** | 64 tests (pytest) | 1 test |
| **Sentry** | Configuré (back+front) | Aucun |
| **UUID PKs** | Partout | UUID sur Block, hex sur Account |
| **Celery** | Async tasks | Synchrone |
| **Docker CI/CD** | Build images → pull | Build sur le serveur |
| **Multi-env** | dev/stg/prod | Pas de staging |
| **Ansible IaC** | From-scratch | Manuel |
| **API docs** | drf-spectacular | Aucun |
| **Lint strict** | CI bloque si erreurs | `|| true` implicite |
