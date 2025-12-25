from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid

# ------------------------------
# Helper functions
# ------------------------------
def generate_unique_invite_code():
    """Generate a unique invite code for UserProfile."""
    for _ in range(5):
        code = uuid.uuid4().hex[:10].upper()
        if not UserProfile.objects.filter(invitation_code=code).exists():
            return code
    raise Exception("Unable to generate unique invite code")


# ---------- USER PROFILE ----------
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, unique=True)
    profile_picture = models.ImageField(
        upload_to='profile_pics/', default='profile_pics/default.png'
    )
    invitation_code = models.CharField(
        max_length=10, unique=True, default=generate_unique_invite_code, db_index=True
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    today_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    invites = models.PositiveIntegerField(default=0)
    subscription_expiry = models.DateField(null=True, blank=True)
    is_subscribed = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    def has_active_subscription(self):
        """Return True if subscription is valid and not expired."""
        if not self.subscription_expiry:
            return False
        return self.subscription_expiry >= timezone.localdate()

    def __str__(self):
        try:
            return self.user.username
        except Exception:
            return str(self.user)

    class Meta:
        ordering = ['-joined_at']


# ---------- TASK MODELS ----------
class BaseTask(models.Model):
    """Abstract base for all task types."""
    task_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    reward = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    provider = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class VideoTask(BaseTask):
    thumbnail = models.URLField()
    video_url = models.URLField()


class SurveyTask(BaseTask):
    iframe_url = models.URLField(blank=True, null=True)
    provider_url = models.URLField(blank=True, null=True)
    time_limit = models.IntegerField(default=5)


class AppTest(BaseTask):
    download_url = models.URLField()


class GiftOffer(BaseTask):
    required_invites = models.IntegerField(default=0)
    duration_days = models.IntegerField(default=1)


# ---------- COMPLETED TASKS ----------
class CompletedTask(models.Model):
    """Tracks task completions by user (API or iframe tasks)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)  # 'VideoTask', 'SurveyTask', etc.
    task_id = models.UUIDField()  # links to BaseTask task_id
    provider = models.CharField(max_length=50)
    reward = models.DecimalField(max_digits=12, decimal_places=2)
    estimated = models.BooleanField(default=False)  # True if category/reward was estimated
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'task_id', 'provider')
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.user} completed {self.task_type} ({self.task_id})"


# ---------- TRANSACTION ----------
class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdraw', 'Withdraw'),
        ('reward', 'Reward'),
        ('subscription', 'Subscription'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('initiated', 'Initiated'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('queued_for_manual', 'Queued for Manual Review'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dashboard_transactions"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=255, unique=True, default=lambda: uuid.uuid4().hex)
    provider_reference = models.CharField(max_length=255, blank=True, null=True)
    flutterwave_id = models.CharField(max_length=255, blank=True, null=True)
    raw_provider_response = models.JSONField(blank=True, null=True)
    failure_reason = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{getattr(self.user, 'username', str(self.user))} - {self.transaction_type} UGX {self.amount}"

    class Meta:
        ordering = ['-created_at']


# ---------- NOTIFICATIONS ----------
class Notification(models.Model):
    NOTIF_TYPES = (
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    type = models.CharField(max_length=10, choices=NOTIF_TYPES, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    related_task = models.ForeignKey(CompletedTask, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Notification for {getattr(self.user, 'username', str(self.user))}"

    class Meta:
        ordering = ['-created_at']


# ---------- TASK PROGRESS ----------
class TaskProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_tasks = models.IntegerField(default=14)
    completed_tasks = models.IntegerField(default=0)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    last_reset = models.DateField(default=lambda: timezone.localdate())

    def update_progress(self):
        if self.total_tasks > 0:
            self.progress = (self.completed_tasks / self.total_tasks) * 100
            self.save(update_fields=['progress'])

    def __str__(self):
        return f"{getattr(self.user, 'username', str(self.user))} Progress {self.progress}%"

    class Meta:
        ordering = ['-last_reset']


# ---------- LEDGER ----------
class LedgerEntry(models.Model):
    ENTRY_TYPES = (
        ('credit', 'Credit'),
        ('debit', 'Debit')
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES)
    reason = models.CharField(max_length=255, blank=True, null=True)
    reference = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.entry_type.upper()} UGX {self.amount} for {getattr(self.user, 'username', str(self.user))}"

    class Meta:
        ordering = ['-created_at']
