from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views.decorators.cache import never_cache
from .forms import LoginForm
from .models import User
from .forms import LoginForm, SignupForm


# ---------------------------------------------------
# LOGIN VIEW
# ---------------------------------------------------
@never_cache
def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)

        if form.is_valid():
            user = form.get_user()   # uses our FastAuthBackend

            if user:
                login(request, user)

                if user.is_staff or user.is_superuser:
                    return redirect("admin_panel:dashboard")

                return redirect("dashboard:home")

        messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})

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

            invited_by_code = form.cleaned_data.get("invited_by")
            invited_by_user = User.objects.filter(invitation_code=invited_by_code).first()

            if not invited_by_user:
                messages.error(request, "Invalid invitation code.")
                return redirect("accounts:signup")

            # Create user instance (not saved yet)
            user = form.save(commit=False)

            # HARD SAFETY CHECK
            if not user.account_number:
                messages.error(
                    request,
                    "Phone number is required. It is used for withdrawals."
                )
                return redirect("accounts:signup")

            # Set password & activate account
            user.set_password(form.cleaned_data["password"])
            user.is_active = True
            user.subscription_status = "inactive"
            user.invited_by = invited_by_user
            # generate invitation code BEFORE saving
            user.assign_invitation_code()

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
