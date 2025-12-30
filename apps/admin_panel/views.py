import random
import string
import uuid
from datetime import timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db import models
from django.db.models import Count, Sum
from django.urls import reverse

from .forms import (
    PendingManualUserForm,
    ManualUserOTPForm,
    GiftOfferForm,
    TaskControlForm,
    PayrollEntryForm,
    AdminSettingsForm,
)

from .models import (
    PendingManualUser,
    ManualUserOTP,
    GiftOffer,
    TaskControl,
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


# =============================
# System Log Model
# =============================
class SystemLog(models.Model):
    LEVEL_CHOICES = [
        ("INFO", "Info"),
        ("SUCCESS", "Success"),
        ("WARNING", "Warning"),
        ("ERROR", "Error"),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.CharField(max_length=150, null=True, blank=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default="INFO")
    message = models.TextField()
    related_object = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]


# =============================
# Logging Helper
# =============================
def log_event(message, level="INFO", user=None, related_object=None):
    SystemLog.objects.create(
        message=message,
        level=level,
        user=getattr(user, "username", None) if user else None,
        related_object=str(related_object) if related_object else None,
    )


# =============================
# Admin Login / Logout / Dashboard
# =============================
def unified_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("admin_panel:dashboard")
    return admin_login(request)


def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user and user.is_staff:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}")
            log_event("Admin logged in", level="SUCCESS", user=user)
            return redirect("admin_panel:dashboard")

        messages.error(request, "Invalid admin credentials.")
        log_event("Failed admin login attempt", level="ERROR")

    return render(request, "admin_panel/login.html")


@login_required(login_url="admin_panel:login")
def admin_logout(request):
    log_event("Admin logged out", user=request.user)
    logout(request)
    messages.info(request, "Logged out successfully.")
    return redirect("admin_panel:login")


@login_required(login_url="admin_panel:login")
@staff_member_required
def admin_dashboard(request):
    users_count = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    gifts_count = GiftOffer.objects.count()

    return render(
        request,
        "admin_panel/users.html",
        {
            "users_count": users_count,
            "active_users": active_users,
            "gifts_count": gifts_count,
        },
    )


# =============================
# Manual User / OTP
# =============================
@login_required
@staff_member_required
def manual_login_view(request):
    if request.method == "POST":
        form = PendingManualUserForm(request.POST)
        if form.is_valid():
            pending = form.save(commit=False)
            pending.invited_by = request.user.username
            pending.save()

            otp = generate_otp()
            ManualUserOTP.create_otp(pending, otp, ttl_minutes=15)
            send_otp_email(pending.email, otp)

            request.session["pending_manual_user_id"] = pending.id
            messages.success(request, "OTP sent successfully.")
            return redirect("admin_panel:verify_otp")
    else:
        form = PendingManualUserForm()

    return render(request, "admin_panel/manual_login.html", {"form": form})


@login_required
@staff_member_required
def verify_otp_view(request):
    pending_id = request.session.get("pending_manual_user_id")
    if not pending_id:
        messages.error(request, "No pending user found.")
        return redirect("admin_panel:manual_login")

    pending = get_object_or_404(PendingManualUser, id=pending_id)

    if request.method == "POST":
        form = ManualUserOTPForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["otp_code"]
            otp = pending.otps.filter(otp_code=code).order_by("-created_at").first()

            if not otp or not otp.is_valid():
                messages.error(request, "Invalid or expired OTP.")
            else:
                temp_password = generate_temporary_password()
                username_base = pending.email.split("@")[0]
                username = username_base
                counter = 1

                while User.objects.filter(username=username).exists():
                    username = f"{username_base}{counter}"
                    counter += 1

                user = User.objects.create_user(
                    username=username,
                    email=pending.email,
                    password=temp_password,
                    first_name=pending.name,
                )

                profile = user.profile
                profile.invitation_code = generate_invitation_code()
                profile.trial_expiry = timezone.now() + timedelta(days=30)
                profile.save()

                send_account_created_email(
                    pending.email, username, profile.invitation_code, temp_password
                )

                pending.delete()
                del request.session["pending_manual_user_id"]

                messages.success(request, "User created successfully.")
                return redirect("admin_panel:manual_login")
    else:
        form = ManualUserOTPForm()

    return render(request, "admin_panel/verify_otp.html", {"form": form})


# =============================
# Gift Offers
# =============================
@login_required(login_url="admin_panel:login")
@staff_member_required
def gift_offer_list(request):
    gifts = GiftOffer.objects.all()
    return render(request, "admin_panel/gift_offer_list.html", {"gifts": gifts})


@login_required(login_url="admin_panel:login")
@staff_member_required
def gift_offer_create(request):
    form = GiftOfferForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        gift = form.save(commit=False)
        gift.created_by = request.user
        gift.save()
        messages.success(request, "Gift offer created.")
        return redirect("admin_panel:gift_offer_list")
    return render(request, "admin_panel/gift_offer_form.html", {"form": form})


@login_required(login_url="admin_panel:login")
@staff_member_required
def gift_offer_edit(request, pk):
    gift = get_object_or_404(GiftOffer, pk=pk)
    form = GiftOfferForm(request.POST or None, request.FILES or None, instance=gift)
    if form.is_valid():
        form.save()
        messages.success(request, "Gift updated.")
        return redirect("admin_panel:gift_offer_list")
    return render(request, "admin_panel/gift_offer_form.html", {"form": form})


@login_required(login_url="admin_panel:login")
@staff_member_required
def gift_offer_delete(request, pk):
    get_object_or_404(GiftOffer, pk=pk).delete()
    messages.success(request, "Gift deleted.")
    return redirect("admin_panel:gift_offer_list")


# =============================
# Payroll
# =============================
@login_required(login_url="admin_panel:login")
@staff_member_required
def payroll_list(request):
    payrolls = PayrollEntry.objects.all()
    return render(request, "admin_panel/payroll_list.html", {"payrolls": payrolls})


# =============================
# Admin Settings
# =============================
@login_required(login_url="admin_panel:login")
@staff_member_required
def admin_settings_view(request):
    instance = AdminSettings.objects.first()
    form = AdminSettingsForm(request.POST or None, instance=instance)

    if form.is_valid():
        form.save()
        messages.success(request, "Settings updated.")
        return redirect("admin_panel:settings")

    return render(request, "admin_panel/settings.html", {"form": form})


# =============================
# Analytics
# =============================
@login_required(login_url="admin_panel:login")
@staff_member_required
def graphs_view(request):
    today = timezone.now().date()

    if request.GET.get("format") == "json":
        months = [(today - timedelta(days=30 * i)).strftime("%b") for i in range(6)]
        months.reverse()

        user_growth = [
            User.objects.filter(
                date_joined__range=[
                    today - timedelta(days=30 * (i + 1)),
                    today - timedelta(days=30 * i),
                ]
            ).count()
            for i in range(6)
        ]

        return JsonResponse(
            {
                "user_growth": {
                    "labels": months,
                    "values": user_growth,
                }
            }
        )

    return render(request, "admin_panel/graphs.html")
