from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db import models
from django.db.models import Count, Sum

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
)

from .utils import (
    generate_otp,
    generate_invitation_code,
    generate_temporary_password,
    send_otp_email,
    send_account_created_email,
)

from apps.accounts.models import User

# Optional transactions app
try:
    from transactions.models import Transaction
except ImportError:
    Transaction = None


# =====================================================
# SYSTEM LOG MODEL (USED BY TRANSACTIONS PAGE)
# =====================================================
class SystemLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=20)
    message = models.TextField()

    class Meta:
        ordering = ["-timestamp"]


# =====================================================
# AUTH (USES SAME LOGIN AS USERS)
# =====================================================
def unified_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("admin_panel:dashboard")
    return redirect("accounts:login")  # your normal user login


@login_required
def admin_logout(request):
    logout(request)
    return redirect("accounts:login")


# =====================================================
# 1️⃣ USERS PAGE (ADMIN DASHBOARD)
# =====================================================
@login_required
@staff_member_required
def admin_dashboard(request):
    users = User.objects.all()
    return render(request, "admin_panel/users.html", {"users": users})


# =====================================================
# 2️⃣ MANUAL LOGIN PAGE
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

    return render(request, "admin_panel/manual_login.html", {"form": form})


# =====================================================
# 3️⃣ VERIFY OTP PAGE
# =====================================================
@login_required
@staff_member_required
def verify_otp_view(request):
    pending_id = request.session.get("pending_manual_user_id")
    pending = get_object_or_404(PendingManualUser, id=pending_id)

    form = ManualUserOTPForm(request.POST or None)
    if form.is_valid():
        otp = form.cleaned_data["otp_code"]
        if pending.verify_otp(otp):
            password = generate_temporary_password()
            user = User.objects.create_user(
                username=pending.email.split("@")[0],
                email=pending.email,
                password=password,
            )
            send_account_created_email(
                pending.email, user.username, generate_invitation_code(), password
            )
            pending.delete()
            return redirect("admin_panel:dashboard")

    return render(request, "admin_panel/verify_otp.html", {"form": form})


# =====================================================
# 4️⃣ GRAPHS PAGE
# =====================================================
@login_required
@staff_member_required
def graphs_view(request):
    users_count = User.objects.count()
    return render(request, "admin_panel/graphs.html", {"users_count": users_count})


# =====================================================
# 5️⃣ TRANSACTIONS + PAYROLL + SYSTEM ERRORS
# =====================================================
@login_required
@staff_member_required
def transaction_page(request):
    payrolls = PayrollEntry.objects.all()
    system_logs = SystemLog.objects.all()

    return render(
        request,
        "admin_panel/transactions.html",
        {
            "payrolls": payrolls,
            "system_logs": system_logs,
        },
    )


# =====================================================
# 6️⃣ SETTINGS PAGE
# =====================================================
@login_required
@staff_member_required
def admin_settings_view(request):
    instance = AdminSettings.objects.first()
    form = AdminSettingsForm(request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        messages.success(request, "Settings updated")
    return render(request, "admin_panel/settings.html", {"form": form})


# =====================================================
# 7️⃣ GIFTS UPLOAD PAGE
# =====================================================
@login_required
@staff_member_required
def gift_upload_view(request):
    form = GiftOfferForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Gift uploaded")
    return render(request, "admin_panel/gift_upload.html", {"form": form})
