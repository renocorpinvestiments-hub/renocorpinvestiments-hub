# apps/admin_panel/views.py

import random
import string
import uuid
from datetime import timedelta
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db import models, transaction as db_transaction
from django.db.models import Count, Sum, F
from django.urls import reverse
from django.conf import settings

from .forms import (
    PendingManualUserForm,
    ManualUserOTPForm,
    GiftOfferForm,
    TaskControlForm,
    PayrollEntryForm,
    AdminSettingsForm,
)
from .models import PendingManualUser, ManualUserOTP, GiftOffer, TaskControl, PayrollEntry, AdminSettings
from .utils import generate_otp, generate_invitation_code, generate_temporary_password, send_otp_email, send_account_created_email

from apps.accounts.models import User  # your custom user model

# Optional transactions app
try:
    from transactions.models import Transaction
except ImportError:
    Transaction = None


# -----------------------------
# System Log Model
# -----------------------------
class SystemLog(models.Model):
    LEVEL_CHOICES = [
        ('INFO', 'Info'),
        ('SUCCESS', 'Success'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
    ]
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.CharField(max_length=150, null=True, blank=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='INFO')
    message = models.TextField()
    related_object = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

# apps/admin_panel/views.py

def unified_login(request):
    # You can reuse admin_login logic
    if request.user.is_authenticated and is_admin(request.user):
        return redirect("admin_panel:dashboard")
    return admin_login(request)


# -----------------------------
# Logging helper
# -----------------------------
def log_event(message, level='INFO', user=None, related_object=None):
    SystemLog.objects.create(
        message=message,
        level=level,
        user=getattr(user, 'username', str(user)) if user else None,
        related_object=str(related_object) if related_object else None
    )



# -----------------------------
# Admin Login / Logout / Dashboard
# -----------------------------
def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user and is_admin(user):
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}")
            log_event(f"Admin {user.username} logged in successfully.", level='SUCCESS', user=user)
            return redirect("admin_panel:dashboard")
        messages.error(request, "Invalid admin credentials.")
        log_event(f"Failed admin login attempt for username: {username}", level='ERROR')
        return redirect("admin_panel:login")
    return render(request, "admin_panel/login.html")


@login_required(login_url="admin_panel:login")
def admin_logout(request):
    log_event(f"Admin {request.user.username} logged out.", level='INFO', user=request.user)
    logout(request)
    messages.info(request, "You have logged out successfully.")
    return redirect("admin_panel:login")


@login_required(login_url="admin_panel:login")
@user_passes_test(is_admin)
def users(request):
    users_count = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    gifts_count = GiftOffer.objects.count()
    log_event(f"Admin {request.user.username} accessed dashboard.", level='INFO', user=request.user)
    return render(
        request,
        "admin_panel/users.html",
        {"users_count": users_count, "active_users": active_users, "gifts_count": gifts_count},
    )


# -----------------------------
# Manual User / OTP
# -----------------------------
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

            request.session['pending_manual_user_id'] = pending.id
            messages.success(request, "OTP sent to the email provided.")
            log_event(f"OTP sent for manual user {pending.email}", level='SUCCESS', user=request.user)
            return redirect(reverse('admin_panel:verify_otp'))
    else:
        form = PendingManualUserForm()
    return render(request, "admin_panel/manual_login.html", {"form": form, "page_title": "MANUAL LOGIN PAGE"})


@login_required
@staff_member_required
def verify_otp_view(request):
    pending_id = request.session.get('pending_manual_user_id')
    if not pending_id:
        messages.error(request, "No pending manual user found. Please start from Manual Login page.")
        log_event("OTP verification failed: No pending manual user.", level='ERROR', user=request.user)
        return redirect(reverse('admin_panel:manual_login'))

    pending = get_object_or_404(PendingManualUser, id=pending_id)

    if request.method == "POST":
        form = ManualUserOTPForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['otp_code'].strip()
            otp_objs = pending.otps.filter(otp_code=code).order_by('-created_at')
            if not otp_objs.exists():
                messages.error(request, "Invalid OTP.")
                log_event(f"Invalid OTP attempt for {pending.email}", level='WARNING', user=request.user)
            else:
                otp_obj = otp_objs.first()
                if not otp_obj.is_valid():
                    messages.error(request, "OTP expired.")
                    log_event(f"Expired OTP attempt for {pending.email}", level='WARNING', user=request.user)
                else:
                    # Create actual user
                    temp_password = generate_temporary_password()
                    username_base = pending.email.split('@')[0]
                    username = username_base
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{username_base}{counter}"
                        counter += 1

                    user = User.objects.create_user(
                        username=username,
                        email=pending.email,
                        password=temp_password,
                        first_name=pending.name
                    )

                    profile = user.profile
                    profile.account_number = pending.account_number
                    profile.age = pending.age
                    profile.gender = pending.gender
                    profile.invited_by = pending.invited_by
                    profile.invitation_code = generate_invitation_code()
                    profile.total_invitations = 0
                    profile.subscription_status = 'trial'
                    profile.balance = 0
                    profile.trial_expiry = timezone.now() + timedelta(days=30)
                    profile.save()

                    pending.invitation_code = profile.invitation_code
                    pending.temporary_password = temp_password
                    pending.verified = True
                    pending.save()

                    send_account_created_email(pending.email, username, profile.invitation_code, temp_password)
                    del request.session['pending_manual_user_id']

                    messages.success(request, "User created and account details sent by email.")
                    log_event(f"Manual user account created for {pending.email}", level='SUCCESS', user=request.user)
                    return redirect(reverse('admin_panel:manual_login'))
    else:
        form = ManualUserOTPForm()
    return render(request, "admin_panel/verify_otp.html", {"form": form, "pending": pending})


