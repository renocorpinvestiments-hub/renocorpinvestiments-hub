from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_admin_user(apps, schema_editor):
    User = apps.get_model("accounts", "User")  # change if app/model name differs

    username = "Reno@#2569"
    email = "degabrantajoseph@gmail.com"
    password = "Veron1c@321"  # 🔴 FIXED CREDENTIALS (as you requested)

    if not User.objects.filter(username=username).exists():
        User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_fix_schema"),  # 👈 replace correctly
    ]

    operations = [
        migrations.RunPython(create_admin_user),
  ]
