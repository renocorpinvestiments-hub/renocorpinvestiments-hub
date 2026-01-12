# apps/accounts/migrations/0002_create_admin_user.py

from django.db import migrations
import os


def create_admin_user(apps, schema_editor):
    User = apps.get_model("apps_accounts", "User")

    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    email = os.getenv("ADMIN_EMAIL", "")

    # Safety checks
    if not username or not password:
        return  # silently skip if env vars not set

    # Do not create duplicate admin
    if User.objects.filter(username=username).exists():
        return

    admin = User(
        username=username,
        email=email,
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )

    # 🔥 THIS IS CRITICAL
    admin.set_password(password)

    admin.save()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_admin_user),
  ]
