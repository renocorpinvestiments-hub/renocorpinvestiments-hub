from django.shortcuts import redirect
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# -------------------------------
# Root redirect ("/" → "/account/")
# -------------------------------
def root_redirect(request):
    return redirect("/account/")

# Optional import for AI app views
try:
    from apps.ai_app import views as ai_views
except ImportError:
    ai_views = None

urlpatterns = [
    # -------------------------------
    # ROOT (IMPORTANT: must be first)
    # -------------------------------
    path("", root_redirect),

    # -------------------------------
    # Django default admin
    # -------------------------------
    path("admin/", admin.site.urls),

    # -------------------------------
    # Main Admin Panel
    # -------------------------------
    path(
        "admin-panel/",
        include(("apps.admin_panel.urls", "admin_panel"), namespace="admin_panel"),
    ),

    # -------------------------------
    # Manual Admin Panel (OTP)
    # -------------------------------
    path(
        "admin/manual/",
        include(
            ("apps.admin_panel.manual_urls", "admin_panel_manual"),
            namespace="admin_panel_manual",
        ),
    ),

    # -------------------------------
    # User Accounts
    # -------------------------------
    path(
        "accounts/",
        include(("accounts.urls", "accounts"), namespace="accounts"),
    ),

    # -------------------------------
    # Dashboard
    # -------------------------------
    path(
        "dashboard/",
        include(("apps.dashboard.urls", "dashboard"), namespace="dashboard"),
    ),

    # -------------------------------
    # AI Apps
    # -------------------------------
    path(
        "ai_core/",
        include(("ai_core.urls", "ai_core"), namespace="ai_core"),
    ),
    path(
        "ai/",
        include(("apps.ai_app.urls", "ai_app"), namespace="ai_app"),
    ),
]

# -------------------------------
# Optional direct route to AI graphs
# -------------------------------
if ai_views and hasattr(ai_views, "graphs_view"):
    urlpatterns.append(
        path("graphs/", ai_views.graphs_view, name="graphs")
    )

# -------------------------------
# Media files (DEV & some PaaS)
# -------------------------------
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )