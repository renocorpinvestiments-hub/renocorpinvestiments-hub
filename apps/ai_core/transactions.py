# apps/ai_core/transactions.py
import json
import uuid
import time
import logging
from decimal import Decimal, ROUND_DOWN
from functools import lru_cache
from typing import Optional, Dict, Any, Tuple

import requests
from django.conf import settings
from django.utils import timezone
from django.db import transaction as db_transaction
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from celery import shared_task

from .models import Transaction, APIConfig
from .utils import get_logger, decrypt_value
from .notifications import notify_system_event, notify_user

# -------------------------
# Constants
# -------------------------
DEFAULT_HTTP_TIMEOUT = 20
HTTP_RETRY_ATTEMPTS = 4
HTTP_RETRY_BACKOFF = 2
CURRENCY = "UGX"
User = get_user_model()
logger = get_logger("renocorp.transactions") or logging.getLogger("renocorp.transactions")


# -------------------------
# Helper Functions
# -------------------------
def _mask_sensitive(s: str, keep: int = 6) -> str:
    if not s:
        return ""
    return f"{s[:keep]}...****" if len(s) > keep else "*" * len(s)


def _safe_notify_system_event(code: str, message: str, level: str = "info") -> None:
    try:
        notify_system_event(code, message, level)
    except Exception:
        logger.exception("notify_system_event failed for %s: %s", code, message)


def _safe_notify_user(user, title: str, message: str, level: str = "info") -> None:
    try:
        if user:
            notify_user(user, title, message, level)
    except Exception:
        logger.exception("notify_user failed for user %s: %s", getattr(user, "id", "<unknown>"), message)


def _parse_json_response(response: Optional[requests.Response]) -> Dict[str, Any]:
    result: Dict[str, Any] = {"status_code": None, "raw_text": None, "json": {}}
    try:
        if response is None:
            return result
        result["status_code"] = getattr(response, "status_code", None)
        try:
            resp_json = response.json()
            result["json"] = resp_json if isinstance(resp_json, dict) else {"data": resp_json}
        except ValueError:
            result["raw_text"] = getattr(response, "text", "")
            result["json"] = {}
    except Exception:
        logger.exception("Unexpected error while parsing HTTP response")
    return result


def _http_request(method: str, url: str, headers: Dict[str, str], json_payload: Optional[Dict[str, Any]] = None,
                  timeout: int = DEFAULT_HTTP_TIMEOUT) -> Tuple[Optional[requests.Response], Dict[str, Any]]:
    attempt = 0
    last_exc = None
    while attempt < HTTP_RETRY_ATTEMPTS:
        try:
            resp = requests.request(method, url, headers=headers, json=json_payload, timeout=timeout)
            parsed = _parse_json_response(resp)
            return resp, parsed.get("json") or {}
        except requests.RequestException as exc:
            last_exc = exc
            wait = HTTP_RETRY_BACKOFF ** attempt
            logger.warning("HTTP %s failed for %s (attempt %s/%s), retrying in %s sec. Error: %s",
                           method, url, attempt + 1, HTTP_RETRY_ATTEMPTS, wait, str(exc))
            time.sleep(wait)
            attempt += 1
        except Exception as exc:
            last_exc = exc
            logger.exception("Unexpected HTTP %s error for %s", method, url)
            time.sleep(HTTP_RETRY_BACKOFF)
            attempt += 1
    logger.error("HTTP %s exhausted retries for %s: %s", method, url, str(last_exc))
    return None, {}


def _http_post(url: str, headers: Dict[str, str], json_payload: Dict[str, Any], timeout: int = DEFAULT_HTTP_TIMEOUT):
    return _http_request("POST", url, headers, json_payload, timeout)


def _http_get(url: str, headers: Dict[str, str], timeout: int = DEFAULT_HTTP_TIMEOUT):
    return _http_request("GET", url, headers, None, timeout)


# -------------------------
# Flutterwave Config
# -------------------------
@lru_cache(maxsize=2)
def _get_flutterwave_config_cached() -> Optional[Dict[str, str]]:
    return _get_flutterwave_config()


