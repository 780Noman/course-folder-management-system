from django.apps import AppConfig


class FoldersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'folders'

    def ready(self):
        from . import signals  # noqa: F401  (register signal handlers)
