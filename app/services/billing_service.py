"""Paddle (Merchant of Record) — checkout config, subscription, webhook verifikácia.

Konfigurácia cez env premenné (môžu chýbať — appka funguje, platby sú len neaktívne):
  PADDLE_API_KEY            – server API kľúč (pdl_live_... / pdl_sdbx_...)
  PADDLE_CLIENT_TOKEN       – client-side token pre Paddle.js (live_... / test_...)
  PADDLE_WEBHOOK_SECRET     – tajný kľúč na overenie webhookov
  PADDLE_PRICE_MONTHLY      – price id mesačného plánu (pri_...)
  PADDLE_PRICE_ANNUAL       – price id ročného plánu (pri_...)
  PADDLE_ENV               – 'sandbox' (default) alebo 'production'
  PADDLE_API_BASE          – voliteľný override base URL
"""
import hashlib
import hmac
import os
from datetime import datetime
from typing import Optional

import httpx

from app.utils import utcnow

# Paddle statusy, pri ktorých má používateľ ešte PLUS prístup.
# (zrušené predplatné má status 'active'/'trialing' až do konca obdobia, potom 'canceled')
ACTIVE_STATUSES = {"trialing", "active", "past_due"}


def environment() -> str:
    return "production" if os.getenv("PADDLE_ENV") == "production" else "sandbox"


def api_base() -> str:
    override = os.getenv("PADDLE_API_BASE")
    if override:
        return override.rstrip("/")
    return (
        "https://api.paddle.com"
        if environment() == "production"
        else "https://sandbox-api.paddle.com"
    )


def is_configured() -> bool:
    """Server-side platby (webhook/portal) sú nakonfigurované."""
    return bool(os.getenv("PADDLE_API_KEY"))


def is_client_configured() -> bool:
    """Client-side checkout (Paddle.js overlay) je nakonfigurovaný."""
    return bool(os.getenv("PADDLE_CLIENT_TOKEN") and os.getenv("PADDLE_PRICE_MONTHLY"))


def client_config() -> dict:
    """Konfigurácia pre Paddle.js na frontende (token je client-side, nie tajný)."""
    return {
        "configured": is_client_configured(),
        "environment": environment(),
        "token": os.getenv("PADDLE_CLIENT_TOKEN", ""),
        "prices": {
            "monthly": os.getenv("PADDLE_PRICE_MONTHLY"),
            "annual": os.getenv("PADDLE_PRICE_ANNUAL"),
        },
    }


def _auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {os.getenv('PADDLE_API_KEY', '')}",
        "Content-Type": "application/json",
    }


def plan_for_price(price_id) -> Optional[str]:
    pid = str(price_id) if price_id else ""
    if pid and pid == os.getenv("PADDLE_PRICE_MONTHLY"):
        return "monthly"
    if pid and pid == os.getenv("PADDLE_PRICE_ANNUAL"):
        return "annual"
    return None


def _first_price_id(data: dict) -> Optional[str]:
    for item in data.get("items") or []:
        price = item.get("price") or {}
        if price.get("id"):
            return price["id"]
    return None


async def create_portal_session(customer_id: str, subscription_id: Optional[str] = None) -> str:
    """Vytvorí Paddle customer portal session a vráti URL na správu predplatného."""
    body: dict = {}
    if subscription_id:
        body["subscription_ids"] = [str(subscription_id)]
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{api_base()}/customers/{customer_id}/portal-sessions",
            json=body,
            headers=_auth_headers(),
        )
        resp.raise_for_status()
        urls = resp.json()["data"]["urls"]
        return urls["general"]["overview"]


def verify_webhook_signature(payload: bytes, sig_header: str) -> bool:
    """Overí Paddle-Signature hlavičku 'ts=..;h1=..' (HMAC-SHA256 z 'ts:body')."""
    secret = os.getenv("PADDLE_WEBHOOK_SECRET", "")
    if not secret or not sig_header:
        return False
    parts = dict(p.split("=", 1) for p in sig_header.split(";") if "=" in p)
    ts, h1 = parts.get("ts"), parts.get("h1")
    if not ts or not h1:
        return False
    signed = f"{ts}:".encode() + payload
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, h1)


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        # Paddle dáva ISO 8601 (napr. 2026-07-28T10:00:00Z) — držíme ako naive UTC
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, AttributeError):
        return None


def apply_subscription(user, data: dict) -> None:
    """Premietne stav Paddle subscription (z webhooku) do používateľa."""
    status = data.get("status")
    user.plus_status = status

    if data.get("id"):
        user.paddle_subscription_id = str(data["id"])
    if data.get("customer_id"):
        user.paddle_customer_id = str(data["customer_id"])

    plan = plan_for_price(_first_price_id(data))
    if plan:
        user.plus_plan = plan

    # Expirácia: naplánované zrušenie → effective_at, inak koniec aktuálneho obdobia
    scheduled = data.get("scheduled_change") or {}
    period = data.get("current_billing_period") or {}
    if scheduled.get("action") == "cancel":
        user.plus_expires_at = _parse_dt(scheduled.get("effective_at"))
        if not user.plus_cancelled_at:
            user.plus_cancelled_at = utcnow()
    else:
        user.plus_expires_at = _parse_dt(period.get("ends_at") or data.get("next_billed_at"))
        if status in ("active", "trialing"):
            user.plus_cancelled_at = None

    not_expired = user.plus_expires_at is None or user.plus_expires_at > utcnow()
    user.is_plus = status in ACTIVE_STATUSES and not_expired


def expire_if_needed(user) -> bool:
    """Ak PLUS expiroval (napr. zmeškaný webhook), vypni ho. Vráti True ak sa zmenilo."""
    if user.is_plus and user.plus_expires_at and user.plus_expires_at < utcnow():
        user.is_plus = False
        user.plus_status = "expired"
        return True
    return False
