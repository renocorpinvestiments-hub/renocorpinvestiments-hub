from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from django.db import transaction as db_transaction
from django.db.models import F, Sum
from django.urls import reverse
import uuid
import json
import logging
import datetime

logger = logging.getLogger(__name__)

from .models import (
    UserProfile,
    VideoTask,
    SurveyTask,
    AppTest,
    GiftOffer,
    Transaction,
    Notification,
    TaskProgress,
    LedgerEntry,
    CompletedTask,
)

from apps.admin_panel.models import AdminSettings

User = get_user_model()

# ============================================================
# HELPERS
# ============================================================

def get_or_create_profile(user):
    try:
        return UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        phone = f"0{user.id}{uuid.uuid4().hex[:6]}"
        return UserProfile.objects.create(user=user, phone=phone)


def json_error(message, status=400):
    return JsonResponse({"ok": False, "message": message}, status=status)


def is_withdraw_enabled():
    try:
        s = AdminSettings.objects.last()
        return bool(s and s.theme_mode == "dark")
    except Exception:
        return False


# ============================================================
# HOME
# ============================================================
@login_required
def home_view(request):
    user = request.user
    profile = get_or_create_profile(user)

    notifications = Notification.objects.filter(user=user).order_by("-created_at")[:8]
    messages_list = [n.message for n in notifications]
    Notification.objects.filter(id__in=[n.id for n in notifications]).update(is_read=True)

    context = {
        "today_earnings": profile.today_earnings,
        "balance": profile.balance,
        "commission": profile.commission,
        "invites": profile.invites,
        "notifications": messages_list,
        "current_page": "home",
    }
    return render(request, "home.html", context)


# ============================================================
# TASKS (DB-DRIVEN FROM AI CORE)
# ============================================================
@login_required
def tasks_view(request):
    user = request.user
    profile = get_or_create_profile(user)

    # Dashboard limits (can later be admin-controlled)
    videos_limit = 10
    surveys_limit = 2
    app_tests_limit = 1

    today = timezone.localdate()

    # ------------------------------
    # Progress reset
    # ------------------------------
    progress, _ = TaskProgress.objects.get_or_create(user=user)
    if progress.last_reset < today:
        progress.total_tasks = 0
        progress.completed_tasks = 0
        progress.progress = 0
        progress.last_reset = today
        progress.save()

    # ------------------------------
    # Completed tasks (AI core truth)
    # ------------------------------
    completed_ids = set(
        CompletedTask.objects.filter(user=user)
        .values_list("task_id", flat=True)
    )

    # ------------------------------
    # VIDEO TASKS
    # ------------------------------
    videos_qs = (
        VideoTask.objects.filter(active=True)
        .exclude(task_id__in=completed_ids)
        .order_by("-reward", "-created_at")[:videos_limit]
    )

    videos = [
        {
            "id": v.task_id,
            "title": v.title,
            "thumbnail": v.thumbnail,
            "url": v.video_url,
            "reward": float(v.reward),
        }
        for v in videos_qs
    ]

    # ------------------------------
    # SURVEYS (iframe / provider URL)
    # ------------------------------
    surveys_qs = (
        SurveyTask.objects.filter(active=True)
        .exclude(task_id__in=completed_ids)
        .order_by("-reward", "-created_at")[:surveys_limit]
    )

    surveys = [
        {
            "id": s.task_id,
            "title": s.title,
            "provider_url": s.iframe_url or s.provider_url,
            "reward": float(s.reward),
        }
        for s in surveys_qs
    ]

    # ------------------------------
    # APP TEST (single highest reward)
    # ------------------------------
    app_test = None
    if app_tests_limit:
        app = (
            AppTest.objects.filter(active=True)
            .exclude(task_id__in=completed_ids)
            .order_by("-reward", "-created_at")
            .first()
        )
        if app:
            app_test = {
                "id": app.task_id,
                "name": app.title,
                "description": app.description,
                "download_url": app.download_url,
                "reward": float(app.reward),
            }

    # ------------------------------
    # Progress calculation
    # ------------------------------
    total_tasks = len(videos) + len(surveys) + (1 if app_test else 0)
    completed_today = CompletedTask.objects.filter(
        user=user, completed_at__date=today
    ).count()

    progress.total_tasks = total_tasks
    progress.completed_tasks = completed_today
    progress.update_progress()

    context = {
        "videos": videos,
        "surveys": surveys,
        "app_test": app_test,
        "progress": float(progress.progress),
        "current_page": "tasks",
    }
    return render(request, "tasks.html", context)


