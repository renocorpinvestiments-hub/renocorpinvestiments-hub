"""
utils.py — AI Core / Offerwall Utilities (FINAL, CANONICAL)
========================================================
Single source of truth for:
- Provider registry
- Secure HTTP client
- Provider-specific iframe builders
- Provider-specific API fetchers
- Webhook security verification
- Postback normalization

Designed for Django + Celery at scale.
"""

# =========================
# Standard Library
# =========================
import hmac
import hashlib
import logging
from decimal import Decimal, ROUND_DOWN, InvalidOperation
from typing import Dict, Any, Optional
from ipaddress import ip_address, ip_network

# =========================
# Third‑Party
# =========================
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =========================
# Django
# =========================
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("ai_core.utils")

# =====================================================
# CONSTANTS
# =====================================================

HTTP_TIMEOUT = 10

# =====================================================
# HTTP SESSION (SAFE, SHARED)
# =====================================================

def get_http_session() -> requests.Session:
    session = requests.Session()

    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update({
        "User-Agent": "AI-Core/1.0",
        "Accept": "application/json",
    })

    return session

# =====================================================
# CURRENCY NORMALIZATION (USD → UGX INTEGER)
# =====================================================

def normalize_usd_to_ugx(value: Any) -> int:
    try:
        usd = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        return int(usd * Decimal(settings.USD_TO_UGX_RATE))
    except (InvalidOperation, TypeError):
        logger.warning("Invalid USD amount: %s", value)
        return 0

# =====================================================
# SECURITY HELPERS
# =====================================================

def verify_hmac(payload: str, secret: str, signature: str) -> bool:
    computed = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


def verify_md5(user_id: str, transaction_id: str, reward: str, secret: str, signature: str) -> bool:
    raw = f"{user_id}{transaction_id}{reward}{secret}".encode()
    expected = hashlib.md5(raw).hexdigest()
    return expected == signature


def verify_ip(request_ip: str, allowed_ranges: list[str]) -> bool:
    try:
        ip = ip_address(request_ip)
        return any(ip in ip_network(net) for net in allowed_ranges)
    except ValueError:
        logger.warning("Invalid IP received: %s", request_ip)
        return False

# =====================================================
# PROVIDER‑SPECIFIC IFRAME BUILDERS
# (URLs pulled from settings for safety)
# =====================================================

def iframe_cpalead(uid: str) -> str:
    return f"{settings.CPALEAD_IFRAME_BASE_URL}?id={settings.CPALEAD_PUBLISHER_ID}&s1={uid}"


def iframe_adgate(uid: str) -> str:
    return f"{settings.ADGATE_IFRAME_BASE_URL}/{settings.ADGATE_WALL_CODE}/{uid}"


def iframe_wannads(uid: str) -> str:
    return (
        f"{settings.WANNADS_IFRAME_BASE_URL}?"
        f"apiKey={settings.WANNADS_API_KEY}&userId={uid}"
    )


def iframe_adscend(uid: str) -> str:
    return (
        f"{settings.ADSCEND_IFRAME_BASE_URL}/publisher/{settings.ADSCEND_PUBLISHER_ID}"
        f"/profile/{settings.ADSCEND_WALL_ID}?subid1={uid}"
    )

# =====================================================
# PROVIDER‑SPECIFIC API FETCHERS (CELERY ONLY)
# =====================================================

def fetch_adgem(user_id: Optional[str] = None) -> dict:
    session = get_http_session()
    headers = {"Authorization": f"Bearer {settings.ADGEM_API_TOKEN}"}
    params = {"user_id": user_id} if user_id else {}

    try:
        r = session.get(
            settings.ADGEM_API_BASE_URL,
            headers=headers,
            params=params,
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        logger.error("AdGem fetch failed", exc_info=e)
        raise


def fetch_offertoro(user_id: str) -> dict:
    session = get_http_session()
    params = {
        "api_key": settings.OFFERTORO_API_KEY,
        "uid": user_id,
    }

    try:
        r = session.get(
            settings.OFFERTORO_API_BASE_URL,
            params=params,
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        logger.error("OfferToro fetch failed", exc_info=e)
        raise

# =====================================================
# PROVIDER REGISTRY (SINGLE SOURCE OF TRUTH)
# =====================================================

PROVIDERS: Dict[str, Dict[str, Any]] = {
    "cpalead": {
        "enabled": True,
        "mode": "iframe",
        "iframe": iframe_cpalead,
        "postback": {"method": "ip"},
    },
    "adgate": {
        "enabled": True,
        "mode": "iframe",
        "iframe": iframe_adgate,
        "postback": {"method": "ip"},
    },
    "wannads": {
        "enabled": True,
        "mode": "iframe",
        "iframe": iframe_wannads,
        "postback": {
            "method": "md5",
            "secret": settings.WANNADS_API_SECRET,
        },
    },
    "adscend": {
        "enabled": True,
        "mode": "iframe",
        "iframe": iframe_adscend,
        "postback": {"method": "none"},
    },
    "adgem": {
        "enabled": True,
        "mode": "api",
        "fetch": fetch_adgem,
        "postback": {
            "method": "hmac",
            "secret": settings.ADGEM_POSTBACK_KEY,
        },
    },
    "offertoro": {
        "enabled": True,
        "mode": "api",
        "fetch": fetch_offertoro,
        "postback": {"method": "ip"},
    },
}

# =====================================================
# PUBLIC HELPERS (USED BY VIEWS / CELERY)
# =====================================================

def provider_enabled(provider: str) -> bool:
    cfg = PROVIDERS.get(provider)
    if not cfg:
        return False
    return cfg.get("enabled", True)


def get_iframe_url(provider: str, user_uid: str) -> Optional[str]:
    cfg = PROVIDERS.get(provider)
    if not cfg or cfg["mode"] != "iframe" or not cfg.get("enabled", True):
        return None
    return cfg["iframe"](user_uid)


def provider_supports_api(provider: str) -> bool:
    return provider in PROVIDERS and PROVIDERS[provider]["mode"] == "api"

# =====================================================
# POSTBACK NORMALIZATION (PROVIDER‑AGNOSTIC)
# =====================================================

def normalize_postback(provider: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    amount = payload.get("amount") or payload.get("reward")

    return {
        "provider": provider,
        "user_id": payload.get("user_id") or payload.get("uid") or payload.get("subid1"),
        "offer_id": payload.get("offer_id") or payload.get("oid"),
        "transaction_id": (
            payload.get("transaction_id")
            or payload.get("tid")
            or payload.get("conversion_id")
        ),
        "reward_usd": amount,
        "reward_ugx": normalize_usd_to_ugx(amount),
        "currency": payload.get("currency", "USD"),
        "status": payload.get("status", "completed"),
        "raw": payload,
        "received_at": timezone.now(),
    }
