from django.contrib.auth.models import Group, Permission
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid


# -------------------------------------------
#  CHOICES
# -------------------------------------------
SUBSCRIPTION_CHOICES = (
    ("inactive", "Inactive"),
    ("active", "Active"),
)

GENDER_CHOICES = (
    ("male", "Male"),
    ("female", "Female"),
    ("other", "Other"),
)


# -------------------------------------------
#  HELPERS
# -------------------------------------------
def generate_invitation_code():
    """Generate a unique invitation code like REN-3X8FD9"""
    return f"REN-{uuid.uuid4().hex[:8].upper()}"


# -------------------------------------------
#  USER MODEL
# -------------------------------------------
class User(AbstractUser):
    email = models.EmailField(unique=True)
    account_number = models.CharField(
    max_length=15,
    unique=True,
    null=False,
    blank=False,
    help_text="User phone number for withdrawals"
    )
    temp_flag = models.BooleanField(default=False)

    # Fix for group/permission conflicts
    groups = models.ManyToManyField(
        Group,
        related_name="accounts_users",
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="accounts_users_permissions",
        blank=True,
    )

    # Optional fields
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)

    # Invitation code (assigned after verification)
    invitation_code = models.CharField(max_length=32, unique=True, blank=True, null=True)

    # Subscription + balance
    subscription_status = models.CharField(max_length=10, choices=SUBSCRIPTION_CHOICES, default="inactive")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Who invited this user
    invited_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invited_users"
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["username"]),
            models.Index(fields=["account_number"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return self.username

    def is_admin_username(self):
        """Admin username pattern must start with '#renon@$'"""
        return self.username.startswith("#renon@$")

    def assign_invitation_code(self):
        """Assign a unique invitation code if not already set."""
        if not self.invitation_code:
            code = generate_invitation_code()
            while User.objects.filter(invitation_code=code).exists():
                code = generate_invitation_code()
            self.invitation_code = code
            self.save(update_fields=["invitation_code"])
        return self.invitation_code