# ============================================================
# ACCOUNT
# ============================================================
@login_required
def account_view(request):
    user = request.user
    profile = get_or_create_profile(user)

    transactions = Transaction.objects.filter(user=user).order_by("-created_at")[:12]

    context = {
        "profile": profile,
        "transactions": transactions,
        "withdraw_enabled": is_withdraw_enabled(),
        "support_number": getattr(settings, "SUPPORT_WHATSAPP_NUMBER", ""),
        "current_page": "account",
    }
    return render(request, "account.html", context)


# ============================================================
# SUBSCRIBE
# ============================================================
@login_required
def subscribe_view(request):
    if request.method != "POST":
        return json_error("POST required")

    data = json.loads(request.body)
    password = data.get("password")

    if not request.user.check_password(password):
        return json_error("Incorrect password", 403)

    amount = Decimal(getattr(settings, "SUBSCRIPTION_FEE", "10000"))

    tx = Transaction.objects.create(
        user=request.user,
        amount=amount,
        transaction_type="subscription",
        status="initiated",
        reference=uuid.uuid4().hex,
    )

    try:
        from apps.payments.flw_api import initiate_payment
        resp = initiate_payment(request.user, float(amount), tx.id)
        tx.status = "processing"
        tx.save()
        return JsonResponse({"ok": True, "payment_url": resp.get("payment_url")})
    except Exception:
        tx.status = "pending"
        tx.save()
        return json_error("Payment initiation failed", 500)


# ============================================================
# WITHDRAW
# ============================================================
@login_required
def withdraw_view(request):
    if not is_withdraw_enabled():
        return json_error("Withdrawals disabled", 403)

    data = json.loads(request.body)
    amount = Decimal(str(data.get("amount", 0)))
    password = data.get("password")

    user = request.user
    profile = get_or_create_profile(user)

    if not user.check_password(password):
        return json_error("Incorrect password", 403)

    if amount <= 0 or amount > profile.balance:
        return json_error("Invalid amount")

    with db_transaction.atomic():
        profile = UserProfile.objects.select_for_update().get(pk=profile.pk)

        tx = Transaction.objects.create(
            user=user,
            amount=amount,
            transaction_type="withdraw",
            status="pending",
            reference=uuid.uuid4().hex,
        )

        LedgerEntry.objects.create(
            user=user,
            amount=amount,
            entry_type="debit",
            reason="withdrawal",
            reference=tx.reference,
        )

        profile.balance = F("balance") - amount
        profile.save()

    try:
        from apps.ai_core.tasks import execute_withdrawal
        execute_withdrawal.delay(tx.id)
    except Exception:
        tx.status = "manual"
        tx.save()

    return JsonResponse({"ok": True, "message": "Withdrawal processing"})


# ============================================================
# GIFTS
# ============================================================
@login_required
def gifts_view(request):
    user = request.user
    profile = get_or_create_profile(user)

    offer = GiftOffer.objects.filter(active=True).order_by("-created_at").first()

    context = {
        "current_offer": offer,
        "support_number": getattr(settings, "SUPPORT_WHATSAPP_NUMBER", ""),
        "current_page": "gifts",
    }
    return render(request, "gifts.html", context)


# ============================================================
# INVITE
# ============================================================
@login_required
def invite_view(request):
    profile = get_or_create_profile(request.user)
    url = request.build_absolute_uri(
        reverse("accounts:signup") + f"?invite={profile.invitation_code}"
    )
    return JsonResponse({"ok": True, "invite_code": profile.invitation_code, "signup_url": url})


# ============================================================
# CHANGE PASSWORD
# ============================================================
@login_required
def change_password_view(request):
    if request.method != "POST":
        return redirect("dashboard:account")

    user = request.user
    if not user.check_password(request.POST.get("old_password")):
        messages.error(request, "Wrong password")
        return redirect("dashboard:account")

    user.set_password(request.POST.get("new_password1"))
    user.save()
    update_session_auth_hash(request, user)

    messages.success(request, "Password updated")
    return redirect("dashboard:account")
