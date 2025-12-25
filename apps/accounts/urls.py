from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.login_view, name="login_root"),  # ← this handles /accounts/
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
]
