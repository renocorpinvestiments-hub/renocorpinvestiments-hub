from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

from .models import User, EmailOTP
from .forms import LoginForm, SignupForm, OTPVerificationForm, generate_otp
import datetime
from django.db import transaction

def fix_blank_account_numbers():
    from .models import User

    with transaction.atomic():
        broken_users = User.objects.filter(
            account_number__isnull=True
        ) | User.objects.filter(account_number="")

        for user in broken_users:
            user.account_number = f"TEMP-{user.id}"
            user.save(update_fields=["account_number"])
# ---------------------------------------------------
# LOGIN VIEW
# ---------------------------------------------------
def login_view(request):
    fix_blank_account_numbers()   # 👈 runs once after deploy

    form = LoginForm(request, data=request.POST or None)
    """
    Handles login for both admin and normal users.
    Admin access is determined by real Django permissions.
    """
    form = LoginForm(request, data=request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")

            user = authenticate(request, username=username, password=password)

            if user:
                login(request, user)

                # -------------------------------
                # ADMIN ACCESS CONTROL (FIXED)
                # -------------------------------
                if user.is_superuser or user.is_staff:
                    return redirect("admin_panel:users")

                # Normal user login
                return redirect("dashboard:home")

            messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Please check your input fields.")

    return render(request, "login.html", {"form": form})


# ---------------------------------------------------
# SIGNUP VIEW
# ---------------------------------------------------
def signup_view(request):
    """
    Handles new user signup.
    After saving → user inactive → send OTP → move to verify page.
    """
    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            inviter_code = form.cleaned_data["invitation_code"]
            inviter = User.objects.filter(invitation_code=inviter_code).first()

            # Create user but inactive
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.is_active = False
            user.invited_by = inviter
            user.subscription_status = "inactive"
            user.save()

            # ---------------------------------
            # Create OTP
            # ---------------------------------
            otp_code = generate_otp()

            EmailOTP.objects.create(
                email=user.email,
                otp=otp_code,
                created_at=timezone.now()
            )

            # Send OTP email
            send_mail(
                subject="RENOCORP Account Verification Code",
                message=f"Your RENOCORP verification code is {otp_code}. It expires in 10 minutes.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )

            request.session["verify_email"] = user.email
            messages.info(request, "OTP has been sent to your email.")
            return redirect("accounts:verify_otp")

    else:
        form = SignupForm()

    return render(request, "signup.html", {"form": form})


# ---------------------------------------------------
# OTP VERIFICATION VIEW
# ---------------------------------------------------
def verify_otp_view(request):
    email = request.session.get("verify_email")

    if not email:
        messages.error(request, "Session expired. Please sign up again.")
        return redirect("accounts:signup")

    if request.method == "POST":
        form = OTPVerificationForm(request.POST)

        if form.is_valid():
            otp_entered = form.cleaned_data["otp"]

            try:
                otp_record = EmailOTP.objects.get(
                    email=email,
                    otp=otp_entered,
                    verified=False
                )
            except EmailOTP.DoesNotExist:
                messages.error(request, "Invalid or incorrect OTP.")
                return redirect("accounts:verify_otp")

            # ---------------------------------
            # 10 MINUTE EXPIRY CHECK
            # ---------------------------------
            expiry_time = otp_record.created_at + datetime.timedelta(minutes=10)
            if timezone.now() > expiry_time:
                otp_record.delete()
                messages.error(request, "OTP expired. Please sign up again.")
                return redirect("accounts:signup")

            # Mark OTP as verified
            otp_record.verified = True
            otp_record.save()

            # Activate user & assign invitation code
            user = User.objects.filter(email=email).first()
            if user:
                user.is_active = True
                user.assign_invitation_code()
                user.save()

            messages.success(request, "Account verified successfully. You may now log in.")
            return redirect("accounts:login")

    else:
        form = OTPVerificationForm()

    return render(request, "verify_otp.html", {"form": form, "email": email})
