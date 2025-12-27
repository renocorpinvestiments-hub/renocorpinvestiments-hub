import os
import time
import django
from django.core.management import call_command
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

django.setup()

# ---------- ONE-TIME DB REPAIR ----------
def wait_for_db(max_retries=12, delay=3):
    for _ in range(max_retries):
        try:
            connection.ensure_connection()
            return True
        except Exception:
            time.sleep(delay)
    return False

if wait_for_db():
    # FORCE all migrations to run now
    call_command("migrate", interactive=False)
# ----------------------------------------

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
