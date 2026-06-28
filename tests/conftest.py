"""Pytest fixtures — izolovaná SQLite DB, vypnutý rate limiting, žiadne reálne e-maily.

Spustenie:  python -m pytest        (z root adresára projektu)
"""
import os

# Test prostredie nastav PRED importom aplikácie.
os.environ["DEBUG"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.pop("ERROR_ALERT_EMAIL", None)  # žiadne e-mail alerty počas testov
for _k in (
    "PADDLE_API_KEY",
    "PADDLE_CLIENT_TOKEN",
    "PADDLE_WEBHOOK_SECRET",
    "PADDLE_PRICE_MONTHLY",
    "PADDLE_PRICE_ANNUAL",
    "PADDLE_ENV",
    "PADDLE_API_BASE",
):
    # Prázdny reťazec (nie pop) — load_dotenv pri importe appky neprepíše existujúci
    # kľúč, takže platby ostanú v testoch deterministicky nenakonfigurované.
    os.environ[_k] = ""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

# Import aplikácie zaregistruje všetky modely na Base.
import app.main as main_module
from app.database.connection import Base, get_db
from app.services.runtime import limiter

# In-memory SQLite zdieľaná naprieč vláknami (TestClient beží vo vlákne).
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=test_engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _no_real_emails(monkeypatch):
    """Nahraď odosielanie e-mailov no-op (neposielame reálne e-maily v testoch)."""
    monkeypatch.setattr("app.routers.auth.send_welcome_email", lambda *a, **k: None)
    monkeypatch.setattr("app.routers.inquiry.send_inquiry_notification", lambda *a, **k: None)


@pytest.fixture
def client():
    """Štandardný client — rate limiting vypnutý."""
    main_module.app.dependency_overrides[get_db] = _override_get_db
    limiter.enabled = False
    # Bez `with` => nespúšťa sa lifespan (žiadne volania na Supabase).
    test_client = TestClient(main_module.app)
    yield test_client
    main_module.app.dependency_overrides.clear()


@pytest.fixture
def rate_limited_client():
    """Client s aktívnym rate limitingom — pre overenie 429."""
    main_module.app.dependency_overrides[get_db] = _override_get_db
    limiter.enabled = True
    test_client = TestClient(main_module.app)
    yield test_client
    limiter.enabled = False
    main_module.app.dependency_overrides.clear()
