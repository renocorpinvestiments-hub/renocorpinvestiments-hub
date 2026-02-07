# manage.py
#!/usr/bin/env python
"""Django’s command-line utility for administrative tasks."""
import os
import sys
from dotenv import load_dotenv  # ✅ Added: loads environment variables
from django.core.management import execute_from_command_line  # ✅ Added: handles Django commands


def main():
    """Run administrative tasks."""
    # ✅ Load environment variables from .env
    load_dotenv()

    # ✅ Set default settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

    try:
        execute_from_command_line(sys.argv)
    except Exception as exc:
        print(f"❌ Error starting Django: {exc}")
        sys.exit(1)


if __name__ == '__main__':
    main()