# -----------------------------
# System / Transaction Logs
# -----------------------------
@login_required(login_url="admin_panel:login")
@user_passes_test(is_admin)
def transaction_page(request):
    logs = SystemLog.objects.all()
    return render(request, "admin_panel/transaction_page.html", {"logs": logs})


# -----------------------------
# Gift Offers Management
# -----------------------------
@login_required(login_url="admin_panel:login")
@user_passes_test(is_admin)
def gift_offer_list(request):
    gifts = GiftOffer.objects.all()
    log_event(f"Accessed gift offer list", level='INFO', user=request.user)
    return render(request, "admin_panel/gift_offer_list.html", {"gifts": gifts})


@login_required(login_url="admin_panel:login")
@user_passes_test(is_admin)
def gift_offer_create(request):
    if request.method == "POST":
        form = GiftOfferForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = obj.created_by or request.user
            obj.save()
            messages.success(request, "Gift offer added successfully.")
            log_event(f"Gift offer created: {obj}", level='SUCCESS', user=request.user)
            return redirect("admin_panel:gift_offer_list")
    else:
        form = GiftOfferForm()
    return render(request, "admin_panel/gift_offer_form.html", {"form": form})


@login_required(login_url="admin_panel:login")
@user_passes_test(is_admin)
def gift_offer_edit(request, pk):
    gift = get_object_or_404(GiftOffer, pk=pk)
    if request.method == "POST":
        form = GiftOfferForm(request.POST, request.FILES, instance=gift)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = gift.created_by or request.user
            obj.save()
            messages.success(request, "Gift offer updated successfully.")
            log_event(f"Gift offer updated: {obj}", level='SUCCESS', user=request.user)
            return redirect("admin_panel:gift_offer_list")
    else:
        form = GiftOfferForm(instance=gift)
    return render(request, "admin_panel/gift_offer_form.html", {"form": form})


@login_required(login_url="admin_panel:login")
@user_passes_test(is_admin)
def gift_offer_delete(request, pk):
    gift = get_object_or_404(GiftOffer, pk=pk)
    gift.delete()
    messages.success(request, "Gift offer deleted.")
    log_event(f"Gift offer deleted: {gift}", level='SUCCESS', user=request.user)
    return redirect("admin_panel:gift_offer_list")


# -----------------------------
# Task Control
# -----------------------------
@login_required(login_url="admin_panel:login")
@user_passes_test(is_admin)
def task_control_view(request):
    instance = TaskControl.objects.first()
    if request.method == "POST":
        form = TaskControlForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Task control updated.")
            log_event("Task control updated", level='SUCCESS', user=request.user)
            return redirect("admin_panel:task_control")
    else:
        form = TaskControlForm(instance=instance)
    return render(request, "admin_panel/task_control.html", {"form": form})


# -----------------------------
# Payroll Management
# -----------------------------
@login_required(login_url="admin_panel:login")
@user_passes_test(is_admin)
def payroll_list(request):
    payrolls = PayrollEntry.objects.all().order_by("-created_at")
    log_event("Accessed payroll list", level='INFO', user=request.user)
    return render(request, "admin_panel/payroll_list.html", {"payrolls": payrolls})


@login_required(login_url="admin_panel:login")
@user_passes_test(is_admin)
def payroll_add(request):
    if request.method == "POST":
        form = PayrollEntryForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            messages.success(request, "Payroll record added successfully.")
            log_event(f"Payroll record added: {obj}", level='SUCCESS', user=request.user)
            return redirect("admin_panel:payroll_list")
    else:
        form = PayrollEntryForm()
    return render(request, "admin_panel/payroll_form.html", {"form": form})


