import os
import sys
from pathlib import Path
from split_settings.tools import include

import environ

env = environ.Env()
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env files
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

_environment = env("ENVIRONMENT", default="development")
_override_files = {
    "production": BASE_DIR / ".envs" / ".prod",
    "staging": BASE_DIR / ".envs" / ".staging",
}
_override_file = _override_files.get(_environment, BASE_DIR / ".envs" / ".local")
if _override_file.exists():
    environ.Env.read_env(_override_file)

# Determine local settings file
def _is_pytest():
    return os.getenv('PYTEST_RUNNING') == 'true' or 'pytest' in sys.argv[0]

if _is_pytest():
    _local = 'local/unittests.py'
elif _environment == 'production':
    _local = 'local/prod.py'
elif _environment == 'staging':
    _local = 'local/prod.py'
else:
    _local = 'local/dev.py'

# Compose settings in order (later files override earlier ones)
include(
    'base.py',
    'database.py',
    'rest_framework.py',
    'storage.py',
    'email.py',
    'celery.py',
    'security.py',
    'sentry.py',
    'logging_config.py',
    _local,
)

# Env var overrides (CLICKMART_SETTING_*) — last, overrides everything
import json as _json
for _key, _value in os.environ.items():
    if _key.startswith('CLICKMART_SETTING_'):
        _setting_name = _key[19:]
        try:
            _value = _json.loads(_value)
        except (_json.JSONDecodeError, ValueError):
            pass
        globals()[_setting_name] = _value
