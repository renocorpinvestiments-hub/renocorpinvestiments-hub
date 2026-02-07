# core/urls.py
from django.shortcuts import redirect
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
# -------------------------------
# Root redirect ("/" → "/accounts/")
# -------------------------------
def root_redirect(request):
    return redirect("/accounts/")

urlpatterns = [
    # -------------------------------
    # ROOT (must be first)
    # -------------------------------
    path("", root_redirect),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # -------------------------------
    # Django default admin
    # -------------------------------
    path("admin/", admin.site.urls),

    # -------------------------------
    # Main Admin Panel (includes manual login/OTP)
    # -------------------------------
    path(
        "admin-panel/",
        include(("apps.admin_panel.urls", "admin_panel"), namespace="admin_panel"),
    ),

    # -------------------------------
    # User Accounts
    # -------------------------------
    path(
        "accounts/",
        include(("apps.accounts.urls", "accounts"), namespace="accounts"),
    ),

    # -------------------------------
    # Dashboard
    # -------------------------------
    path(
        "dashboard/",
        include(("apps.dashboard.urls", "dashboard"), namespace="dashboard"),
    ),

    # -------------------------------
    # AI Core
    # -------------------------------
    path(
        "ai_core/",
        include(("apps.ai_core.urls", "ai_core"), namespace="ai_core"),
    ),
]
# -------------------------------
# Media files (DEV & some PaaS)
# -------------------------------
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
