# apps/admin_panel/models.py
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.dispatch import receiver
from django.db.models.signals import post_save
from datetime import timedelta
import uuid


# ============================================================
# UTILITIES
# ============================================================

def gen_uuid8():
    return uuid.uuid4().hex[:8].upper()


# ============================================================
# ADMIN GLOBAL SETTINGS (SINGLETON)
# ============================================================
class AdminSettings(models.Model):
    THEME_CHOICES = (
        ("light", "Light"),
        ("dark", "Dark"),
        ("system", "System"),
    )

    theme_mode = models.CharField(max_length=20, choices=THEME_CHOICES, default="system")
    site_email = models.EmailField(blank=True, null=True)
    support_contact = models.CharField(max_length=64, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Admin Settings"
        verbose_name_plural = "Admin Settings"

    def save(self, *args, **kwargs):
        if not self.pk and AdminSettings.objects.exists():
            raise ValidationError("Only one AdminSettings instance is allowed")
        super().save(*args, **kwargs)

    def __str__(self):
        return "Admin Global Settings"


# ============================================================
# TASK CATEGORIES (ADMIN CONTROLS REWARDS)
# ============================================================
class TaskCategory(models.Model):
    """
    Admin-controlled task categories.
    ONLY these four categories are allowed.
    Reward amount here is the single source of truth.
    """

    VIDEO_ADS = "video_ads"
    SURVEY = "survey"
    APP_INSTALL = "app_install"
    OTHER = "other"

    CATEGORY_CHOICES = (
        (VIDEO_ADS, "Video Ads"),
        (SURVEY, "Survey"),
        (APP_INSTALL, "App Install"),
        (OTHER, "Other"),
    )

    code = models.CharField(
        max_length=32,
        choices=CATEGORY_CHOICES,
        unique=True
    )

    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)

    reward_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Amount credited per successful task"
    )

    max_daily_completions = models.PositiveIntegerField(
        default=0,
        help_text="0 = unlimited"
    )

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Task Category"
        verbose_name_plural = "Task Categories"

    def __str__(self):
        return f"{self.get_code_display()} ({self.reward_amount})"


# ============================================================
# USER PROFILE & BALANCE (LEDGER SAFE)
# ============================================================
class UserProfile(models.Model):
    SUB_STATUS = (
        ("trial", "Trial"),
        ("active", "Active"),
        ("expired", "Expired"),
    )

    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="profile")
    invitation_code = models.CharField(max_length=64, unique=True, blank=True, null=True)
    invited_by = models.CharField(max_length=150, blank=True, null=True)

    subscription_status = models.CharField(max_length=20, choices=SUB_STATUS, default="trial")
    trial_expiry = models.DateTimeField(blank=True, null=True)

    balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )

    account_number = models.CharField(max_length=64, blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)

    def is_trial_active(self):
        return self.trial_expiry and timezone.now() <= self.trial_expiry

    def __str__(self):
        return f"Profile({self.user})"


@receiver(post_save)
def create_profile(sender, instance, created, **kwargs):
    User = get_user_model()
    if sender == User and created:
        UserProfile.objects.create(user=instance)

# ============================================================
# REWARD LEDGER (SOURCE OF TRUTH)
# ============================================================
class RewardLog(models.Model):
    """
    Immutable ledger of all task rewards.
    Never delete rows from this table.
    """

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="reward_logs")
    category = models.ForeignKey(TaskCategory, on_delete=models.PROTECT)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    source_ref = models.CharField(max_length=128, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "category"]),
        ]

    def __str__(self):
        return f"{self.user} +{self.amount} ({self.category.code})"


# ============================================================
# TRANSACTION LOG (AUDIT)
# ============================================================
class TransactionLog(models.Model):
    TYPES = (
        ("reward", "Reward"),
        ("withdrawal", "Withdrawal"),
        ("subscription", "Subscription"),
        ("system", "System"),
    )

    STATUS = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    )

    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    actor = models.CharField(max_length=32, default="system")

    amount = models.DecimalField(max_digits=14, decimal_places=2)
    txn_type = models.CharField(max_length=20, choices=TYPES)
    status = models.CharField(max_length=16, choices=STATUS, default="pending")

    details = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def mark_success(self, details=""):
        self.status = "success"
        self.processed_at = timezone.now()
        if details:
            self.details += f"\n{details}"
        self.save(update_fields=["status", "processed_at", "details"])


# ============================================================
# ADMIN LOGIN AUDIT
# ============================================================
class AdminLoginAudit(models.Model):
    admin_user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    username_entered = models.CharField(max_length=150, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=512, blank=True)
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"AdminLogin(success={self.success})"


# ============================================================
# MANUAL USER ONBOARDING
# ============================================================
class PendingManualUser(models.Model):
    GENDER = (
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    )

    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=20, choices=GENDER)
    email = models.EmailField(unique=True)
    account_number = models.CharField(max_length=64)

    invitation_code = models.CharField(max_length=64, blank=True, null=True)
    temporary_password = models.CharField(max_length=128, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f"PendingUser({self.email})"


class ManualUserOTP(models.Model):
    pending_user = models.ForeignKey(PendingManualUser, on_delete=models.CASCADE, related_name="otps")
    otp_code = models.CharField(max_length=8)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return timezone.now() <= self.expires_at

    @classmethod
    def create_otp(cls, pending_user, code, ttl_minutes=15):
        return cls.objects.create(
            pending_user=pending_user,
            otp_code=code,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
    )

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    message = models.TextField()
    category = models.CharField(max_length=64, default="general")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification({self.user}, {self.title})"


class AdminNotification(models.Model):
    title = models.CharField(max_length=255)
    message = models.TextField()
    category = models.CharField(max_length=64, default="system")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AdminNotification({self.title})"

# ============================================================
# GIFT OFFER MODEL
# ============================================================
class GiftOffer(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    reward_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    required_invites = models.PositiveIntegerField(
        default=0,
        help_text="Number of invites required to unlock this gift offer"
    )
    time_limit_hours = models.PositiveIntegerField(
        default=0,
        help_text="Time limit in hours to complete the offer (0 = no limit)"
    )
    extra_video_count = models.PositiveIntegerField(
        default=0,
        help_text="Extra videos the user can watch to earn additional rewards"
    )
    earning_per_extra_video = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Reward for each extra video"
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Gift Offer"
        verbose_name_plural = "Gift Offers"
        ordering = ["-created_at"]

    def __str__(self):
        return f"GiftOffer({self.title}, Reward: {self.reward_amount})"

# ============================================================
# TASK CONTROL MODEL
# ============================================================
class TaskControl(models.Model):
    """
    Admin-controlled global limits and earnings for tasks.
    """

    videos_count = models.PositiveIntegerField(default=0, help_text="Number of videos allowed per day")
    video_earning = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    surveys_count = models.PositiveIntegerField(default=0, help_text="Number of surveys allowed per day")
    survey_earning = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    app_tests_count = models.PositiveIntegerField(default=0, help_text="Number of app tests allowed per day")
    app_test_earning = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    invite_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)],
                                      help_text="Cost per invite for the user")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Task Control"
        verbose_name_plural = "Task Controls"

    def __str__(self):
        return f"TaskControl(Videos: {self.videos_count}, Surveys: {self.surveys_count}, App Tests: {self.app_tests_count})"

# ============================================================
# PAYROLL ENTRY MODEL
# ============================================================
class PayrollEntry(models.Model):
    name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    auto_withdraw = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payroll Entry"
        verbose_name_plural = "Payroll Entries"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.account_number}) - {self.amount}"
