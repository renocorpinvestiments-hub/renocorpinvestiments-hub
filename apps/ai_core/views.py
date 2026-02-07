# apps/ai_core/views.py
"""
views.py — AI Core (FINAL, CANONICAL, PRODUCTION-READY)
"""

# =========================
# Standard Library
# =========================
import json
import logging

# =========================
# Django
# =========================
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.conf import settings

# =========================
# Local
# =========================
from .models import (
    Task,
    RewardLog,
    WebhookLog,
    IdempotencyKey,
)
from .utils import (
    PROVIDERS,
    get_iframe_url,
    provider_enabled,
    normalize_postback,
    normalize_usd_to_ugx,
    verify_hmac,
    verify_md5,
    verify_ip,
)

User = get_user_model()
logger = logging.getLogger("ai_core.views")
CACHE_TIMEOUT = 60 * 5


# =====================================================
# API TASK LIST (READ-ONLY)
# =====================================================
@require_http_methods(["GET"])
def api_task_list_view(request):
    provider = request.GET.get("provider")
    cache_key = f"api_tasks:{provider or 'all'}"

    cached = cache.get(cache_key)
    if cached:
        return JsonResponse({"tasks": cached})

    qs = Task.objects.filter(is_active=True, source="api")
    if provider:
        qs = qs.filter(provider_name=provider)

    tasks = list(
        qs.values(
            "id",
            "provider_name",
            "provider_task_id",
            "title",
            "reward_ugx",
            "category",
        )
    )

    cache.set(cache_key, tasks, CACHE_TIMEOUT)
    return JsonResponse({"tasks": tasks})


# =====================================================
# IFRAME OFFERWALLS
# =====================================================
@require_http_methods(["GET"])
def iframe_offerwalls_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    data = {}

    for provider, cfg in PROVIDERS.items():
        if cfg["mode"] != "iframe" or not provider_enabled(provider):
            continue

        try:
            url = get_iframe_url(provider, str(request.user.id))
            if url:
                data[provider] = url
        except Exception:
            logger.exception("Failed to build iframe URL", extra={"provider": provider})

    return JsonResponse({"offerwalls": data})


# =====================================================
# REFRESH API TASKS (ADMIN / CRON)
# =====================================================
@require_http_methods(["POST"])
def refresh_api_tasks_view(request):
    created = 0

    for provider, cfg in PROVIDERS.items():
        if cfg["mode"] != "api" or not provider_enabled(provider):
            continue

        fetcher = cfg.get("fetch")
        if not fetcher:
            continue

        try:
            result = fetcher(None)
        except Exception:
            logger.exception("Provider fetch failed", extra={"provider": provider})
            continue

        for offer in result.get("offers", []):
            _, was_created = Task.objects.update_or_create(
                provider_name=provider,
                provider_task_id=str(offer.get("id")),
                defaults={
                    "title": offer.get("title", "Unnamed Offer"),
                    "reward_ugx": normalize_usd_to_ugx(offer.get("payout")),
                    "category": offer.get("category", "general"),
                    "is_active": True,
                    "source": "api",
                },
            )
            if was_created:
                created += 1

    cache.clear()
    return JsonResponse({"status": "ok", "new_tasks": created})


# =====================================================
# PROVIDER WEBHOOK (SECURE, IDEMPOTENT)
# =====================================================
@csrf_exempt
@require_http_methods(["POST"])
def provider_webhook_view(request, provider: str):
    if not provider_enabled(provider):
        logger.warning("Postback for disabled provider", extra={"provider": provider})
        return HttpResponse(status=404)

    cfg = PROVIDERS.get(provider)
    if not cfg:
        return HttpResponse(status=404)

    try:
        payload = json.loads(request.body.decode())
    except json.JSONDecodeError:
        logger.warning("Invalid JSON postback", extra={"provider": provider})
        return HttpResponse(status=400)

    raw_body = request.body.decode()

    # -----------------------------
    # SECURITY VERIFICATION
    # -----------------------------
    postback_cfg = cfg.get("postback", {})
    method = postback_cfg.get("method")

    if method == "hmac":
        sig = request.headers.get("X-Signature")
        if not sig or not verify_hmac(raw_body, postback_cfg["secret"], sig):
            return HttpResponse(status=403)

    elif method == "md5":
        if not verify_md5(
            payload.get("user_id"),
            payload.get("transaction_id"),
            payload.get("reward"),
            postback_cfg["secret"],
            payload.get("signature"),
        ):
            return HttpResponse(status=403)

    elif method == "ip":
        allowed_ips = getattr(settings, f"{provider.upper()}_POSTBACK_IPS", [])
        if not verify_ip(request.META.get("REMOTE_ADDR"), allowed_ips):
            return HttpResponse(status=403)

    # -----------------------------
    # NORMALIZATION
    # -----------------------------
    data = normalize_postback(provider, payload)

    user_id = data.get("user_id")
    tx_id = data.get("transaction_id")
    reward = data.get("reward_ugx", 0)

    if not user_id or not tx_id or reward <= 0:
        return HttpResponse(status=400)

    user = get_object_or_404(User.objects.select_related("profile"), pk=user_id)

    task = Task.objects.filter(
        provider_name=provider,
        provider_task_id=data.get("offer_id"),
    ).first()

    category_code = task.category if task else "other"

    # 🔐 Authoritative reward source
    admin_cap = task.admin_reward_ugx if task else reward
    final_reward = min(reward, admin_cap)

    # -----------------------------
    # ATOMIC + IDEMPOTENT
    # -----------------------------
    try:
        with transaction.atomic():
            IdempotencyKey.objects.create(
                provider=provider,
                unique_hash=tx_id,
                user=user,
            )

            user.profile.balance += final_reward
            user.profile.save(update_fields=["balance"])

            RewardLog.objects.create(
                user=user,
                task=task,
                provider=provider,
                final_reward_ugx=final_reward,
                raw_payload=data["raw"],
                category=category_code,
            )

            WebhookLog.objects.create(
                provider=provider,
                user=user,
                tx_id=tx_id,
                reward_ugx=final_reward,
                status="success",
                raw_payload=data["raw"],
            )

    except IntegrityError:
        return JsonResponse({"status": "duplicate"})

    return JsonResponse({"status": "ok", "reward_ugx": final_reward})
