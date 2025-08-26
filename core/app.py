# core/apps.py
from django.apps import AppConfig
from django.core.cache import caches
from django.db import connection
from django.core.management import call_command

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Проверяем, есть ли таблица кэша
        cache = caches['default']
        if hasattr(cache, 'table') and cache._table is not None:
            table_name = cache._table
            if table_name not in connection.introspection.table_names():
                print(f"Таблица кэша {table_name} не найдена. Создаём...")
                call_command('createcachetable', table_name)