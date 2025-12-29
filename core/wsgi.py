import os
import django
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# Initialize Django first
django.setup()

from django.contrib.auth import get_user_model

def ensure_admin():
    User = get_user_model()
    username = "admin"
    email = "admin@example.com"
    password = "Admin123!"

    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email, password=password)
        print("✅ Admin account created")
    else:
        print("ℹ️ Admin account already exists")

ensure_admin()

application = get_wsgi_application()
