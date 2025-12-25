# ai_core/urls.py
from django.urls import path
from . import views

app_name = "ai_core"

urlpatterns = [
    # -------------------------------
    # Task endpoints
    # -------------------------------
    path("tasks/", views.api_task_list_view, name="task_list"),
    path("refresh-tasks/", views.refresh_tasks_view, name="refresh_tasks"),

    # -------------------------------
    # Provider webhook endpoints
    # -------------------------------
    path("webhook/offertoro/", views.offertoro_webhook, name="offertoro_webhook"),
    path("webhook/adgem/", views.adgem_webhook, name="adgem_webhook"),
    path("webhook/adgate/", views.adgate_webhook, name="adgate_webhook"),
    path("webhook/wannads/", views.wannads_webhook, name="wannads_webhook"),
    path("webhook/extra/", views.extra_webhook, name="extra_webhook"),
]
