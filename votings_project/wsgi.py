"""
WSGI config for votings_project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "votings_project.settings")

import shutil
from pathlib import Path

# Ejecutar copiado de media_seed a media al iniciar WSGI
base_dir = Path(__file__).resolve().parent.parent
seed_dir = base_dir / 'media_seed'
target_dir = base_dir / 'media'

if seed_dir.exists():
    target_dir.mkdir(exist_ok=True)
    for item in seed_dir.iterdir():
        d = target_dir / item.name
        if item.is_dir():
            shutil.copytree(item, d, dirs_exist_ok=True)
        else:
            if not d.exists():
                shutil.copy2(item, d)

application = get_wsgi_application()
