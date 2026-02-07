# apps/admin_panel/utils.py
import logging
import random
import string
import uuid
from django.conf import settings
from .models import PendingManualUser
import logging

logger = logging.getLogger(__name__)

# =====================================================
# PENDING MANUAL USERS CLEANUP
# =====================================================

def clear_pending_manual_users():
    """
    Delete all pending manual users from the database.
    Can be called when the manual login page is loaded or session expired.
    """
    try:
        count, _ = PendingManualUser.objects.all().delete()
        logger.info(f"Cleared {count} pending manual users.")
    except Exception as e:
        logger.error(f"Failed to clear pending manual users: {str(e)}")

# =====================================================
# OTP / CODE GENERATORS
# =====================================================

def generate_invitation_code() -> str:
    """Generate unique invitation code"""
    return uuid.uuid4().hex[:10].upper()


def generate_temporary_password(length: int = 10) -> str:
    """Generate secure temporary password"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.SystemRandom().choices(chars, k=length))