def _get_flutterwave_config() -> Optional[Dict[str, str]]:
    try:
        config = APIConfig.objects.get(name__iexact="flutterwave")
        base_url = (getattr(config, "base_url", "") or "").rstrip("/")
        secret_key = decrypt_value(getattr(config, "secret_key", None)) if getattr(config, "secret_key", None) else None
        public_key = decrypt_value(getattr(config, "public_key", None)) if getattr(config, "public_key", None) else None
        webhook_secret = decrypt_value(getattr(config, "webhook_secret", None)) if getattr(config, "webhook_secret", None) else None

        if not base_url or not secret_key:
            logger.error("Flutterwave configuration missing base_url or secret_key")
            _safe_notify_system_event("FLW_CONFIG_ERROR", "Missing Flutterwave API credentials", "error")
            return None

        return {"base_url": base_url, "secret_key": secret_key, "public_key": public_key, "webhook_secret": webhook_secret}

    except APIConfig.DoesNotExist:
        logger.error("Flutterwave configuration not found in DB.")
        _safe_notify_system_event("FLW_CONFIG_ERROR", "Missing Flutterwave API credentials", "error")
        return None
    except Exception as exc:
        logger.exception("Error retrieving Flutterwave APIConfig: %s", str(exc))
        _safe_notify_system_event("FLW_CONFIG_ERROR", str(exc), "error")
        return None


