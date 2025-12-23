from django.apps import AppConfig

class AdminPanelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admin_panel"
    verbose_name = "Admin Panel"

    def ready(self):
        # Import signals to register them
        from . import signals  # noqa: F401