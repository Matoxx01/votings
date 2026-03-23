"""
Settings específicos para tests.
Usa SQLite en memoria para no requerir conexión a MySQL.
"""
from .settings import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Desactivar logging ruidoso en tests
LOGGING = {}
