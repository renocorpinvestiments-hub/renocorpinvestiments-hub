from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages

from .models import User
from .forms import LoginForm, SignupForm


# ---------------------------------------------------
# LOGIN VIEW
# ---------------------------------------------------
def login_view(request):
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
                # ADMIN ACCESS CONTROL
                # -------------------------------
                if user.is_superuser or user.is_staff:
                    return redirect("admin_panel:dashboard")

                return redirect("dashboard:home")

            messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Please check your input fields.")

    return render(request, "login.html", {"form": form})


# ---------------------------------------------------
# SIGNUP VIEW (NO OTP)
# ---------------------------------------------------
def signup_view(request):
    """
    Handles new user signup.
    - Phone number is REQUIRED
    - Invitation code MUST exist
    - User becomes active immediately
    - Auto-login after signup
    """

    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            invited_by = form.cleaned_data.get("invitation_code")
            invited_by = User.objects.filter(invitation_code=invited_by).first()

            if not invited_by:
               messages.error(request, "Invalid invitation code.")
               return render(request, "signup.html", {"form": form})
            # Create user instance (not saved yet)
            user = form.save(commit=False)

            # HARD SAFETY CHECK
            if not user.account_number:
                messages.error(
                    request,
                    "Phone number is required. It is used for withdrawals."
                )
                return render(request, "signup.html", {"form": form})

            user.set_password(form.cleaned_data["password"])
            user.is_active = True
            user.invited_by = invited_by 
            user.subscription_status = "inactive"

            user.save()

            # Assign invitation code AFTER save
            user.assign_invitation_code()
            user.save(update_fields=["invitation_code"])

            # Auto-login user
            login(request, user)

            messages.success(request, "Account created successfully.")
            return redirect("accounts:signup_success")

    else:
        form = SignupForm()

    return render(request, "signup.html", {"form": form})


# ---------------------------------------------------
# SIGNUP SUCCESS PAGE
# ---------------------------------------------------
def signup_success_view(request):
    """
    Simple success page before dashboard redirect.
    """
    return render(request, "signup_success.html")
