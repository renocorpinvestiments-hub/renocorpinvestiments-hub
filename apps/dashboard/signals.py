#apps/dashboard/signals.py
import logging
from datetime import timedelta
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import UserProfile, CompletedTask, Transaction, LedgerEntry, TaskProgress

logger = logging.getLogger("dashboard.signals")
User = get_user_model()


# -------------------------------
# Automatically create UserProfile when a new User is created
# -------------------------------
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        try:
            UserProfile.objects.get_or_create(user=instance)
            logger.info(f"UserProfile created for user {instance.id}")
        except Exception as e:
            logger.exception(f"Failed to create UserProfile for user {instance.id}: {e}")


# -------------------------------
# Update user balance and ledger on task completion
# -------------------------------
@receiver(post_save, sender=CompletedTask)
def update_balance_on_task_completion(sender, instance, created, **kwargs):
    if not created:
        return

    try:
        profile = instance.user.userprofile
        profile.balance += instance.reward
        profile.today_earnings += instance.reward
        profile.save(update_fields=['balance', 'today_earnings'])

        LedgerEntry.objects.create(
            user=instance.user,
            amount=instance.reward,
            entry_type="credit",
            reason=f"Completed {instance.task_type}",
            reference=str(instance.task_id),
        )

        logger.info(f"Added {instance.reward} to user {instance.user.id} for task {instance.task_type}")
    except Exception as e:
        logger.exception(f"Failed to update balance for user {instance.user.id}: {e}")


# -------------------------------
# Automatically create ledger entries on transactions
# -------------------------------
@receiver(post_save, sender=Transaction)
def update_ledger_on_transaction(sender, instance, created, **kwargs):
    if not created:
        return

    try:
        entry_type = "credit" if instance.transaction_type in ["deposit", "reward", "subscription"] else "debit"
        LedgerEntry.objects.create(
            user=instance.user,
            amount=instance.amount,
            entry_type=entry_type,
            reason=instance.transaction_type,
            reference=instance.reference,
        )
        logger.info(f"Ledger entry created for user {instance.user.id} for transaction {instance.transaction_type}")
    except Exception as e:
        logger.exception(f"Failed to create ledger entry for transaction {instance.id}: {e}")


# -------------------------------
# Daily reset for today_earnings and task progress
# -------------------------------
@receiver(post_save, sender=UserProfile)
def reset_daily_progress(sender, instance, **kwargs):
    today = timezone.localdate()
    try:
        if instance.joined_at.date() < today:
            # Reset today_earnings if date has changed
            instance.today_earnings = 0
            instance.save(update_fields=['today_earnings'])

        # Reset TaskProgress
        progress, _ = TaskProgress.objects.get_or_create(user=instance.user)
        if progress.last_reset < today:
            progress.completed_tasks = 0
            progress.total_tasks = 0
            progress.progress = 0
            progress.last_reset = today
            progress.save()
            logger.info(f"Daily task progress reset for user {instance.user.id}")
    except Exception as e:
        logger.exception(f"Failed to reset daily progress for user {instance.user.id}: {e}")


# -------------------------------
# Update subscription status automatically
# -------------------------------
@receiver(pre_save, sender=UserProfile)
def update_subscription_status(sender, instance, **kwargs):
    try:
        if instance.subscription_expiry:
            instance.is_subscribed = instance.subscription_expiry >= timezone.localdate()
    except Exception as e:
        logger.exception(f"Failed to update subscription status for user {instance.user.id}: {e}")
