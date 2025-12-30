from django.apps import AppConfig
from django.db import transaction

class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        from .models import User

        try:
            with transaction.atomic():
                broken_users = User.objects.filter(
                    account_number__isnull=True
                ) | User.objects.filter(account_number="")

                for user in broken_users:
                    user.account_number = f"TEMP-{user.id}"
                    user.save(update_fields=["account_number"])
        except Exception:
            pass
