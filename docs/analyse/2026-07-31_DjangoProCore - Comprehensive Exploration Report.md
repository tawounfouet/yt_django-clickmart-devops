Comprehensive Exploration Report: django-pro-core
1. Split Settings Architecture
Entrypoint: src/project/settings/__init__.py
The key insight is the use of the django-split-settings library (split_settings.tools.include) to compose Django settings from multiple files in a specific, ordered sequence.
ENVVAR_SETTINGS_PREFIX = 'SRC_SETTING_'
LOCAL_SETTINGS_PATH = os.getenv(f'{ENVVAR_SETTINGS_PREFIX}LOCAL_SETTINGS_PATH')

if not LOCAL_SETTINGS_PATH:
    LOCAL_SETTINGS_PATH = f'local/settings{".unittests" if is_pytest_running() else ".dev"}.py'
File resolution logic:
- First checks the env var SRC_SETTING_LOCAL_SETTINGS_PATH
- If not set, detects pytest via PYTEST_RUNNING env var or sys.argv[0]
- During pytest runs: local/settings.unittests.py
- During normal runs (including Docker): local/settings.dev.py
- Relative paths are made absolute from BASE_DIR
Inclusion order (this is the entire overloading chain):
1. base.py          ← Django defaults, DEBUG, ALLOWED_HOSTS, INSTALLED_APPS
2. logging.py       ← LOGGING dict
3. rest_framework.py ← DRF + SimpleJWT config
4. channels.py      ← CHANNEL_LAYERS (InMemory)
5. aws.py           ← S3 stubs (empty strings)
6. custom.py        ← App-specific: IN_DOCKER, STOKEN_EXPIRATION_SECONDS, USE_ON_COMMIT_HOOK
7. local/*.py       ← OPTIONAL — dev/unittests overrides
8. envvars.py       ← Environment variable overrides via SRC_SETTING_*
9. docker.py        ← Auto-detect Docker, inject Whitenoise + S3 storage
Overloading mechanism: Later files can directly mutate globals set by earlier files because all files execute in the same module scope (globals()). For example, custom.py sets IN_DOCKER = False, then docker.py reads that value. Templates like settings.dev.py overwrite DEBUG and SECRET_KEY that were set in base.py.
The SRC_SETTING_* / deep_update mechanism
envvars.py (file 4 lines):
from src.general.utils.collections import deep_update
from src.general.utils.settings import get_settings_from_environment

deep_update(globals(), get_settings_from_environment(ENVVAR_SETTINGS_PREFIX))
get_settings_from_environment(prefix) (in src/general/utils/settings.py):
- Iterates all os.environ items
- Filters those starting with SRC_SETTING_
- Strips the prefix to get the setting name
- Parses values as YAML via yaml_coerce() (e.g., '{"default":{"HOST":"db"}}' becomes a Python dict)
deep_update(base_dict, update_with) (in src/general/utils/collections.py):
- Recursively merges nested dicts
- For keys where both values are dicts, recurses; otherwise overwrites
- This means you can pass SRC_SETTING_DATABASES='{"default":{"HOST":"db"}}' and it will only override the HOST key within the default database config, preserving all other database settings
Individual settings files
File	Lines	Key Content
base.py	135	DEBUG=True, SECRET_KEY in hardcoded, ALLOWED_HOSTS=['*'], CORS_ALLOW_ALL_ORIGINS=True, AUTH_USER_MODEL='accounts.Account', INSTALLED_APPS with 5 custom apps + 8 third-party, ASGI_APPLICATION, SQLite default DB
rest_framework.py	15	SIMPLE_JWT with 365-day access token, hardcoded SIGNING_KEY, USER_ID_FIELD='account_number'
channels.py	5	InMemoryChannelLayer — no Redis, messages lost on restart
aws.py	3	Empty string stubs for AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME
custom.py	7	IN_DOCKER=False, STOKEN_EXPIRATION_SECONDS=10, USE_ON_COMMIT_HOOK=True
docker.py	10	Checks IN_DOCKER or /.dockerenv file existence; injects WhiteNoiseMiddleware at position 1, sets S3Boto3Storage for file/static storage
logging.py	27	Console handler at INFO, Django loggers at WARNING, root at DEBUG, section-dev/tmpl overrides add colorlog.ColoredFormatter
Templates (local settings)
Template	Key overrides
settings.dev.py	DEBUG=True, dev SECRET_KEY, colored logging, DEBUG level for src logger
settings.unittests.py	DEBUG=True, colored logging, DEBUG level for src logger (NO SECRET_KEY override — relies on base.py's key)
settings.github.py	DEBUG=True, dev SECRET_KEY (used by CI)
2. Django Channels / WebSocket Setup
ASGI Entrypoint: src/project/asgi.py
application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': URLRouter(websocket_urlpatterns),
})
Daphne serves both HTTP and WebSocket. The ProtocolTypeRouter dispatches by protocol.
WebSocket Routing: src/accounts/routing.py
from src.accounts.consumers import AccountConsumer

websocket_urlpatterns = [
    re_path(r'ws/accounts/(?P<account_number>[a-f0-9]{64})$', AccountConsumer.as_asgi()),
]
A single route pattern: ws/accounts/<64-char-hex-account-number>. Note the regex is case-sensitive (only lowercase hex).
AccountConsumer — Full Implementation (208 lines)
Class: AccountConsumer(JsonWebsocketConsumer)
RPC Protocol Design:
The client sends JSON messages with:
{"method": "<method_name>", "correlation_id": "<id>", ...kwargs...}
The server responds:
{"return_value": <value>, "correlation_id": "<id>"}
Or on error:
{"error": "not such method" | "exception", "correlation_id": "<id>"}
The dispatch is handled in receive_json():
1. Extracts correlation_id and method from the message
2. Looks up rpc_{method_name} attribute via getattr(self, f'rpc_{method_name}', None)
3. Calls with remaining kwargs as **content
4. Sends response with send_rpc_response()
Available RPC methods:
Method	Auth Required	Logic
authenticate(token)	No	Parses SToken format: account_number$ISOdatetime$signature. Validates signature and 10-second expiration. Adds to account group and broadcasts online status
authenticate_signing_key(signing_key)	No	Derives public key from signing key, compares to URL's account_number. Same group/broadcast behavior
set_peers(peers=[...])	Yes	Manages online tracking subscriptions. Diffs current vs new peer list; adds/removes from online_{peer} groups; sends silent pings to new peers
get_peers()	Yes	Returns dict mapping account_number → {"is_online": bool}
SToken Authentication (src/general/authentication.py):
- Format: {account_number}${iso_formatted_datetime}${signature}
- Regex extract: r'^(?P<account_number>[0-9a-f]{64})\$(?P<iso_formatted_datetime>.+?)\$(?P<signature>[0-9a-f]{128})$'
- Validates: (1) regex match, (2) Ed25519 signature of the ISO datetime string, (3) expiration within STOKEN_EXPIRATION_SECONDS (10s default)
- Returns account_number on success, None on failure
Channel Groups:
- account_{account_number} — only the account owner subscribes; receives balance updates and new blocks
- online_{account_number} — peers subscribe to track online/offline status
Event handlers (mapped from MessageType enum):
- create_block → forwards block JSON to client
- update_account → forwards account update JSON to client
- track_online_status → tracks which channel names are online per peer; broadcasts is_online/is_offline to client
- handle_ping → responds with online tracking payload via channel_layer.send()
Out-of-band send function (used by Django models/views):
def send(message_type: MessageType, recipient: str, message: dict):
    channel_layer = channels.layers.get_channel_layer()
    payload = {'type': message_type.value, 'message': message}
    async_to_sync(channel_layer.group_send)(f'account_{recipient}', payload)
Assertion safety check (line 202):
assert all(hasattr(AccountConsumer, item.value.replace('.', '_')) for item in MessageType)
Ensures every MessageType has a corresponding handler method on the consumer.
MessageType enum:
class MessageType(Enum):
    CREATE_BLOCK = 'create.block'
    UPDATE_ACCOUNT = 'update.account'
    HANDLE_PING = 'handle.ping'
    TRACK_ONLINE_STATUS = 'track.online_status'
3. Cryptography and Security
Ed25519 via PyNaCl: src/general/utils/cryptography.py
Core types (from src/general/utils/types.py):
- These use pydantic v1 constrained types:
hexstr = constr(regex=r'^[0-9a-f]+$', strict=True)
class AccountNumber(hexstr64):  min_length=64, max_length=64
class SigningKey(hexstr64):     min_length=64, max_length=64
class Signature(hexstr128):     min_length=128, max_length=128
Key functions:
Function	Input	Output
generate_key_pair()	—	KeyPair(private=hex, public=hex)
derive_public_key(signing_key)	64-char hex private key	64-char hex public key
is_signature_valid(message, verify_key, signature)	bytes, hex, hex	bool
is_dict_signature_valid(dict_, verify_key, signature)	dict, hex, hex	bool
normalize_dict(dict_)	dict	bytes
bytes_to_hex(bytes_)	bytes	hex string
CustomEncoder: Converts UUID to string for deterministic JSON serialization.
Account Model (Key Management): src/accounts/models/account.py
class Account(AbstractBaseUser, PermissionsMixin):
    account_number = CharField(max_length=64, primary_key=True)  # = Ed25519 public key
    balance = PositiveBigIntegerField(default=0)
    display_image = URLField(blank=True)
    display_name = CharField(max_length=50, blank=True)
Critical design choices:
- USERNAME_FIELD = 'account_number' — the public key is the username
- password field (inherited from AbstractBaseUser) stores the hash of the signing key via Django's set_password()
- The id property aliases self.account_number (for DRF compatibility)
- FieldTracker from model-utils detects balance changes; on save, broadcasts UPDATE_ACCOUNT via WebSocket using apply_on_commit()
- has_perm() returns True — bypasses all Django permission checks
- has_module_perms() returns True — gives admin access to everyone
- __str__ exposes balance in logs: f'{self.account_number} | {self.balance}'
AccountManager: src/accounts/managers/account.py
def create_user(self, account_number, password=None, **extra_fields):
    signing_key = password.lower().strip()
    public_key = derive_public_key(signing_key)
    if account_number != public_key:
        raise ValueError('The account number does not match the derived public key')
    user = self.model(account_number=account_number, **extra_fields)
    user.set_password(password)  # Hashes the signing key
    user.save()
    return user
The signing key (private key) is used as the Django password. It's validated by deriving the public key and comparing to the given account_number.
Key Usage Throughout the System
Context	Operation
Account creation	generate_key_pair() → server generates keypair, returns private key to client
Login	Client sends signing key → derive_public_key() → lookup account
Block signature	is_dict_signature_valid() on entire block dict
Config update	is_dict_signature_valid() on config fields
WebSocket SToken	is_signature_valid() on ISO datetime string
WebSocket key auth	derive_public_key() to verify identity
4. Permissions and Serializers
Permissions: src/general/permissions.py
IsAccountOwner:
def has_object_permission(self, request, view, obj):
    if isinstance(request.user, AnonymousUser): return False
    return obj.account_number == request.user.account_number
Used on PATCH /api/accounts/{id}. Compares the authenticated user's account_number (PK) to the object's PK.
IsObjectCreatorOrReadOnly:
def has_object_permission(self, request, view, obj):
    if request.method in permissions.SAFE_METHODS: return True
    return obj.creator == request.user
Used on Comments and Recipes. Read is open; write requires obj.creator == request.user.
Custom Base Serializers: src/general/serializers.py
Three mixin classes forming a hierarchy:
ValidateUnknownFieldsMixin:
- After validation, checks if any field in initial_data is NOT in self.fields (a typo detection for frontend devs)
- Raises ValidationError('Unknown field(s): ...')
- Has a TODO workaround for nested serializers lacking initial_data
ValidateReadonlyFieldsMixin:
- Checks that no field in initial_data is marked as read-only (either via field.read_only or Meta.read_only_fields)
- Raises ValidationError('Readonly field(s): ...')
ValidateFieldsMixin (combines both):
class ValidateFieldsMixin(ValidateUnknownFieldsMixin, ValidateReadonlyFieldsMixin):
    pass
Used by BlockSerializer and ConfigSerializer.
5. Testing Infrastructure
Configuration: pyproject.toml (pytest section)
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "src.project.settings"
django_find_project = false
python_files = "test_*.py"
testpaths = ["src"]
filterwarnings = "ignore::DeprecationWarning:^(?!node\\.).*:"
Conftest: src/conftest.py
os.environ['PYTEST_RUNNING'] = 'true'  # Set before any imports!
from src.accounts.tests.fixtures import *
from src.general.tests.fixtures import *
Critical: Sets PYTEST_RUNNING before importing fixtures, which triggers the is_pytest_running() check in settings/__init__.py to use local/settings.unittests.py.
Fixture Organization
src/accounts/tests/fixtures/accounts.py:
- sender_key_pair — hardcoded KeyPair(public='eb01...', private='acb2...') (deterministic for tests)
- sender_account_number — derived from sender_key_pair.public
- sender_account(account_number, db) — created via baker.make('accounts.Account', account_number=..., balance=20000)
src/general/tests/fixtures/clients.py:
- api_client — DRF APIClient()
src/general/tests/fixtures/misc.py:
- test_settings(settings) — autouse fixture overriding SECRET_KEY with a test-specific value via override_settings()
Existing Tests: src/accounts/tests/test_rest_api.py
Only 1 test across the entire 6-app project:
def test_retrieve_account(sender_account, api_client):
    response = api_client.get(f'/api/accounts/{sender_account.account_number}')
    assert response.status_code == 200
    assert response.json() == {
        'account_number': sender_account.account_number,
        'balance': sender_account.balance,
        'display_image': '',
        'display_name': '',
    }
Test execution: make test
poetry run pytest -v -rs -n auto --show-capture=no
Uses pytest-xdist (-n auto) for parallel test execution. --show-capture=no suppresses captured output. -rs shows skipped test reasons.
6. Dependency Management (Poetry)
pyproject.toml dependencies:
Production dependencies:
Package	Version
python	^3.11
django	^4.2
channels (with daphne)	^4.0.0
djangorestframework	^3.14.0
djangorestframework-simplejwt	^5.2.2
django-cors-headers	^3.14.0
django-filter	^23.2
django-model-utils	^4.3.1
django-split-settings	^1.2.0
django-storages	^1.13.2
boto3	^1.26.137
psycopg2	^2.9.6
pynacl	^1.5.0
pydantic	^1.10.7
pyyaml	^6.0
whitenoise	^6.4.0
gunicorn	^23.0.0
pillow	^9.5.0
python-dotenv	^1.1.1
Dev dependencies:
Package
colorlog
django-debug-toolbar
pre-commit
pytest
pytest-django
pytest-xdist
model-bakery
Tool configuration in pyproject.toml:
- isort: multi_line_output=5, line_length=119
- yapf: Google style, 119 column limit, coalesce brackets
- pytest: settings module, test paths, filter warnings
7. Docker
Dockerfile
FROM python:3.10.4-buster         # Note: pyproject.toml requires ^3.11 — mismatch!
WORKDIR /opt/project
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH .
ENV COOKING_CORE_SETTING_IN_DOCKER true    # Legacy prefix — code reads SRC_SETTING_*
RUN apt-get install build-essential
RUN pip install virtualenvwrapper poetry==1.4.2
COPY poetry.lock pyproject.toml ./
RUN poetry install --no-root
COPY README.md Makefile ./
COPY cooking_core cooking_core              # BROKEN: should be `src`
COPY local local
EXPOSE 8000
COPY scripts/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
docker-compose.yml (production)
services:
  db:
    image: postgres:14.2-alpine
    environment:
      POSTGRES_DB: cooking_core
      POSTGRES_USER: cooking_core
      POSTGRES_PASSWORD: cooking_core
  app:
    build: .
    depends_on: [db]
    environment:
      COOKING_CORE_SETTING_DATABASES: '{"default":{"HOST":"db"}}'           # BROKEN prefix
      COOKING_CORE_SETTING_LOCAL_SETTINGS_PATH: 'local/settings.prod.py'    # BROKEN prefix + file missing
docker-compose.dev.yml
Only the db service (Postgres 14.2-alpine). No app service. Used via make up-dependencies-only.
entrypoint.sh
set -e
poetry run python -m src.manage collectstatic --no-input
poetry run python -m src.manage migrate --no-input
exec poetry run daphne src.project.asgi:application -p 8000 -b 0.0.0.0
Runs collectstatic, then migrate, then starts Daphne (ASGI server) on port 8000. Daphne is used because the project needs both HTTP and WebSocket support through a single protocol router.
8. CI/CD
.github/workflows/pr.yml (Quality Assurance)
name: Quality Assurance
on: [pull_request, workflow_call]

jobs:
  quality-assurance:
    runs-on: ubuntu-latest
    container: python:3.10.4-buster    # BROKEN: requires 3.11
    services:
      db:
        image: postgres:14.2-alpine
    steps:
      - uses: actions/checkout@v2       # Deprecated, should be @v4
      - Install Poetry 1.4.2 (abatilo/actions-poetry@v2.0.0)
      - make install && make install-pre-commit
      - make lint    # pre-commit run --all-files (isort → yapf → flake8 → mypy)
      - make test    # pytest -v -rs -n auto
        env:
          COOKING_CORE_SETTING_DATABASES: '{"default":{"HOST":"db"}}'                          # BROKEN prefix
          COOKING_CORE_SETTING_LOCAL_SETTINGS_PATH: './cooking_core/project/settings/templates/settings.github.py'  # BROKEN path
Critical CI issues (from CRITIQUE.md):
1. Python 3.10.4 in container vs ^3.11 required
2. COOKING_CORE_SETTING_ prefix not recognized — code reads SRC_SETTING_
3. Path ./cooking_core/project/settings/templates/settings.github.py doesn't exist — should be ./src/...
4. actions/checkout@v2 deprecated (Node 12 based)
.github/workflows/master.yml (CI + Deploy)
name: Continuous Integration
on:
  push:
    branches: [master]

concurrency:
  group: master
  cancel-in-progress: true

jobs:
  quality-assurance:
    uses: ./.github/workflows/pr.yml    # Reuses PR workflow

  deploy:
    needs: quality-assurance
    runs-on: ubuntu-latest
    steps:
      - Configure SSH (private key, host, user from GitHub Secrets)
        mkdir -p ~/.ssh/
        echo "$SSH_PRIVATE_KEY" > ~/.ssh/github
        chmod 600 ~/.ssh/github
        StrictHostKeyChecking no
      - ssh target "cd django-pro-core/ && docker-compose down && git pull && docker-compose build && docker-compose up -d --force-recreate"
Deployment issues:
- No health check after docker-compose up -d — CI reports success even if app crashes
- No rollback mechanism
- Migrations run at every container start (race condition with multiple replicas)
- SSH key passed via env var (potential leak in GitHub Actions logs)
- concurrency: group master, cancel-in-progress: true — auto-cancels in-flight deploys
9. Makefile
Full content:
.PHONY: install
install:
	poetry install

.PHONY: install-pre-commit
install-pre-commit:
	poetry run pre-commit uninstall; poetry run pre-commit install

.PHONY: lint
lint:
	poetry run pre-commit run --all-files

.PHONY: migrate
migrate:
	poetry run python -m src.manage migrate

.PHONY: migrations
migrations:
	poetry run python -m src.manage makemigrations

.PHONY: run-server
run-server:
	poetry run python -m src.manage runserver

.PHONY: shell
shell:
	poetry run python -m src.manage shell

.PHONY: superuser
superuser:
	poetry run python -m src.manage createsuperuser

.PHONY: test
test:
	poetry run pytest -v -rs -n auto --show-capture=no

.PHONY: up-dependencies-only
up-dependencies-only:
	test -f .env || touch .env
	docker-compose -f docker-compose.dev.yml up --force-recreate db

.PHONY: update
update: install migrate install-pre-commit ;
Key: test uses -n auto (pytest-xdist parallel), lint runs all pre-commit hooks on all files.
10. CRITIQUE.md (Expert's Own Critique)
Full file: /Users/awf/workspace/learning/openclassrooms/02-parcours-formations/DA. Python _ OCR/P13 - Django CI_CD - Architecture Modulaire  /yt_django-pro-core/CRITIQUE.md (664 lines)
Summary of Findings
Severity	Count	Key Issues
CRITICAL	9	Secrets in the repo (SECRET_KEY, JWT_SIGNING_KEY), select_for_update() without transaction.atomic() enabling double-spend, unauthenticated block creation, has_perm() always returns True, private key transmitted in cleartext, account creation returns private key, assert used for financial invariants (disabled with -O), blocks not immutable
HIGH	12	DEBUG=True / ALLOWED_HOSTS=['*'] / CORS_ALLOW_ALL_ORIGINS=True in base settings, AWS credentials as stubs, double-spend in withdraw, fields='__all__' mass assignment risk, debug_toolbar always installed, InMemoryChannelLayer in production, non-atomic comment/recipe creation, Config singleton race condition, no pagination, no rate limiting
MEDIUM	9	USE_ON_COMMIT_HOOK without active transactions, case-sensitive hex regex, balance exposed in __str__, signing key used as Django password, ConfigSerializer validation order, transaction fee on every comment update, fragile is_dict_signature_valid
LOW	9	Deprecated actions/checkout@v2, deprecated flake8-coding, flake8-import-order conflicts with isort, CORS middleware positioning, non-standard WithdrawSerializer.validate(), inconsistent endpoint /api/withdraw, useless test_settings override, minimal test coverage, wildcard fixture imports
CI BLOCKING	5	Python 3.10 vs 3.11, COOKING_CORE_SETTING_ vs SRC_SETTING_, broken paths cooking_core → src
10 Positive Points Identified
 1. Cryptographic transaction validation (Ed25519/NaCl)
 2. Awareness of select_for_update() for concurrency
 3. transaction.on_commit() pattern for WebSocket notifications
 4. ValidateFieldsMixin for defense in depth
 5. Clean RPC WebSocket with rpc_* dispatch
 6. Public key as user identifier (no email/username)
 7. Modular 6-app Django structure
 8. CustomQuerySet.get_or_none()
 9. Split-settings architecture
10. model-bakery for test fixtures
Prioritized Action Plan
- Phase 1 — Security: Fix transactions, remove hardcoded secrets, stop private key transmission, replace asserts, make blocks immutable, add authentication, fix permissions
- Phase 2 — CI/Deploy: Update Python, fix legacy paths/prefixes, add health checks
- Phase 3 — Quality: Add tests for financial logic, WebSocket, crypto; add pagination
- Phase 4 — Architecture: Redis channel layer, rate limiting, restrict CORS, atomic transactions
Complete File Inventory
Below is every file I read or identified, organized by area:
Root Level
- pyproject.toml, poetry.lock, Makefile, Dockerfile, docker-compose.yml, docker-compose.dev.yml
- .gitignore, .editorconfig, .flake8, .pre-commit-config.yaml, mypy.ini
- README.md, ARCHITECTURE.md, ANALYSE_ARCHITECTURE.md, CRITIQUE.md, CHANGELOG.md, INDEX.md, AGENTS.md
GitHub Actions
- .github/workflows/pr.yml, .github/workflows/master.yml
Settings (src/project/settings/)
- __init__.py, base.py, logging.py, rest_framework.py, channels.py, aws.py, custom.py, envvars.py, docker.py
- templates/settings.dev.py, templates/settings.unittests.py, templates/settings.github.py
Project Config
- src/project/asgi.py, src/project/wsgi.py, src/project/urls.py
- src/manage.py, src/conftest.py
General App (src/general/)
- authentication.py, balance.py, constants.py, exceptions.py, managers.py, permissions.py, serializers.py, validators.py, views.py
- models/__init__.py, models/custom_model.py, models/created_modified.py
- utils/__init__.py, utils/collections.py, utils/cryptography.py, utils/misc.py, utils/pytest.py, utils/settings.py, utils/types.py
- tests/__init__.py, tests/fixtures/__init__.py, tests/fixtures/clients.py, tests/fixtures/misc.py
Accounts App (src/accounts/)
- __init__.py, apps.py, admin.py, consumers.py, routing.py, urls.py
- models/__init__.py, models/account.py
- managers/__init__.py, managers/account.py
- serializers/__init__.py, serializers/account.py
- views/__init__.py, views/account.py
- tests/__init__.py, tests/test_rest_api.py, tests/fixtures/__init__.py, tests/fixtures/accounts.py
- migrations/ (4 files)
Authentication App (src/authentication/)
- __init__.py, apps.py, admin.py
- views/__init__.py, views/login.py
- serializers/__init__.py, serializers/login.py
Blocks App (src/blocks/)
- __init__.py, apps.py, admin.py, urls.py
- models/__init__.py, models/block.py
- serializers/__init__.py, serializers/block.py
- views/__init__.py, views/block.py
- migrations/ (2 files)
Comments App (src/comments/)
- __init__.py, apps.py, admin.py, urls.py
- models/__init__.py, models/comment.py
- serializers/__init__.py, serializers/comment.py
- views/__init__.py, views/comment.py
- filters/__init__.py, filters/comment.py
- migrations/ (6 files)
Config App (src/config/)
- __init__.py, apps.py, admin.py, models.py, views.py, serializers.py, urls.py
- migrations/ (2 files)
Recipes App (src/recipes/)
- __init__.py, apps.py, admin.py, urls.py
- models/__init__.py, models/recipe.py
- serializers/__init__.py, serializers/recipe.py, serializers/withdraw.py
- views/__init__.py, views/recipe.py, views/withdraw.py
- filters/__init__.py, filters/recipe.py
- migrations/ (7 files)
Scripts
- scripts/entrypoint.sh
Other
- archives/, draft/, resources/, .docs/ (directories present but not explored)