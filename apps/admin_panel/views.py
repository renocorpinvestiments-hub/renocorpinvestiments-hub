from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db.models import Sum, Count

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
    users = User.objects.select_related("profile").all()
    total_balance = UserProfile.objects.aggregate(total=Sum("balance"))["total"] or 0

    return render(request, "users.html", {
        "users": users,
        "total_balance": total_balance,
    })

@login_required
def update_user(request, user_id):
    if request.method == "POST":
        user = get_object_or_404(User, id=user_id)

        user.name = request.POST.get("name", user.name)
        user.email = request.POST.get("email", user.email)
        user.age = request.POST.get("age", user.age)

        user.save()

    return redirect("admin_panel:dashboard")
# =====================================================
# 2️⃣ ANALYTICS / GRAPHS
# =====================================================
@login_required
@staff_member_required
def graphs_view(request):
    today = timezone.now()
    week_ago = today - timedelta(days=7)

    total_users = User.objects.count()
    new_users_week = User.objects.filter(date_joined__gte=week_ago).count()

    rewards_total = RewardLog.objects.aggregate(total=Sum("amount"))["total"] or 0
    withdrawals_total = TransactionLog.objects.filter(
        txn_type="withdrawal", status="success"
    ).aggregate(total=Sum("amount"))["total"] or 0

    daily_rewards = RewardLog.objects.filter(created_at__gte=week_ago).values(
        "created_at__date"
    ).annotate(total=Sum("amount")).order_by("created_at__date")

    return render(request, "graphs.html", {
        "total_users": total_users,
        "new_users_week": new_users_week,
        "rewards_total": rewards_total,
        "withdrawals_total": withdrawals_total,
        "daily_rewards": daily_rewards,
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
