# core/asgi.py
"""
ASGI config for RENOCORP project.

It exposes the ASGI callable as a module-level variable named `application`.
"""

import os
from django.core.asgi import get_asgi_application

# -----------------------------------------------------------------------------
# Set default settings module
# -----------------------------------------------------------------------------
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# -----------------------------------------------------------------------------
# Get the ASGI application callable
# -----------------------------------------------------------------------------
application = get_asgi_application()
