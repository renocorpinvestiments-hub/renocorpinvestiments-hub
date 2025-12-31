from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_admin_user(apps, schema_editor):
    User = apps.get_model("accounts", "User")

    username = "Reno@#2569"
    password = "Veron1c@321"
    email = "degabrantajoseph@gmail.com"
    admin_phone = "+256753310698"  # ✅ REAL phone number

    if not User.objects.filter(username=username).exists():
        User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            is_staff=True,
            is_superuser=True,
            is_active=True,
            account_number=admin_phone
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_fix_schema"),
    ]

    operations = [
        migrations.RunPython(create_admin_user),
    ]
