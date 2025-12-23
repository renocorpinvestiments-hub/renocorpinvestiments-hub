# apps/ai_core/tasks.py

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction

from .utils import PROVIDERS, provider_supports_api

logger = logging.getLogger("ai_core.tasks")


# -----------------------------------------------------
# DAILY OFFER / TASK REFRESH
# -----------------------------------------------------
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=30, retry_kwargs={"max_retries": 3})
def scheduled_daily_task_refresh(self):
    """
    Runs once per day.
    Refreshes API-based offerwalls (AdGem, OfferToro, etc).
    """
    logger.info("Starting daily offer refresh")

    for provider, cfg in PROVIDERS.items():
        if not cfg.get("enabled"):
            continue

        if provider_supports_api(provider):
            fetch_fn = cfg.get("fetch")
            if not fetch_fn:
                continue

            try:
                fetch_fn()  # user_id optional by design
                logger.info("Refreshed provider: %s", provider)
            except Exception as e:
                logger.exception("Provider refresh failed: %s", provider)
                raise

    logger.info("Daily offer refresh completed")
    return {"status": "ok", "run_at": timezone.now().isoformat()}


# -----------------------------------------------------
# WITHDRAWAL / TRANSACTION RECONCILIATION
# -----------------------------------------------------
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=60, retry_kwargs={"max_retries": 5})
def reconcile_pending_transactions(self):
    """
    Runs every 10 minutes.
    Placeholder for:
    - reconciling withdrawals
    - fixing stuck transactions
    """
    logger.info("Reconciling pending transactions")

    # Example placeholder — adjust to your models
    from apps.transactions.models import Transaction

    with transaction.atomic():
        pending = Transaction.objects.select_for_update().filter(status="pending")

        for tx in pending:
            # your reconciliation logic here
            tx.updated_at = timezone.now()
            tx.save(update_fields=["updated_at"])

    logger.info("Reconciliation completed")
    return {"reconciled": pending.count()}