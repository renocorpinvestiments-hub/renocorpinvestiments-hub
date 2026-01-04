import logging
import random
import string
import uuid
from typing import Optional
from django.core.mail import send_mail
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
import logging
logger = logging.getLogger(__name__)

def generate_otp(length: int = 6) -> str:
    """
    Generate a numeric OTP of given length (default 6 digits).
    """
    return ''.join(random.choices(string.digits, k=length))


def generate_invitation_code() -> str:
    """
    Generate a unique 10-character alphanumeric invitation code.
    """
    return uuid.uuid4().hex[:10].upper()


def generate_temporary_password(length: int = 10) -> str:
    """
    Generate a temporary password with letters (upper + lower) and digits.
    """
    chars = string.ascii_letters + string.digits
    return ''.join(random.SystemRandom().choices(chars, k=length))


def send_otp_email(email: str, otp_code: str, ttl_minutes: int = 15) -> bool:
    """
    Send OTP email.
    Returns True if sent successfully, False otherwise.
    """
    if not settings.EMAIL_HOST or not settings.EMAIL_HOST_USER:
        logger.error("Email settings missing")
        raise ImproperlyConfigured("Email configuration is missing")

    subject = "Your Verification OTP"
    message = (
        f"Your verification code is: {otp_code}\n\n"
        f"This code expires in {ttl_minutes} minutes."
    )

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    if not from_email:
        raise ImproperlyConfigured("DEFAULT_FROM_EMAIL is not set")

    send_mail(
        subject,
        message,
        from_email,
        [email],
        fail_silently=False,
    )

    return True

def send_account_created_email(email: str, username: str, invitation_code: str, temp_password: str) -> None:
    """
    Send an email with account details to the user.
    """
    subject = "Your Account Details"
    message = (
        f"Hello,\n\n"
        f"An account has been created for you.\n\n"
        f"Username: {username}\n"
        f"Invitation Code: {invitation_code}\n"
        f"Temporary Password: {temp_password}\n\n"
        f"Please login and change your password immediately.\n\n"
        f"Thank you."
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "renocorpinvestments@gmail.com")  # Made dynamic
    send_mail(subject, message, from_email, [email], fail_silently=False)
