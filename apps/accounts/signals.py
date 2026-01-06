from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


# --------------------------------------------------
# AUTO-ASSIGN INVITATION CODE AFTER USER CREATION
# --------------------------------------------------
@receiver(post_save, sender=User)
def assign_invitation_code_signal(sender, instance, created, **kwargs):
    """
    Automatically assign an invitation code to a newly created user
    if they do not already have one.

    This runs once, immediately after user creation.
    """

    if created and not instance.invitation_code:
        instance.assign_invitation_code()
        instance.save(update_fields=["invitation_code"])
