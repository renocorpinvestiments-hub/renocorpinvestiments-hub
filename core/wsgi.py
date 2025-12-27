import os
import time
import django
from django.core.management import call_command
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

django.setup()

# ---------- SAFE DB BOOTSTRAP ----------
def wait_for_db(max_retries=10, delay=3):
    for i in range(max_retries):
        try:
            connection.ensure_connection()
            return True
        except Exception:
            time.sleep(delay)
    return False

def database_has_tables():
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                );
            """)
        else:
            cursor.execute("SELECT count(*) FROM sqlite_master;")
        return cursor.fetchone()[0]

if wait_for_db():
    if not database_has_tables():
        call_command("migrate", interactive=False)
# --------------------------------------

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
