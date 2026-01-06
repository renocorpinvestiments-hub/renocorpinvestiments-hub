import logging
import random
import string
import uuid
from django.conf import settings

logger = logging.getLogger(__name__)

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


