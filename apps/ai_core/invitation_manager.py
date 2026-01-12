import logging
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.db.models import F
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
        inviter = User.objects.only("id").filter(invitation_code=invite_code).first()
        if not inviter or inviter == invitee:
            return False

        with transaction.atomic():
            Invite.objects.get_or_create(inviter=inviter, invitee=invitee)

            User.objects.filter(pk=invitee.pk).update(invited_by=inviter)

        notify_user(
            user=inviter,
            title="🎉 New Invite Joined!",
            message=f"{invitee.username} joined using your invite link.",
            category="invite"
        )

        notify_admin(
            title="Invitation Linked",
            message=f"{invitee.username} linked to inviter {inviter.username}"
        )

        return True

    except Exception as e:
        logger.error(f"Failed to link invitation: {e}")
        return False
# ------------------------------------------------
# Reward inviter on activation
# ------------------------------------------------

def reward_for_activation(user: User):
    try:
        inviter_id = User.objects.filter(pk=user.pk).values_list("invited_by_id", flat=True).first()
        if not inviter_id:
            return

        with transaction.atomic():
            inviter = User.objects.select_for_update().get(pk=inviter_id)

            # Prevent double reward
            if RewardLog.objects.filter(
                user_id=inviter.id,
                category="invite_activation",
                provider="system",
                task__isnull=True,
                reference=user.id
            ).exists():
                return

            task_category = TaskCategory.objects.filter(code="other", active=True).only("reward_amount").first()
            if not task_category:
                return

            reward_ugx = int(task_category.reward_amount)

            # 💥 FAST COUNTER + BALANCE
            User.objects.filter(pk=inviter.id).update(
                balance=F("balance") + reward_ugx,
                invites=F("invites") + 1
            )

            RewardLog.objects.create(
                user_id=inviter.id,
                task=None,
                provider="system",
                category="invite_activation",
                reference=user.id,  # 🔐 prevents duplicates
                final_reward_ugx=reward_ugx,
                provider_reward_ugx=0,
                admin_reward_ugx=reward_ugx,
            )

        notify_user(
            user=inviter,
            title="💰 Referral Bonus Earned!",
            message=f"You earned {reward_ugx} UGX for {user.username}'s activation.",
            category="reward"
        )

        notify_admin(
            title="Reward Processed",
            message=f"{reward_ugx} UGX rewarded to {inviter.username} for {user.username}'s activation"
        )

    except Exception as e:
        logger.error(f"Error rewarding inviter: {e}")
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