@login_required(login_url="admin_panel:login")
@user_passes_test(is_admin)
def payroll_edit(request, pk):
    payroll = get_object_or_404(PayrollEntry, pk=pk)
    if request.method == "POST":
        form = PayrollEntryForm(request.POST, instance=payroll)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = payroll.created_by or request.user
            obj.save()
            messages.success(request, "Payroll updated successfully.")
            log_event(f"Payroll record updated: {obj}", level='SUCCESS', user=request.user)
            return redirect("admin_panel:payroll_list")
    else:
        form = PayrollEntryForm(instance=payroll)
    return render(request, "admin_panel/payroll_form.html", {"form": form})


@login_required(login_url="admin_panel:login")
@user_passes_test(is_admin)
def payroll_delete(request, pk):
    payroll = get_object_or_404(PayrollEntry, pk=pk)
    payroll.delete()
    messages.success(request, "Payroll record deleted.")
    log_event(f"Payroll record deleted: {payroll}", level='SUCCESS', user=request.user)
    return redirect("admin_panel:payroll_list")


# -----------------------------
# Admin Settings
# -----------------------------
@login_required(login_url="admin_panel:login")
@user_passes_test(is_admin)
def admin_settings_view(request):
    settings_instance = AdminSettings.objects.first()
    if request.method == "POST":
        form = AdminSettingsForm(request.POST, instance=settings_instance)
        if form.is_valid():
            form.save()
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")
            if new_password or confirm_password:
                if new_password != confirm_password:
                    messages.error(request, "Passwords do not match.")
                    log_event("Admin password update failed: mismatch", level='WARNING', user=request.user)
                    return redirect("admin_panel:settings")
                if len(new_password) < 6:
                    messages.error(request, "Password must be at least 6 characters long.")
                    log_event("Admin password update failed: too short", level='WARNING', user=request.user)
                    return redirect("admin_panel:settings")
                request.user.set_password(new_password)
                request.user.save()
                messages.success(request, "Admin password updated successfully. Please log in again.")
                log_event("Admin password updated successfully", level='SUCCESS', user=request.user)
                return redirect("admin_panel:login")
            messages.success(request, "Settings updated successfully.")
            log_event("Admin settings updated", level='SUCCESS', user=request.user)
            return redirect("admin_panel:settings")
    else:
        form = AdminSettingsForm(instance=settings_instance)
    return render(request, "admin_panel/settings.html", {"form": form})


# -----------------------------
# Analytics / Graphs
# -----------------------------
@login_required(login_url="admin_panel:login")
@user_passes_test(is_admin)
def graphs_view(request):
    today = timezone.now().date()

    if request.GET.get("format") == "json":
        months = [(today - timedelta(days=30 * i)).strftime("%b") for i in reversed(range(6))]
        user_growth_data = [
            User.objects.filter(date_joined__range=[today - timedelta(days=30*(i+1)), today - timedelta(days=30*i)]).count()
            for i in range(6)
        ]
        active_count = User.objects.filter(profile__subscription_status="active").count()
        expired_count = User.objects.filter(profile__subscription_status="expired").count()
        revenue_data = []
        if Transaction:
            for i in range(6):
                start = today - timedelta(days=30*(i+1))
                end = today - timedelta(days=30*i)
                revenue = Transaction.objects.filter(created_at__range=[start, end]).aggregate(total=Sum("amount"))["total"] or 0
                revenue_data.insert(0, float(revenue))
        else:
            revenue_data = [0]*6
        invitation_data = User.objects.values("profile__invited_by").annotate(total=Count("id")).order_by("-total")[:5]
        invitation_labels = [i["profile__invited_by"] or "Unknown" for i in invitation_data]
        invitation_values = [i["total"] for i in invitation_data]
        return JsonResponse({
            "user_growth": {"labels": months, "values": user_growth_data},
            "subscription_status": [active_count, expired_count],
            "revenue_flow": {"labels": months, "values": revenue_data},
            "invitation_performance": {"labels": invitation_labels, "values": invitation_values},
        })

    return render(request, "admin_panel/graphs.html")


# -----------------------------
# Simple Render Pages
# -----------------------------
@login_required
@staff_member_required
def users_view(request):
    return render(request, "admin_panel/users.html")


@login_required
@staff_member_required
def gift_upload_view(request):
    return render(request, "admin_panel/gift_upload.html")


@login_required
@staff_member_required
def transactions_view(request):
    return render(request, "admin_panel/transactions.html")
