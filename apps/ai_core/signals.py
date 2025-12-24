# ai_core/signals.py

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Task, RewardLog, Transaction, IdempotencyKey
from .invitation_manager import reward_for_activation

logger = logging.getLogger("ai_core.signals")
User = get_user_model()


# -------------------------------
# Reward Assignment on Task Completion
# -------------------------------
@receiver(post_save, sender=RewardLog)
def handle_reward_log(sender, instance: RewardLog, created, **kwargs):
    if not created:
        return

    # Optionally: auto-update user balance (if not handled elsewhere)
    try:
        user_profile = instance.user.profile
        user_profile.balance += instance.final_reward_ugx
        user_profile.save(update_fields=["balance"])
        logger.info(f"Reward applied for user {instance.user.id}: {instance.final_reward_ugx} UGX")
    except Exception as e:
        logger.exception(f"Failed to apply reward for user {instance.user.id}: {e}")


# -------------------------------
# Transaction completion hook
# -------------------------------
@receiver(post_save, sender=Transaction)
def handle_transaction_completion(sender, instance: Transaction, created, **kwargs):
    if created:
        return

    # If transaction is subscription success, reward inviter
    if instance.tx_type == "subscription" and instance.status == "success":
        try:
            if hasattr(instance.user, "invited_by") and instance.user.invited_by:
                reward_for_activation(instance.user)
        except Exception as e:
            logger.exception(f"Failed to reward inviter for user {instance.user.id}: {e}")


# -------------------------------
# Task Completion
# -------------------------------
@receiver(post_save, sender=Task)
def handle_task_completion(sender, instance: Task, **kwargs):
    if instance.is_completed:
        logger.info(f"Task marked completed: {instance.provider_name}:{instance.provider_task_id}")
