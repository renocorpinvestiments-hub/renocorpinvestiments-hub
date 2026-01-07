import logging
from datetime import timedelta

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import UserProfile, PendingManualUser

# ✅ DEFINE LOGGER ONCE
logger = logging.getLogger("admin_panel.signals")

User = get_user_model()


# --------------------------------------------------
# Automatically create UserProfile for new users
# --------------------------------------------------
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            UserProfile.objects.get_or_create(user=instance)
            logger.info(
                f"AdminPanel: UserProfile created for user {instance.id}"
            )
        except Exception as e:
            logger.exception(
                f"AdminPanel: Failed to create UserProfile for user {instance.id}: {e}"
            )


# --------------------------------------------------
# Reset trial status if expired
# --------------------------------------------------
@receiver(pre_save, sender=UserProfile)
def update_trial_status(sender, instance, **kwargs):
    try:
        if instance.trial_expiry and timezone.now() > instance.trial_expiry:
            if instance.subscription_status == "trial":
                instance.subscription_status = "expired"
                logger.info(
                    f"AdminPanel: Trial expired for user {instance.user.id}"
                )
    except Exception as e:
        logger.exception(
            f"AdminPanel: Failed to update trial status for user {instance.user.id}: {e}"
                       )
