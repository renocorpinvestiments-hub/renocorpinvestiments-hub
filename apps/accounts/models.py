# apps/accounts/models.py
from django.contrib.auth.models import Group, Permission
from django.db import models
from django.contrib.auth.models import AbstractUser
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
    return f"REN-{uuid.uuid4().hex[:8].upper()}"

# -------------------------------------------
#  USER MODEL
# -------------------------------------------
class User(AbstractUser):
    email = models.EmailField(unique=True)

    account_number = models.CharField(
        max_length=15,
        unique=True,
        null=True,
        blank=True,
        help_text="User phone number for withdrawals"
    )

    temp_flag = models.BooleanField(default=False)

    # Fix for group/permission conflicts
    groups = models.ManyToManyField(Group, related_name="accounts_users", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="accounts_users_permissions", blank=True)

    # Optional fields
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)

    # Invitation code
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

    # 🚀 FAST referral counter
    invites = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["username"]),
            models.Index(fields=["account_number"]),
            models.Index(fields=["email"]),
            models.Index(fields=["invitation_code"]),
            models.Index(fields=["invites"]),
        ]

    def __str__(self):
        return self.username

    def is_admin_username(self):
        return self.username.startswith("#renon@$")

    def assign_invitation_code(self):
        if not self.invitation_code:
            code = generate_invitation_code()
            while User.objects.filter(invitation_code=code).exists():
                code = generate_invitation_code()
            self.invitation_code = code
