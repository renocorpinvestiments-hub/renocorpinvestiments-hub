from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db.models import Sum, Count
from django.core.exceptions import ObjectDoesNotExist

from .forms import (
    PendingManualUserForm,
    ManualUserOTPForm,
    GiftOfferForm,
    AdminSettingsForm,
)

from .models import (
    PendingManualUser,
    ManualUserOTP,
    GiftOffer,
    PayrollEntry,
    AdminSettings,
    UserProfile,
    RewardLog,
    TransactionLog,
    AdminLoginAudit,
)

from .utils import (
    generate_otp,
    generate_invitation_code,
    generate_temporary_password,
    send_otp_email,
    send_account_created_email,
)

from apps.accounts.models import User


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
# 4️⃣ MANUAL USER ONBOARDING
# =====================================================
@login_required
@staff_member_required
def manual_login_view(request):
    form = PendingManualUserForm(request.POST or None)

    if form.is_valid():
        pending = form.save()
        otp = generate_otp()
        ManualUserOTP.create_otp(pending, otp)
        send_otp_email(pending.email, otp)

        request.session["pending_manual_user_id"] = pending.id
        return redirect("admin_panel:verify_otp")

    return render(request, "manual_login.html", {"form": form})


@login_required
@staff_member_required
def verify_otp_view(request):
    pending_id = request.session.get("pending_manual_user_id")
    pending = get_object_or_404(PendingManualUser, id=pending_id)

    form = ManualUserOTPForm(request.POST or None)

    if form.is_valid():
        if pending.verify_otp(form.cleaned_data["otp_code"]):
            password = generate_temporary_password()

            user = User.objects.create_user(
                username=pending.email.split("@")[0],
                email=pending.email,
                password=password,
            )

            send_account_created_email(
                pending.email,
                user.username,
                generate_invitation_code(),
                password,
            )

            pending.delete()
            return redirect("admin_panel:dashboard")

    return render(request, "verify_otp.html", {"form": form})


# =====================================================
# 5️⃣ ADMIN SETTINGS
# =====================================================
@login_required
@staff_member_required
def admin_settings_view(request):
    instance = AdminSettings.objects.first()
    form = AdminSettingsForm(request.POST or None, instance=instance)

    if form.is_valid():
        form.save()
        messages.success(request, "Settings updated")

    return render(request, "settings.html", {"form": form})


# =====================================================
# 6️⃣ GIFT UPLOAD
# =====================================================
@login_required
@staff_member_required
def gift_upload_view(request):
    form = GiftOfferForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        form.save()
        messages.success(request, "Gift uploaded")

    return render(request, "gift_upload.html", {"form": form})
