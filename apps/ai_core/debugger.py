# apps/ai_core/debugger.py

import traceback
import psutil
import logging
from django.utils import timezone
from celery import shared_task
from ai_app.models import SystemHealthLog, Transaction, Task
from ai_app.notifications import NotificationManager
from ai_app.connector import Connector
from ai_app.transactions import TransactionManager
from ai_app.reward_manager import RewardManager
from ai_app.task_fetcher import TaskFetcher

logger = logging.getLogger(__name__)


class SystemDebugger:
    """
    Central AI Debugging & Auto-Repair Engine for Renocorp.
    Scans for errors, verifies APIs, repairs stuck data,
    and alerts admin when manual review is needed.
    """

    @staticmethod
    def run_full_diagnostic():
        """
        Executes a full diagnostic scan across all Renocorp AI modules.
        """
        results = []
        status = "OK"
        message = "✅ Full system diagnostic completed successfully."

        try:
            results.append(SystemDebugger.check_server_resources())
            results.append(SystemDebugger.check_api_connectivity())
            results.append(SystemDebugger.check_transaction_integrity())
            results.append(SystemDebugger.check_task_fetch_status())
            results.append(SystemDebugger.check_reward_queue())

        except Exception as e:
            status = "ERROR"
            message = f"⚠️ Diagnostic failed: {str(e)}"
            logger.error(traceback.format_exc())

            NotificationManager.create_admin_notification(
                title="System Debugger Critical Failure",
                message=f"{message}\n\nTraceback:\n{traceback.format_exc()}"
            )

        # Log diagnostic summary
        SystemHealthLog.objects.create(
            module_name="Debugger",
            status=status,
            message=message,
            last_checked=timezone.now()
        )

        return results

    # ----------------------------------------------------------
    # 🧩 SUB-MODULE HEALTH CHECKS
    # ----------------------------------------------------------

    @staticmethod
    def check_server_resources():
        """
        Monitor server CPU and Memory load.
        Alerts if usage exceeds 85%.
        """
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        logger.info(f"System load → CPU: {cpu}%, RAM: {memory}%")

        if cpu > 85 or memory > 85:
            NotificationManager.create_admin_notification(
                title="⚠️ High Server Load Detected",
                message=f"CPU usage: {cpu}% | Memory usage: {memory}%"
            )

        return {"cpu_usage": cpu, "memory_usage": memory}

    @staticmethod
    def check_api_connectivity():
        """
        Ping all active providers to confirm connectivity.
        """
        connector = Connector()
        providers = connector.list_providers()
        results = []

        for provider in providers:
            ok = connector.test_connection(provider)
            results.append({provider: "Connected" if ok else "Failed"})

            if not ok:
                logger.warning(f"Connection failed for provider: {provider}")
                NotificationManager.create_admin_notification(
                    title=f"API Connection Failed: {provider}",
                    message="Automatic reconnect attempt in progress."
                )
                connector.reconnect(provider)

        return {"api_connectivity": results}

    @staticmethod
    def check_transaction_integrity():
        """
        Detects transactions that were pending too long and retries them.
        """
        cutoff = timezone.now() - timezone.timedelta(minutes=15)
        stuck = Transaction.objects.filter(status="pending", created_at__lte=cutoff)

        retried = 0
        for tx in stuck:
            try:
                TransactionManager.retry_transaction(tx)
                retried += 1
            except Exception as e:
                logger.error(f"Failed to retry transaction {tx.id}: {e}")

        logger.info(f"Transaction integrity check complete: retried {retried} transactions.")
        return {"retried_transactions": retried}

    @staticmethod
    def check_task_fetch_status():
        """
        Ensures that new tasks were fetched today.
        If not, it triggers TaskFetcher to run immediately.
        """
        today = timezone.now().date()
        count = Task.objects.filter(created_at__date=today).count()

        if count == 0:
            logger.warning("No tasks fetched today! Attempting auto-fetch.")
            NotificationManager.create_admin_notification(
                title="⚠️ No Tasks Fetched Today",
                message="Daily task fetch missing — initiating auto-fetch retry."
            )
            try:
                TaskFetcher.refresh_all_tasks()
            except Exception as e:
                logger.error(f"Auto-fetch retry failed: {e}")

        return {"tasks_fetched_today": count}

    @staticmethod
    def check_reward_queue():
        """
        Confirms no pending reward issues.
        """
        try:
            pending = RewardManager.check_pending_rewards()
            return {"pending_rewards": pending}
        except Exception as e:
            logger.error(f"Reward queue check failed: {e}")
            NotificationManager.create_admin_notification(
                title="Reward Manager Error",
                message=f"Reward processing error detected: {str(e)}"
            )
            return {"pending_rewards": "error"}


# ----------------------------------------------------------
# 🔁 CELERY TASK SCHEDULER
# ----------------------------------------------------------

@shared_task
def run_system_diagnostic_task():
    """
    Scheduled Celery task that runs full diagnostic every 6 hours.
    Add this to CELERY_BEAT_SCHEDULE in settings.py:

    'run_system_diagnostic_every_6h': {
        'task': 'ai_core.debugger.run_system_diagnostic_task',
        'schedule': crontab(hour='*/6'),
    }
    """
    logger.info("Running scheduled system diagnostic...")
    SystemDebugger.run_full_diagnostic()
    logger.info("System diagnostic complete.")
