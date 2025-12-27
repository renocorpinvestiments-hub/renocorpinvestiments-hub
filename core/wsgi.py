import os
import time
import django
from django.core.management import call_command
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

# -------------------------
# Helper functions
# -------------------------
def wait_for_db(max_retries=12, delay=3):
    """Wait until the database is ready."""
    for _ in range(max_retries):
        try:
            connection.ensure_connection()
            return True
        except Exception:
            time.sleep(delay)
    return False

def database_has_tables():
    """Check if database has any tables."""
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                );
            """)
        else:  # sqlite fallback
            cursor.execute("SELECT count(*) FROM sqlite_master;")
        return cursor.fetchone()[0]

def create_special_admin():
    """Ensure the special admin user exists."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    username = "Reno@#2569"
    password = "Veron1c@321"
    email = "degabrantajoseph@gmail.com"
    
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f"Special admin '{username}' created.")
    else:
        print(f"Special admin '{username}' already exists.")

# -------------------------
# Migration & seeding
# -------------------------
if wait_for_db():
    if not database_has_tables():
        # 1️⃣ Accounts migrations first (custom user tables)
        call_command("migrate", "accounts", interactive=False)
        
        # 2️⃣ Core Django and other apps
        call_command("migrate", "admin", interactive=False)
        call_command("migrate", "auth", interactive=False)
        call_command("migrate", "contenttypes", interactive=False)
        call_command("migrate", "sessions", interactive=False)
        call_command("migrate", interactive=False)  # catch any remaining apps

        # 3️⃣ Seed special admin user
        create_special_admin()

# -------------------------
# Start WSGI application
# -------------------------
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
