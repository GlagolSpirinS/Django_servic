"""
WSGI config for DjangoProject project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/stable/howto/deployment/wsgi/
"""

import os
import sys
from django.core.wsgi import get_wsgi_application

# --- Настройка путей ---
# Добавляем корневую папку проекта в sys.path
sys.path.insert(0, '/var/www/Django_servic')

# Добавляем папку с Django-приложением (где лежит settings.py)
sys.path.insert(0, '/var/www/Django_servic/DjangoProject')

# Указываем модуль настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoProject.settings')

# --- Запуск WSGI приложения ---
try:
    application = get_wsgi_application()
except Exception as exc:
    # Логируем ошибку в stderr (появится в логах Apache)
    import logging
    logger = logging.getLogger('wsgi')
    logger.exception("Failed to load Django WSGI application")
    raise