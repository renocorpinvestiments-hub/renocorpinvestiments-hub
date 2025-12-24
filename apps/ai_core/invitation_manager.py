import logging
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import Invite, RewardLog
from apps.admin_panel.models import TaskCategory, UserProfile
from .notifications import notify_user, notify_admin  # updated import

User = get_user_model()
logger = logging.getLogger(__name__)


# ------------------------------------------------
# Invitation linking
# ------------------------------------------------
def link_invitation(invitee: User, invite_code: str) -> bool:
    try:
        inviter_profile = UserProfile.objects.filter(invitation_code=invite_code).first()
        if not inviter_profile:
            logger.warning(f"Invalid invite code used: {invite_code}")
            return False

        inviter = inviter_profile.user

        if inviter == invitee:
            logger.warning(f"User {invitee.username} attempted self-invite.")
            return False

        with transaction.atomic():
            Invite.objects.get_or_create(inviter=inviter, invitee=invitee)

            invitee_profile = UserProfile.objects.select_for_update().get(user=invitee)
            invitee_profile.invited_by = inviter.username
            invitee_profile.save(update_fields=["invited_by"])

            # Notify user
            notify_user(
                user=inviter,
                title="🎉 New Invite Joined!",
                message=f"{invitee.username} joined using your invite link.",
                category="invite"
            )

            # Notify admin
            notify_admin(
                title="Invitation Linked",
                message=f"{invitee.username} linked to inviter {inviter.username}"
            )

        logger.info(f"Invite linked: {invitee.username} invited by {inviter.username}")
        return True

    except Exception as e:
        logger.error(f"Failed to link invitation: {e}")
        return False


# ------------------------------------------------
# Reward inviter on activation
# ------------------------------------------------
def reward_for_activation(user: User):
    try:
        with transaction.atomic():
            user_profile = UserProfile.objects.select_for_update().get(user=user)
            inviter_username = user_profile.invited_by
            if not inviter_username:
                return

            inviter_profile = UserProfile.objects.select_for_update().filter(
                user__username=inviter_username
            ).first()
            if not inviter_profile:
                return

            inviter = inviter_profile.user

            if inviter == user:
                logger.warning(f"User {user.username} attempted self-reward.")
                return

            # Prevent duplicate reward
            if RewardLog.objects.filter(
                user=inviter,
                category="invite_activation",
                task__isnull=True,
                provider="system",
                admin_reward_ugx__gt=0,
            ).exists():
                logger.warning(f"Reward already issued for {user.username}")
                return

            # Pull reward from admin configuration
            task_category = TaskCategory.objects.filter(code="other", active=True).first()
            if not task_category:
                logger.warning("No active TaskCategory for invite rewards.")
                return

            reward_ugx = int(task_category.reward_amount)

            # Credit inviter balance
            inviter_profile.balance += reward_ugx
            inviter_profile.save(update_fields=["balance"])

            # Immutable ledger entry
            RewardLog.objects.create(
                user=inviter,
                task=None,
                provider="system",
                category="invite_activation",
                final_reward_ugx=reward_ugx,
                provider_reward_ugx=0,
                admin_reward_ugx=reward_ugx,
            )

        # Notify user
        notify_user(
            user=inviter,
            title="💰 Referral Bonus Earned!",
            message=f"You earned {reward_ugx} UGX for {user.username}'s activation.",
            category="reward"
        )

        # Notify admin
        notify_admin(
            title="Reward Processed",
            message=f"{reward_ugx} UGX rewarded to {inviter.username} for {user.username}'s activation"
        )

        logger.info(f"Rewarded {reward_ugx} UGX to {inviter.username} for inviting {user.username}")

    except Exception as e:
        logger.error(f"Error rewarding inviter for activation: {e}")


# ------------------------------------------------
# Repair missing invites
# ------------------------------------------------
def repair_missing_invites() -> int:
    try:
        missing = UserProfile.objects.filter(invited_by__isnull=False).exclude(
            user__id__in=Invite.objects.values_list("invitee_id", flat=True)
        )

        repaired = 0
        for profile in missing:
            inviter = User.objects.filter(username=profile.invited_by).first()
            if not inviter:
                continue

            Invite.objects.get_or_create(
                inviter=inviter,
                invitee=profile.user,
                defaults={"date_invited": timezone.now()}
            )
            repaired += 1

        if repaired:
            logger.info(f"Repaired {repaired} missing invite records.")
            notify_admin(
                title="Missing Invites Repaired",
                message=f"Repaired {repaired} missing invite records."
            )

        return repaired

    except Exception as e:
        logger.error(f"Error repairing missing invites: {e}")
        return 0
