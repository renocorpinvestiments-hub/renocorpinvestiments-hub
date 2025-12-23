"""
WSGI config for Renocorp AI project.

This file exposes the WSGI callable as a module-level variable named `application`.
It serves as the entry point for WSGI-compatible web servers like Gunicorn or uWSGI.
"""

import os
from django.core.wsgi import get_wsgi_application

# -----------------------------------------------------------------------------
# Default Django settings module
# -----------------------------------------------------------------------------
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# -----------------------------------------------------------------------------
# Get the WSGI application callable
# -----------------------------------------------------------------------------
application = get_wsgi_application()