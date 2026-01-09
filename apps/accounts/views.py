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

def logout_view(request):
    """
    Logs out the user and redirects to login page.
    """
    logout(request)
    return redirect("login")
# ---------------------------------------------------
# ---------------------------------------------------
# SIGNUP VIEW (NO OTP)
# ---------------------------------------------------
def signup_view(request):
    """
    Handles new user signup.
    - Phone number is REQUIRED
    - invited_by code MUST exist
    - User becomes active immediately
    - Auto-login after signup
    """

    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            # Get the invited_by code from form
            invited_by_code = form.cleaned_data.get("invited_by")
            invited_by_user = User.objects.filter(invitation_code=invited_by_code).first()

            if not invited_by_user:
                messages.error(request, "Invalid invitation code.")
                return render(request, "signup.html", {"form": form})

            # Create user instance (not saved yet)
            user = form.save(commit=False)

            # HARD SAFETY CHECK: phone number required
            if not user.account_number:
                messages.error(
                    request,
                    "Phone number is required. It is used for withdrawals."
                )
                return render(request, "signup.html", {"form": form})

            # Set password & activate account
            user.set_password(form.cleaned_data["password"])
            user.is_active = True
            user.subscription_status = "inactive"
            user.invited_by = invited_by_user  # assign the inviter

            # Save the user (signal will assign invitation code automatically)
            user.save()

            # Auto-login user
            login(request, user)

            messages.success(request, "Account created successfully.")
            return redirect("accounts:success")

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
    return render(request, "success.html")
