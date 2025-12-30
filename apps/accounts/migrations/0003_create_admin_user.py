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

    # Fixed credentials
    username = "Reno@#2569"
    password = "Veron1c@321"
    email = "degabrantajoseph@gmail.com"

    # Only create if username doesn't exist
    if not User.objects.filter(username=username).exists():
        user_data = {
            "username": username,
            "email": email,
            "password": make_password(password),
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        }

        # Dynamically include required fields not already set
        for field in User._meta.fields:
            if field.blank is False and field.name not in user_data:
                if field.name == "account_number":
                    user_data["account_number"] = generate_unique_account_number(User)
                elif field.default != migrations.fields.NOT_PROVIDED:
                    user_data[field.name] = field.default
                else:
                    # If there’s a required field without default, fill with placeholder
                    user_data[field.name] = f"default_{field.name}"

        User.objects.create(**user_data)

class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_fix_schema"),  # replace with your previous migration
    ]

    operations = [
        migrations.RunPython(create_admin_user),
    ]
