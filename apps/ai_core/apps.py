# apps/ai_core/apps.py

from django.apps import AppConfig


class AiCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_core"
    verbose_name = "AI Core"

    def ready(self):
        # Correct relative import
        from . import signals  # noqa: F401