def _get_headers(secret_key: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {secret_key}", "Content-Type": "application/json"}


def _generate_reference(prefix: str = "RENOWD") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _notify_failure(tx: Optional[Transaction], message: str, event_code: str):
    try:
        if tx:
            with db_transaction.atomic():
                tx.status = "failed"
                tx.failure_reason = str(message)[:1000]
                tx.save(update_fields=["status", "failure_reason"])
    except Exception:
        logger.exception("Failed to mark transaction %s failed", getattr(tx, "id", "<unknown>"))
    _safe_notify_system_event(event_code, message, "error")


# -------------------------
# Wallet / Balance Helpers
# -------------------------
@lru_cache(maxsize=2)
def _get_wallet_model_cached() -> Tuple[Optional[type], Optional[str]]:
    try:
        from apps.wallets.models import Wallet
        return Wallet, "balance_ugx"
    except Exception:
        try:
            from apps.dashboard.models import UserProfile
            return UserProfile, "balance_ugx"
        except Exception:
            logger.warning("No wallet model found (apps.wallets or apps.dashboard).")
            return None, None


def _to_minor_units(amount: Any) -> int:
    try:
        dec = Decimal(str(amount)).quantize(Decimal("1"), rounding=ROUND_DOWN)
        minor = int(dec)
        if minor < 0:
            raise ValueError("amount_must_be_positive")
        return minor
    except Exception:
        raise ValueError("invalid_amount")


def _deduct_user_balance_atomic(user, amount: Any) -> None:
    Model, field = _get_wallet_model_cached()
    if not Model:
        raise Exception("no_wallet_model_found")

    amount_int = _to_minor_units(amount)
    with db_transaction.atomic():
        obj = Model.objects.select_for_update().filter(user=user).first()
        if not obj:
            raise Exception("wallet_not_found")
        current = getattr(obj, field, None)
        if current is None:
            raise Exception("wallet_balance_field_missing")
        current_int = int(current)
        if current_int < amount_int:
            raise ValueError("insufficient_balance")
        setattr(obj, field, current_int - amount_int)
        obj.save(update_fields=[field])


# -------------------------
# Celery Helpers
# -------------------------
def celery_enabled() -> bool:
    always_eager = bool(getattr(settings, "CELERY_ALWAYS_EAGER", False))
    broker = getattr(settings, "CELERY_BROKER_URL", None) or getattr(settings, "CELERY_BROKER", None)
    return (not always_eager) and bool(broker)


# -------------------------
# Celery Tasks
# -------------------------
@shared_task(bind=True, max_retries=4, default_retry_delay=10)
def celery_process_withdrawal(self, tx_id: int, account_bank: str, account_number: str, amount: Any):
    from .transactions import confirm_withdrawal_status_task
    try:
        tx = Transaction.objects.select_related("user").get(pk=tx_id)
    except Transaction.DoesNotExist:
        logger.error("celery_process_withdrawal: transaction %s not found", tx_id)
        return {"status": "failed", "message": "tx_not_found"}

    config = _get_flutterwave_config_cached()
    if not config or not config.get("secret_key"):
        _notify_failure(tx, "Missing flutterwave config", "WITHDRAWAL_CONFIG_MISSING")
        return {"status": "failed", "message": "missing_config"}

    reference = tx.tx_ref or _generate_reference()
    payload = {
        "account_bank": account_bank,
        "account_number": account_number,
        "amount": str(_to_minor_units(amount)),
        "currency": CURRENCY,
        "narration": f"Renocorp Withdrawal {getattr(tx.user, 'username', 'user')}",
        "reference": reference,
    }
    url = f"{config['base_url']}/transfers"

    response, data = _http_post(url, headers=_get_headers(config["secret_key"]), json_payload=payload, timeout=30)
    status_code = getattr(response, "status_code", None) if response else None
    success = (status_code in (200, 201)) and isinstance(data, dict) and data.get("status") == "success"

    if success:
        provider_data = data.get("data") or {}
        provider_ref = provider_data.get("id") or provider_data.get("reference") or payload["reference"]
        try:
            with db_transaction.atomic():
                tx = Transaction.objects.select_for_update().get(pk=tx_id)
                tx.provider_reference = provider_ref
                tx.raw_provider_response = json.dumps(provider_data or data, default=str)[:20000]
                tx.status = "processing"
                tx.sent_at = timezone.now()
                if not getattr(tx, "tx_ref", None):
                    tx.tx_ref = reference
                tx.save(update_fields=["provider_reference", "raw_provider_response", "status", "sent_at", "tx_ref"])
        except Exception:
            logger.exception("Failed updating tx after provider accepted transfer for tx %s", tx_id)
            _notify_failure(tx, "DB update error after transfer initiation", "WITHDRAWAL_DB_ERROR")
            return {"status": "failed", "message": "db_error"}

        _safe_notify_user(tx.user, "Withdrawal Processing", f"Your withdrawal of UGX {amount} is being processed.", "info")
        _safe_notify_system_event("WITHDRAWAL_INITIATED",
                                  f"Withdrawal started for {getattr(tx.user, 'username', tx.user_id)}", "info")

        try:
            confirm_withdrawal_status_task.apply_async(
                (provider_ref,),
                countdown=getattr(settings, "WITHDRAWAL_STATUS_POLL_DELAY", 30)
            )
        except Exception:
            logger.exception("Failed to schedule confirm_withdrawal_status_task for provider_ref %s", provider_ref)

        return {"status": "processing", "provider_ref": provider_ref}
    else:
        msg = (data.get("message") or data.get("error") or "Withdraw initiation failed") if isinstance(data, dict) else "Withdraw initiation failed"
        _notify_failure(tx, msg, "WITHDRAWAL_FAIL")
        return {"status": "failed", "message": msg}


@shared_task(bind=True, max_retries=4, default_retry_delay=15)
def confirm_withdrawal_status_task(self, reference: str):
    from .transactions import confirm_withdrawal_status
    result = confirm_withdrawal_status(reference)
    if result and result.get("status") == "processing":
        raise self.retry(countdown=getattr(settings, "WITHDRAWAL_STATUS_POLL_DELAY", 60))
    return result


# -------------------------
# Core Functions
# -------------------------
def initiate_subscription(user, package_id, amount):
    try:
        _deduct_user_balance_atomic(user, amount)
        tx = Transaction.objects.create(
            user=user,
            tx_type="subscription",
            amount=amount,
            status="processing",
            tx_ref=_generate_reference("SUB")
        )
        _safe_notify_user(user, "Subscription Initiated", f"Subscription payment of UGX {amount} started.", "info")
        _safe_notify_system_event("SUB_INIT", f"User {user.id} started subscription {tx.id}", "info")
        return tx
    except Exception as exc:
        logger.exception("initiate_subscription failed for user %s", getattr(user, "id", "<unknown>"))
        _safe_notify_user(user, "Subscription Failed", str(exc), "error")
        return None


def verify_transaction(tx_ref: str):
    try:
        tx = Transaction.objects.select_related("user").get(tx_ref=tx_ref)
    except Transaction.DoesNotExist:
        return {"status": "failed", "message": "Transaction not found"}

    config = _get_flutterwave_config_cached()
    if not config:
        return {"status": "failed", "message": "Missing Flutterwave config"}

    url = f"{config['base_url']}/transactions/{tx_ref}/verify"
    response, data = _http_get(url, headers=_get_headers(config["secret_key"]))

    if response and response.status_code == 200 and data.get("status") == "success":
        tx.status = "success"
        tx.save(update_fields=["status"])
        _safe_notify_user(tx.user, "Transaction Successful", f"Payment of UGX {tx.amount} verified.", "info")
        return {"status": "success"}
    else:
        tx.status = "failed"
        tx.save(update_fields=["status"])
        _safe_notify_user(tx.user, "Transaction Failed", f"Payment verification failed.", "error")
        return {"status": "failed", "data": data}


def initiate_withdrawal(user, amount, account_bank, account_number):
    try:
        _deduct_user_balance_atomic(user, amount)
        tx = Transaction.objects.create(
            user=user,
            tx_type="withdrawal",
            amount=amount,
            status="pending",
            tx_ref=_generate_reference("WD")
        )
        celery_process_withdrawal.apply_async((tx.id, account_bank, account_number, amount))
        return tx
    except Exception as exc:
        logger.exception("initiate_withdrawal failed for user %s", getattr(user, "id", "<unknown>"))
        _safe_notify_user(user, "Withdrawal Failed", str(exc), "error")
        return None


def confirm_withdrawal_status(reference: str):
    try:
        config = _get_flutterwave_config_cached()
        if not config:
            return {"status": "failed", "message": "Missing config"}

        url = f"{config['base_url']}/transfers/{reference}"
        response, data = _http_get(url, headers=_get_headers(config["secret_key"]))

        tx = Transaction.objects.select_related("user").filter(provider_reference=reference).first()
        if not tx:
            return {"status": "failed", "message": "Transaction not found"}

        status = (data.get("data") or {}).get("status") or data.get("status")
        if status == "SUCCESSFUL":
            tx.status = "success"
            tx.save(update_fields=["status"])
            _safe_notify_user(tx.user, "Withdrawal Successful", f"Your withdrawal of UGX {tx.amount} succeeded.", "info")
            return {"status": "success"}
        elif status in ["FAILED", "DECLINED"]:
            tx.status = "failed"
            tx.save(update_fields=["status"])
            _safe_notify_user(tx.user, "Withdrawal Failed", f"Your withdrawal of UGX {tx.amount} failed.", "error")
            return {"status": "failed"}
        else:
            return {"status": "processing"}
    except Exception as exc:
        logger.exception("confirm_withdrawal_status failed for reference %s", reference)
        return {"status": "failed", "message": str(exc)}


# -------------------------
# Webhook Handler
# -------------------------
@csrf_exempt
def handle_flutterwave_webhook(request):
    if request.method != "POST":
        return JsonResponse({"status": "failed", "message": "Invalid method"}, status=405)

    try:
        payload = json.loads(request.body)
        tx_ref = payload.get("tx_ref")
        signature = request.headers.get("verif-hash")

        config = _get_flutterwave_config_cached()
        if not config or not config.get("webhook_secret"):
            return JsonResponse({"status": "failed", "message": "Config missing"}, status=500)

        import hmac, hashlib
        expected_sig = hmac.new(config["webhook_secret"].encode(), request.body, hashlib.sha256).hexdigest()
        if signature != expected_sig:
            logger.warning("Invalid webhook signature for tx_ref %s", tx_ref)
            return JsonResponse({"status": "failed", "message": "Invalid signature"}, status=403)

        tx = Transaction.objects.select_related("user").filter(tx_ref=tx_ref).first()
        if not tx:
            return JsonResponse({"status": "failed", "message": "Transaction not found"}, status=404)

        status = payload.get("status")
        if status == "successful":
            tx.status = "success"
            tx.save(update_fields=["status"])
            _safe_notify_user(tx.user, "Payment Successful", f"Payment UGX {tx.amount} completed.", "info")
        elif status in ["failed", "declined"]:
            tx.status = "failed"
            tx.save(update_fields=["status"])
            _safe_notify_user(tx.user, "Payment Failed", f"Payment UGX {tx.amount} failed.", "error")
        else:
            tx.status = "processing"
            tx.save(update_fields=["status"])
            _safe_notify_user(tx.user, "Payment Processing", f"Payment UGX {tx.amount} is processing.", "info")

        return JsonResponse({"status": "ok"})
    except Exception as exc:
        logger.exception 
# -------------------------
# Payroll: Automatic Sunday Payout
# -------------------------
from django.db.models import Q
from .models import PayrollEntry

@shared_task
def run_sunday_payroll():
    """
    Pay all enabled payroll users every Sunday at 00:00
    """
    admin_user = User.objects.filter(is_superuser=True).first()  # notify first admin
    today = timezone.now().date()

    # Fetch entries enabled for auto pay and not already paid today
    payroll_entries = PayrollEntry.objects.filter(
        enabled=True,
        auto_withdraw=True
    ).exclude(last_paid_at=today)

    for entry in payroll_entries:
        try:
            # Create Transaction for payroll
            tx = Transaction.objects.create(
                user=None,
                tx_type="payroll",
                amount=Decimal(entry.amount),
                status="pending",
                tx_ref=_generate_reference("PAY")
            )

            # Initiate withdrawal via existing celery_process_withdrawal
            celery_process_withdrawal.apply_async(
                (tx.id, entry.bank_code or "000", entry.account_number, entry.amount)
            )

            # Update last_paid_at to prevent double payout
            entry.last_paid_at = today
            entry.save(update_fields=["last_paid_at"])

            _safe_notify_system_event(
                "PAYROLL_INITIATED",
                f"Payroll for {entry.name} ({_mask_sensitive(entry.account_number)}) initiated.",
                level="info"
            )

        except Exception as exc:
            _safe_notify_system_event(
                "PAYROLL_FAILED",
                f"Failed to initiate payroll for {entry.name} ({_mask_sensitive(entry.account_number)}): {exc}",
                level="error"
            )
            if admin_user:
                _safe_notify_user(admin_user, "Payroll Failure",
                                  f"Failed to pay {entry.name}: {exc}", level="error")        
