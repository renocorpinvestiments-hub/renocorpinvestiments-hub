import os
import django
from django.core.management import call_command
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

django.setup()

# ---------- SAFETY MIGRATION BLOCK ----------
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

if not database_has_tables():
    call_command("migrate", interactive=False)
# --------------------------------------------

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
