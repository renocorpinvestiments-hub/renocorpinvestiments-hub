from django.core.management.base import BaseCommand
from django.db import connection, transaction
from apps.accounts.models import User

class Command(BaseCommand):
    help = "Repairs broken account_number uniqueness"

    def handle(self, *args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute('''
                ALTER TABLE accounts_user
                DROP CONSTRAINT IF EXISTS accounts_user_account_number_key;
            ''')

        with transaction.atomic():
            broken = User.objects.filter(account_number__isnull=True) | User.objects.filter(account_number="")

            for u in broken:
                u.account_number = f"TEMP-{u.id}"
                u.save(update_fields=["account_number"])

        with connection.cursor() as cursor:
            cursor.execute('''
                ALTER TABLE accounts_user
                ADD CONSTRAINT accounts_user_account_number_key UNIQUE (account_number);
            ''')

        self.stdout.write(self.style.SUCCESS("✔ account_number repaired"))
