# models.py — AI Core (Production‑Grade, Scalable, Robust)
# ------------------------------------------------------------
# Responsibilities:
# - Normalized task storage
# - Strong webhook idempotency
# - Reward ledger & admin enforcement
# - Provider health & fetch logs
# - Safe integer-based monetary accounting
# ------------------------------------------------------------

from uuid import uuid4
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction, IntegrityError
from django.utils import timezone

# =============================================================
# ENUMS / CONSTANTS
# =============================================================

PROVIDER_CHOICES = [
    ("offertoro", "Offertoro"),
    ("adgem", "AdGem"),
    ("adgate", "AdGate"),
    ("wannads", "Wannads"),
    ("cpalead", "CPALead"),
    ("adscend", "AdScend"),
]

CONNECTION_STATUS_CHOICES = [
    ("connected", "connected"),
    ("failed", "failed"),
    ("rate_limited", "rate_limited"),
]

TRANSACTION_STATUS_CHOICES = [
    ("pending", "pending"),
    ("processing", "processing"),
    ("success", "success"),
    ("failed", "failed"),
]

TRANSACTION_TYPE_CHOICES = [
    ("withdrawal", "withdrawal"),
    ("subscription", "subscription"),
]

# =============================================================
# TASK MODEL (NORMALIZED OFFERS)
# =============================================================

class Task(models.Model):
    """Normalized task/offer stored in our system."""

    internal_task_id = models.UUIDField(default=uuid4, editable=False, unique=True)
    provider_name = models.CharField(max_length=50, choices=PROVIDER_CHOICES, db_index=True)
    provider_task_id = models.CharField(max_length=255, db_index=True)

    title = models.CharField(max_length=512)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=128, db_index=True)

    provider_reward_ugx = models.BigIntegerField(validators=[MinValueValidator(0)])
    admin_reward_ugx = models.BigIntegerField(validators=[MinValueValidator(0)])

    is_active = models.BooleanField(default=True, db_index=True)
    is_completed = models.BooleanField(default=False, db_index=True)

    raw_payload = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("provider_name", "provider_task_id")
        indexes = [
            models.Index(fields=["provider_name", "provider_task_id"]),
            models.Index(fields=["category", "is_active"]),
        ]

    def __str__(self):
        return f"{self.provider_name}:{self.provider_task_id}"

    def mark_completed(self):
        if not self.is_completed:
            self.is_completed = True
            self.save(update_fields=["is_completed"])

# =============================================================
# TASK FETCH / PROVIDER HEALTH LOGS
# =============================================================

class TaskFetchLog(models.Model):
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, db_index=True)
    status = models.CharField(max_length=64)
    message = models.TextField(blank=True)
    fetched_count = models.IntegerField(default=0)
    deleted_old_count = models.IntegerField(default=0)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-timestamp"]

class ProviderConnectionLog(models.Model):
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, db_index=True)
    status = models.CharField(max_length=32, choices=CONNECTION_STATUS_CHOICES)
    details = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-timestamp"]

# =============================================================
# IDEMPOTENCY (CRITICAL FOR WEBHOOK SAFETY)
# =============================================================

class IdempotencyKey(models.Model):
    """Guarantees webhook idempotency per provider transaction."""

    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, db_index=True)
    transaction_id = models.CharField(max_length=255, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ("provider", "transaction_id")
        indexes = [models.Index(fields=["provider", "transaction_id"])]

    @classmethod
    def acquire(cls, provider: str, transaction_id: str, user):
        """Returns (obj, created). Safe under concurrency."""
        try:
            with transaction.atomic():
                obj = cls.objects.create(
                    provider=provider,
                    transaction_id=transaction_id,
                    user=user,
                )
                return obj, True
        except IntegrityError:
            return cls.objects.get(provider=provider, transaction_id=transaction_id), False

# =============================================================
# WEBHOOK AUDIT LOG
# =============================================================

class WebhookLog(models.Model):
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, db_index=True)
    payload = models.JSONField()

    signature_valid = models.BooleanField(default=False)
    is_duplicate = models.BooleanField(default=False)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL)

    reward_ugx = models.BigIntegerField(null=True, blank=True)

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-timestamp"]

# =============================================================
# REWARD LEDGER (SOURCE OF TRUTH)
# =============================================================

class RewardLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)

    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES, db_index=True)
    category = models.CharField(max_length=128, db_index=True)

    # Integer‑only monetary storage (UGX)
    final_reward_ugx = models.BigIntegerField(validators=[MinValueValidator(0)])
    provider_reward_ugx = models.BigIntegerField(validators=[MinValueValidator(0)])
    admin_reward_ugx = models.BigIntegerField(validators=[MinValueValidator(0)])

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-timestamp"]

# =============================================================
# API CONFIGURATION / PAYMENTS
# =============================================================

class APIConfig(models.Model):
    name = models.CharField(max_length=100, unique=True)
    base_url = models.CharField(max_length=500)
    secret_key = models.TextField(blank=True, null=True)
    public_key = models.TextField(blank=True, null=True)
    webhook_secret = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Transaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    tx_type = models.CharField(max_length=50, choices=TRANSACTION_TYPE_CHOICES)

    amount_ugx = models.BigIntegerField(validators=[MinValueValidator(0)])

    status = models.CharField(max_length=50, choices=TRANSACTION_STATUS_CHOICES, default="pending")

    tx_ref = models.CharField(max_length=100, unique=True, db_index=True)
    provider_reference = models.CharField(max_length=100, null=True, blank=True)

    raw_provider_response = models.JSONField(null=True, blank=True)
    failure_reason = models.TextField(null=True, blank=True)

    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]