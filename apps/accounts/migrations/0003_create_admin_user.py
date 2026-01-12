from django.db import migrations
import os


def create_admin_user(apps, schema_editor):
    # ✅ CORRECT APP LABEL
    User = apps.get_model("accounts", "User")

    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    email = os.getenv("ADMIN_EMAIL", "")
    admin_phone = os.getenv("ADMIN_PHONE", "")

    if not username or not password:
        return  # safety exit

    if User.objects.filter(username=username).exists():
        return

    admin = User(
        username=username,
        email=email,
        is_staff=True,
        is_superuser=True,
        is_active=True,
        account_number=admin_phone,
    )

    # ✅ ALWAYS USE THIS
    admin.set_password(password)
    admin.save()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_fix_schema"),
    ]

    operations = [
        migrations.RunPython(create_admin_user),
    ]
