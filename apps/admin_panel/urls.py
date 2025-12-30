# apps/admin_panel/urls.py

from django.urls import path
from . import views

app_name = "admin_panel"

urlpatterns = [
    # Unified login for both users and admins
    path("login/", views.unified_login, name="login"),
    path("logout/", views.admin_logout, name="logout"),

    # Dashboard
    path("", views.users, name="users"),

    # Manual user & OTP
    path("manual-login/", views.manual_login_view, name="manual_login"),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),

    # System / Transaction Logs
    path("transactions/", views.transaction_page, name="transaction_page"),

    # Gift Offers
    path("gifts/", views.gift_offer_list, name="gift_offer_list"),
    path("gifts/add/", views.gift_offer_create, name="gift_offer_create"),
    path("gifts/edit/<int:pk>/", views.gift_offer_edit, name="gift_offer_edit"),
    path("gifts/delete/<int:pk>/", views.gift_offer_delete, name="gift_offer_delete"),
    path("gifts/upload/", views.gift_upload_view, name="gift_upload"),

    # Task Control
    path("task-control/", views.task_control_view, name="task_control"),

    # Payroll
    path("payroll/", views.payroll_list, name="payroll_list"),
    path("payroll/add/", views.payroll_add, name="payroll_add"),
    path("payroll/edit/<int:pk>/", views.payroll_edit, name="payroll_edit"),
    path("payroll/delete/<int:pk>/", views.payroll_delete, name="payroll_delete"),

    # Admin Settings
    path("settings/", views.admin_settings_view, name="settings"),

    # Analytics / Graphs
    path("graphs/", views.graphs_view, name="graphs"),
]
