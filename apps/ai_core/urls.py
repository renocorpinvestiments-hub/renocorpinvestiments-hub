# apps/ai_core/urls.py
from django.urls import path
from . import views

app_name = "ai_core"

urlpatterns = [
    # -------------------------------
    # Task endpoints
    # -------------------------------
    path("tasks/", views.api_task_list_view, name="task_list"),
    path("refresh-tasks/", views.refresh_api_tasks_view, name="refresh_tasks"),

    # -------------------------------
    # Provider webhook (single secure endpoint)
    # -------------------------------
    path("webhook/<str:provider>/", views.provider_webhook_view, name="provider_webhook"),
]
