# accounts/urls.py
from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # -------------------------------
    # User authentication and signup
    # -------------------------------

    # Login page for normal users
    path("login/", views.login_view, name="login"),

    # User signup page
    path("signup/", views.signup_view, name="signup"),

    # OTP verification page after signup
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),

    # -------------------------------
    # Optional future endpoints
    # -------------------------------
    # Example: resend OTP
    # path("resend-otp/", views.resend_otp_view, name="resend_otp"),
]