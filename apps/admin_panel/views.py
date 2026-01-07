from django.db import transaction
import re
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db.models import Sum, Count
from .models import AdminNotification
from .forms import PendingManualUserForm, GiftOfferForm, AdminSettingsForm
from django.utils.timezone import now
from .models import (
    PendingManualUser,
    GiftOffer,
    PayrollEntry,
    AdminSettings,
    UserProfile,
    RewardLog,
    TransactionLog,
    AdminLoginAudit,
)

from .utils import (
    generate_invitation_code,
    generate_temporary_password,
)

from apps.accounts.models import User
import resource
import logging

log = logging.getLogger(__name__)

def mem():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


# =====================================================
# AUTH
# =====================================================
def unified_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("admin_panel:dashboard")
    return redirect("accounts:login")


@login_required
def admin_logout(request):
    logout(request)
    return redirect("accounts:login")


# =====================================================
# 1️⃣ USERS DASHBOARD
# =====================================================
@login_required
@staff_member_required
def admin_dashboard(request):
    users = User.objects.all()
    total_balance = UserProfile.objects.aggregate(total=Sum("balance"))["total"] or 0
    

    return render(request, "users.html", {
        "users": users,
        "total_balance": total_balance,
    })

@login_required
@staff_member_required
def update_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        # -------- USER --------
        full_name = request.POST.get("name", "").strip()
        if full_name:
            parts = full_name.split(" ", 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ""

        user.email = request.POST.get("email", user.email)
        user.save(update_fields=["first_name", "last_name", "email"])

        # -------- PROFILE --------
        profile.age = request.POST.get("age") or profile.age
        profile.gender = request.POST.get("gender") or profile.gender
        profile.account_number = request.POST.get("account_number") or profile.account_number
        profile.invitation_code = request.POST.get("invitation_code") or profile.invitation_code
        profile.invited_by = request.POST.get("invited_by") or profile.invited_by
        profile.subscription_status = request.POST.get(
            "subscription_status", profile.subscription_status
        )
        profile.save()

        messages.success(request, "User updated successfully")

    return redirect("admin_panel:dashboard")
# =====================================================
# 2️⃣ ANALYTICS / GRAPHS
# =====================================================
@login_required
@staff_member_required
def graphs_view(request):
    from django.db.models.functions import TruncHour, TruncDay, TruncMonth

    range_type = request.GET.get("range", "week")
    now = timezone.now()

    # ---------------------------
    # USER GROWTH (DYNAMIC)
    # ---------------------------
    if range_type == "day":
        start = now - timedelta(days=1)
        growth_qs = (
            User.objects.filter(date_joined__gte=start)
            .annotate(period=TruncHour("date_joined"))
            .values("period")
            .annotate(count=Count("id"))
            .order_by("period")
        )

    elif range_type == "month":
        start = now - timedelta(days=30)
        growth_qs = (
            User.objects.filter(date_joined__gte=start)
            .annotate(period=TruncDay("date_joined"))
            .values("period")
            .annotate(count=Count("id"))
            .order_by("period")
        )

    elif range_type == "year":
        start = now - timedelta(days=365)
        growth_qs = (
            User.objects.filter(date_joined__gte=start)
            .annotate(period=TruncMonth("date_joined"))
            .values("period")
            .annotate(count=Count("id"))
            .order_by("period")
        )

    else:  # week (default)
        start = now - timedelta(days=7)
        growth_qs = (
            User.objects.filter(date_joined__gte=start)
            .annotate(period=TruncDay("date_joined"))
            .values("period")
            .annotate(count=Count("id"))
            .order_by("period")
        )

    user_growth_data = {
        "labels": [g["period"].strftime("%Y-%m-%d %H:%M") for g in growth_qs],
        "values": [g["count"] for g in growth_qs],
    }

    # ---------------------------
    # REFERRAL RATE (PER HOUR)
    # ---------------------------
    referral_qs = (
        User.objects.filter(invited_by__isnull=False)
        .annotate(hour=TruncHour("date_joined"))
        .values("hour")
        .annotate(count=Count("id"))
        .order_by("hour")
    )

    referral_data = {
        "labels": [r["hour"].strftime("%H:%M") for r in referral_qs],
        "values": [r["count"] for r in referral_qs],
    }

    return render(request, "graphs.html", {
        "user_growth_data": user_growth_data,
        "referral_data": referral_data,
        "range_type": range_type,
    })

# =====================================================
# 3️⃣ TRANSACTIONS + SYSTEM LOGS + PAYROLL
# =====================================================
@login_required
@staff_member_required
def transaction_page(request):
    transactions = TransactionLog.objects.select_related("user").all()
    system_logs = TransactionLog.objects.filter(txn_type="system")
    payrolls = PayrollEntry.objects.all()

    return render(request, "transactions.html", {
        "transactions": transactions,
        "system_logs": system_logs,
        "payrolls": payrolls,
    })


# =====================================================
# MANUAL USER ONBOARDING
# =====================================================
@login_required
@staff_member_required
def manual_login_view(request):
    form = PendingManualUserForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        pending = PendingManualUser.objects.filter(email__iexact=form.cleaned_data["email"]).first()

        if pending:
            for field in ["name", "age", "gender", "account_number"]:
                setattr(pending, field, form.cleaned_data[field])
            pending.save()
        else:
            pending = form.save()

        request.session["pending_manual_user_id"] = pending.id
        return redirect("admin_panel:verify_admin_password")

    return render(request, "manual_login.html", {"form": form})


@login_required
@staff_member_required
def verify_admin_password(request):
    pending_id = request.session.get("pending_manual_user_id")
    if not pending_id:
        messages.error(request, "Session expired. Please restart manual login.")
        return redirect("admin_panel:manual_login")

    pending = get_object_or_404(PendingManualUser, id=pending_id)

    if request.method == "POST":
        password = request.POST.get("password")

        if not request.user.check_password(password):
            messages.error(request, "Invalid admin password.")
            return render(request, "verify_admin_password.html")

        with transaction.atomic():
            # Generate username from name
            base = re.sub(r"[^a-zA-Z0-9]", "", pending.name.lower())
            username = base
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base}{counter}"
                counter += 1

            # Generate unique invitation code
            invite = generate_invitation_code()
            while UserProfile.objects.filter(invitation_code=invite).exists():
                invite = generate_invitation_code()

            temp_password = generate_temporary_password()

            user = User.objects.create_user(
                username=username,
                email=pending.email,
                password=temp_password,
                is_active=True,
            )

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.invitation_code = invite
            profile.account_number = pending.account_number
            profile.age = pending.age
            profile.gender = pending.gender
            profile.subscription_status = "active"
            profile.subscription_expiry = timezone.now() + timedelta(days=30)
            profile.invited_by = request.user.username
            profile.save()

            AdminNotification.objects.create(
                title="Manual User Created",
                message=f"{user.email} onboarded by {request.user.username}",
                category="manual_onboarding",
            )

            TransactionLog.objects.create(
                user=user,
                actor=request.user.username,
                amount=0,
                txn_type="system",
                status="success",
                details="Manual onboarding completed",
            )

            request.session["created_user"] = {
                "username": username,
                "password": temp_password,
                "invitation": invite,
            }

            pending.delete()
            request.session.pop("pending_manual_user_id", None)

        return redirect("admin_panel:user_created_success")

    return render(request, "verify_admin_password.html")


