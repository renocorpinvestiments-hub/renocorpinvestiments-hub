from django.db import migrations
from django.contrib.auth.hashers import make_password
import random

def generate_unique_account_number(User):
    """Generate a random 10-digit account number that is unique."""
    while True:
        account_number = str(random.randint(1000000000, 9999999999))
        if not User.objects.filter(account_number=account_number).exists():
            return account_number

def create_admin_user(apps, schema_editor):
    User = apps.get_model("accounts", "User")

    username = "Reno@#2569"
    password = "Veron1c@321"
    email = "degabrantajoseph@gmail.com"

    # Only create if username doesn't exist
    if not User.objects.filter(username=username).exists():
        # Generate account number only for admin
        account_number = generate_unique_account_number(User)

        User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            is_staff=True,
            is_superuser=True,
            is_active=True,
            account_number=account_number
        )

class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_fix_schema"),  # replace with your previous migration
    ]

    operations = [
        migrations.RunPython(create_admin_user),
    ]
