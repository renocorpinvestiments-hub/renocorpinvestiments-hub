from django.urls import path
from . import views

app_name = "admin_panel"

urlpatterns = [
    path("", views.admin_dashboard, name="dashboard"),

    path("manual-login/", views.manual_login_view, name="manual_login"),
    path("verify-admin-password/", views.verify_admin_password, name="verify_admin_password"),
    path("graphs/", views.graphs_view, name="graphs"),
    path("transactions/", views.transaction_page, name="transactions"),

    path("settings/", views.admin_settings_view, name="settings"),
    path("gift-upload/", views.gift_upload_view, name="gift_upload"),

    path("logout/", views.admin_logout, name="logout"),
    path("update-user/<int:user_id>/", views.update_user, name="update_user"),
    path("delete-all-pending-users/", views.delete_all_pending_users, name="delete_all_pending_users"),

    path("user-created/", views.user_created_success, name="user_created_success")
]
