# ai_app/invitation_manager.py

import logging
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from .models import Invite
from .reward_manager import reward_inviter
from .notifications import create_notification

User = get_user_model()
logger = logging.getLogger(__name__)


class InvitationManager:
    """
    Handles user invitation tracking, linking, and reward assignment.
    """

    @staticmethod
    def link_invitation(invitee: User, invite_code: str) -> bool:
        """
        Links a user to their inviter using the invite code.
        Returns True if successfully linked, False otherwise.
        """
        try:
            inviter = User.objects.filter(referral_code=invite_code).first()
            if not inviter:
                logger.warning(f"Invalid invite code used: {invite_code}")
                return False

            if inviter == invitee:  # prevent self-invites
                logger.warning(f"User {invitee.username} attempted self-invite.")
                return False

            with transaction.atomic():
                # Create or ensure invite relationship exists
                Invite.objects.get_or_create(inviter=inviter, invitee=invitee)

                # Save inviter on user
                invitee.invited_by = inviter
                invitee.save(update_fields=["invited_by"])

                # Notify inviter
                create_notification(
                    user=inviter,
                    title="🎉 New Invite Joined!",
                    message=f"{invitee.username} joined using your invite link.",
                    category="invite"
                )

            logger.info(f"Invite linked: {invitee.username} invited by {inviter.username}")
            return True

        except Exception as e:
            logger.error(f"Failed to link invitation: {e}")
            return False

    @staticmethod
    def reward_for_activation(user: User):
        """
        Reward inviter when the invited user activates subscription.
        """
        try:
            if not user.invited_by:
                return

            inviter = user.invited_by

            reward_inviter(inviter, user, event="activation")

            create_notification(
                user=inviter,
                title="💰 Referral Bonus Earned!",
                message=f"You earned a referral reward for {user.username}'s activation.",
                category="reward"
            )

            logger.info(
                f"Referral reward for activation: inviter={inviter.username}, invitee={user.username}"
            )

        except Exception as e:
            logger.error(f"Error rewarding inviter for activation: {e}")

    @staticmethod
    def repair_missing_invites():
        """
        Rebuilds missing Invite records for existing users.
        """
        try:
            missing = User.objects.filter(invited_by__isnull=False).exclude(
                id__in=Invite.objects.values_list("invitee_id", flat=True)
            )

            repaired = 0
            for user in missing:
                Invite.objects.get_or_create(
                    inviter=user.invited_by,
                    invitee=user,
                    defaults={"date_invited": timezone.now()}
                )
                repaired += 1

            if repaired > 0:
                logger.info(f"Repaired {repaired} missing invite records.")

            return repaired

        except Exception as e:
            logger.error(f"Error repairing missing invites: {e}")
            return 0