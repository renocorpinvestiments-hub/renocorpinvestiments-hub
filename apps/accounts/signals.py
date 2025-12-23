from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import User, EmailOTP
from .forms import generate_otp
from django.core.mail import send_mail
from django.conf import settings

# -----------------------------
# AUTO-GENERATE INVITATION CODE AFTER USER CREATION (if verified)
# -----------------------------
@receiver(post_save, sender=User)
def assign_invitation_code_signal(sender, instance, created, **kwargs):
    """
    Automatically assign an invitation code to new users
    who are active but don't have one yet.
    """
    if created and instance.is_active and not instance.invitation_code:
        instance.assign_invitation_code()


# -----------------------------
# SEND OTP EMAIL AUTOMATICALLY WHEN NEW USER IS CREATED (if inactive)
# -----------------------------
@receiver(post_save, sender=User)
def send_otp_signal(sender, instance, created, **kwargs):
    """
    Automatically send OTP to new users who are inactive.
    """
    if created and not instance.is_active:
        otp_code = generate_otp()
        EmailOTP.objects.create(email=instance.email, otp=otp_code, created_at=timezone.now())

        # Send email (fail silently)
        send_mail(
            subject="RENOCORP Account Verification Code",
            message=f"Your RENOCORP verification code is {otp_code}. It expires in 10 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.email],
            fail_silently=True,
        )