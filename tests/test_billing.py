"""Platby (Paddle) — config, stav predplatného, webhook."""
import hashlib
import hmac
import json


def _paddle_headers(payload: bytes, secret: str, ts: str = "1700000000") -> dict:
    signed = f"{ts}:".encode() + payload
    h1 = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return {"Paddle-Signature": f"ts={ts};h1={h1}"}


def test_config_requires_auth(client):
    r = client.get("/api/v1/billing/config")
    assert r.status_code in (401, 403)


def test_config_not_configured(client):
    client.post("/api/v1/register", json={"email": "cfg@example.com", "password": "Abcdef12"})
    data = client.get("/api/v1/billing/config").json()
    assert data["configured"] is False


def test_subscription_status_default(client):
    client.post("/api/v1/register", json={"email": "sub@example.com", "password": "Abcdef12"})
    data = client.get("/api/v1/subscription").json()
    assert data["is_plus"] is False
    assert data["status"] is None


def test_cancel_requires_auth(client):
    r = client.post("/api/v1/billing/cancel")
    assert r.status_code in (401, 403)


def test_cancel_without_subscription_returns_404(client):
    client.post("/api/v1/register", json={"email": "can@example.com", "password": "Abcdef12"})
    r = client.post("/api/v1/billing/cancel")
    assert r.status_code == 404


def test_webhook_rejects_invalid_signature(client):
    r = client.post("/api/webhooks/paddle", content=b"{}", headers={"Paddle-Signature": "ts=1;h1=bad"})
    assert r.status_code == 401


def test_webhook_activates_plus(client, monkeypatch):
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "testsecret")
    reg = client.post("/api/v1/register", json={"email": "wh@example.com", "password": "Abcdef12"})
    uid = reg.json()["user"]["id"]

    body = {
        "event_type": "subscription.activated",
        "data": {
            "id": "sub_123",
            "status": "active",
            "customer_id": "ctm_99",
            "custom_data": {"user_id": str(uid)},
            "current_billing_period": {"ends_at": "2099-01-01T00:00:00Z"},
            "items": [{"price": {"id": "pri_month"}}],
        },
    }
    raw = json.dumps(body).encode()
    r = client.post("/api/webhooks/paddle", content=raw, headers=_paddle_headers(raw, "testsecret"))
    assert r.status_code == 200

    data = client.get("/api/v1/subscription").json()
    assert data["is_plus"] is True
    assert data["status"] == "active"
    assert data["expires_at"] is not None


def test_webhook_canceled_deactivates_plus(client, monkeypatch):
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "testsecret")
    reg = client.post("/api/v1/register", json={"email": "exp@example.com", "password": "Abcdef12"})
    uid = reg.json()["user"]["id"]

    body = {
        "event_type": "subscription.canceled",
        "data": {
            "id": "sub_999",
            "status": "canceled",
            "custom_data": {"user_id": str(uid)},
            "current_billing_period": {"ends_at": "2020-01-01T00:00:00Z"},
        },
    }
    raw = json.dumps(body).encode()
    r = client.post("/api/webhooks/paddle", content=raw, headers=_paddle_headers(raw, "testsecret"))
    assert r.status_code == 200
    assert client.get("/api/v1/subscription").json()["is_plus"] is False