@login_required
@staff_member_required
def user_created_success(request):
    creds = request.session.get("created_user")
    if not creds:
        return redirect("admin_panel:dashboard")

    request.session.pop("created_user", None)
    return render(request, "user_created_success.html", {"creds": creds})

# =====================================================
# 5️⃣ ADMIN SETTINGS
# =====================================================
@login_required
@staff_member_required
def admin_settings_view(request):
    instance = AdminSettings.objects.first()
    form = AdminSettingsForm(request.POST or None, instance=instance)

    if request.method == "POST" and form.is_valid():
        # Save theme and support number
        settings_instance = form.save(commit=False)

        # Update admin password if provided
        new_password = form.cleaned_data.get("new_password")
        if new_password:
            request.user.set_password(new_password)
            request.user.save()
            messages.success(request, "Admin password updated. Please log in again.")
            settings_instance.save()
            return redirect("accounts:login")

        settings_instance.save()
        messages.success(request, "Settings updated successfully.")

    return render(request, "settings.html", {"form": form})

# =====================================================
# 6️⃣ GIFT UPLOAD
# =====================================================
@login_required
@staff_member_required
def gift_upload_view(request):
    if request.method == "POST":
        try:
            with transaction.atomic():

                # =========================
                # 1️⃣ CREATE GIFT OFFER
                # =========================
                description = request.POST.get("description", "").strip()
                reward_amount = request.POST.get("reward", 0)
                required_invites = request.POST.get("invites_required", 0)
                extra_videos = request.POST.get("extra_videos", 0)
                earning_per_video = request.POST.get("earning_per_video", 0)

                if not description:
                    messages.error(request, "Gift description is required.")
                    return redirect("admin_panel:gift_upload")

                gift = GiftOffer.objects.create(
                    title=f"Gift-{now().strftime('%Y%m%d%H%M%S')}",
                    description=description,
                    reward_amount=reward_amount,
                    required_invites=required_invites,
                    extra_video_count=extra_videos,
                    earning_per_extra_video=earning_per_video,
                    active=True,
                )

                # =========================
                # 2️⃣ UPDATE TASK CONTROL
                # =========================
                videos_number = request.POST.get("videos_number", 0)
                video_earning = request.POST.get("video_earning", 0)

                surveys_number = request.POST.get("surveys_number", 0)
                survey_earning = request.POST.get("survey_earning", 0)

                app_tests_number = request.POST.get("app_tests_number", 0)
                app_test_earning = request.POST.get("app_test_earning", 0)

                invite_reward = request.POST.get("invite_reward", 0)

                task_control, _ = TaskControl.objects.get_or_create(id=1)

                task_control.videos_count = videos_number
                task_control.video_earning = video_earning

                task_control.surveys_count = surveys_number
                task_control.survey_earning = survey_earning

                task_control.app_tests_count = app_tests_number
                task_control.app_test_earning = app_test_earning

                task_control.invite_cost = invite_reward
                task_control.save()

                # =========================
                # 3️⃣ AUDIT LOG
                # =========================
                AdminNotification.objects.create(
                    title="Gift & Task Control Updated",
                    message=f"Gift '{gift.title}' uploaded by {request.user.username}",
                    category="gift_upload",
                )

                messages.success(request, "Gift and task settings saved successfully.")
                return redirect("admin_panel:gift_upload")

        except Exception as e:
            messages.error(request, f"Error saving gift: {str(e)}")

    # =========================
    # GET REQUEST
    # =========================
    task_control = TaskControl.objects.first()

    return render(
        request,
        "gift_upload.html",
        {
            "task_control": task_control,
        }
                )
