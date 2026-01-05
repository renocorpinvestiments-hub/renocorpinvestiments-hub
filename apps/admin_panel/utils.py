import logging
import random
import string
import uuid
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

# =====================================================
# OTP / CODE GENERATORS
# =====================================================

def generate_otp(length: int = 6) -> str:
    """Generate numeric OTP"""
    return ''.join(random.choices(string.digits, k=length))


def generate_invitation_code() -> str:
    """Generate unique invitation code"""
    return uuid.uuid4().hex[:10].upper()


def generate_temporary_password(length: int = 10) -> str:
    """Generate secure temporary password"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.SystemRandom().choices(chars, k=length))


# =====================================================
# EMAIL HELPERS (GMAIL SAFE)
# =====================================================

def send_otp_email(email: str, otp_code: str, ttl_minutes: int = 5) -> bool:
    """
    Send OTP email using Gmail SMTP.
    NEVER raises exceptions (prevents 500 errors).
    Returns True if sent, False if failed.
    """

    # 🔍 DEBUG (visible in Render logs)
    print("=== OTP EMAIL ATTEMPT ===")
    print("TO:", email)
    print("OTP:", otp_code)

    # Basic config validation (NO crashing)
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        logger.error("EMAIL CONFIG MISSING (USER OR PASSWORD)")
        return False

    if not settings.DEFAULT_FROM_EMAIL:
        logger.error("DEFAULT_FROM_EMAIL NOT SET")
        return False

    try:
        send_mail(
            subject="Your Verification OTP",
            message=(
                f"Your verification code is: {otp_code}\n\n"
                f"This code expires in {ttl_minutes} minutes."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,  # show real Gmail errors in logs
        )
        return True

    except Exception as e:
        logger.error(f"GMAIL SMTP ERROR (OTP): {e}")
        return False


def send_account_created_email(
    email: str,
    username: str,
    invitation_code: str,
    temp_password: str,
) -> bool:
    """
    Send account credentials email.
    Safe for Gmail / Render.
    """

    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        logger.error("EMAIL CONFIG MISSING (ACCOUNT EMAIL)")
        return False

    try:
        send_mail(
            subject="Your Account Details",
            message=(
                f"Hello,\n\n"
                f"An account has been created for you.\n\n"
                f"Username: {username}\n"
                f"Invitation Code: {invitation_code}\n"
                f"Temporary Password: {temp_password}\n\n"
                f"Please login and change your password immediately.\n\n"
                f"Thank you."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True

    except Exception as e:
        logger.error(f"GMAIL SMTP ERROR (ACCOUNT EMAIL): {e}")
        return False
