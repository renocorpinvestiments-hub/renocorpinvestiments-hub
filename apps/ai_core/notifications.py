# apps/ai_core/notifications.py
import logging
from django.utils import timezone
from apps.admin_panel.models import Notification, AdminNotification  # hypothetical models

logger = logging.getLogger(__name__)

# -----------------------------
# User notifications
# -----------------------------
def notify_user(user, title: str, message: str, category: str = "general"):
    """
    Sends a notification to a user.
    """
    try:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            category=category,
            created_at=timezone.now()
        )
    except Exception as e:
        logger.error(f"Failed to create user notification for {user.username}: {e}")


# -----------------------------
# Admin / system notifications
# -----------------------------
def notify_admin(title: str, message: str, category: str = "system"):
    """
    Logs an admin/system notification to the database.
    """
    try:
        AdminNotification.objects.create(
            title=title,
            message=message,
            category=category,
            created_at=timezone.now()
        )
        logger.info(f"Admin notification logged: {title}")
    except Exception as e:
        logger.error(f"Failed to log admin notification: {e}")
