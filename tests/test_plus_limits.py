"""Fáza 5 — PLUS benefity: denný AI limit, limit slov na kategóriu, PLUS štatistiky."""

from app.models.user import User
from app.models.word import Word
from app.services.limits import WORD_LIMIT_FREE, AI_DAILY_LIMIT_FREE


def _user_by_email(db_factory, email):
    db = db_factory()
    try:
        return db.query(User).filter(User.email == email).first()
    finally:
        db.close()


def _set_plus(db_factory, email, value=True):
    db = db_factory()
    try:
        u = db.query(User).filter(User.email == email).first()
        u.is_plus = value
        db.commit()
    finally:
        db.close()


def _seed_words(db_factory, user_id, category_id, n):
    db = db_factory()
    try:
        for i in range(n):
            db.add(Word(original_word=f"w{i}", translation=f"t{i}",
                        category_id=category_id, user_id=user_id))
        db.commit()
    finally:
        db.close()


def _create_category(client, name, user_id):
    return client.post(
        "/api/v1/categories", json={"name": name, "description": "", "user_id": user_id}
    ).json()


# ── Limit slov na kategóriu (Free) ──

def test_free_word_limit_blocks_over_limit(client, db_factory):
    client.post("/api/v1/register", json={"email": "wl@example.com", "password": "Abcdef12"})
    user = _user_by_email(db_factory, "wl@example.com")
    cat = _create_category(client, "Cat A", user.id)
    _seed_words(db_factory, user.id, cat["id"], WORD_LIMIT_FREE)  # presne na limite

    res = client.post("/api/v1/words", json={
        "original_word": "extra", "translation": "navyse", "category_id": cat["id"],
    })
    assert res.status_code == 400
    assert str(WORD_LIMIT_FREE) in res.json()["detail"]


def test_plus_word_limit_unlimited(client, db_factory):
    client.post("/api/v1/register", json={"email": "wl2@example.com", "password": "Abcdef12"})
    user = _user_by_email(db_factory, "wl2@example.com")
    cat = _create_category(client, "Cat B", user.id)
    _seed_words(db_factory, user.id, cat["id"], WORD_LIMIT_FREE)
    _set_plus(db_factory, "wl2@example.com", True)

    res = client.post("/api/v1/words", json={
        "original_word": "extra", "translation": "navyse", "category_id": cat["id"],
    })
    assert res.status_code == 200


# ── Denný AI limit (Free) ──

def test_free_ai_daily_limit(client, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    async def _fake_groq(**kwargs):
        return {
            "category_name": "AI Cat",
            "category_description": None,
            "words": [{"original_word": "go", "translation": "ist", "language_from": "en", "language_to": "sk"}],
        }

    monkeypatch.setattr("app.routers.categories.generate_category_and_words_groq", _fake_groq)
    client.post("/api/v1/register", json={"email": "ai@example.com", "password": "Abcdef12"})

    payload = {"prompt": "travel words", "language_from": "en", "language_to": "sk", "count": 5}
    for _ in range(AI_DAILY_LIMIT_FREE):
        assert client.post("/api/v1/categories/ai-create", json=payload).status_code == 200

    # (AI_DAILY_LIMIT_FREE + 1)-té volanie už prekročí denný limit
    blocked = client.post("/api/v1/categories/ai-create", json=payload)
    assert blocked.status_code == 429
    assert str(AI_DAILY_LIMIT_FREE) in blocked.json()["detail"]


def test_plus_ai_no_daily_limit(client, db_factory, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    async def _fake_groq(**kwargs):
        return {"category_name": "AI Cat P", "category_description": None,
                "words": [{"original_word": "go", "translation": "ist", "language_from": "en", "language_to": "sk"}]}

    monkeypatch.setattr("app.routers.categories.generate_category_and_words_groq", _fake_groq)
    client.post("/api/v1/register", json={"email": "aip@example.com", "password": "Abcdef12"})
    _set_plus(db_factory, "aip@example.com", True)

    payload = {"prompt": "travel words", "language_from": "en", "language_to": "sk", "count": 5}
    for _ in range(AI_DAILY_LIMIT_FREE + 2):
        assert client.post("/api/v1/categories/ai-create", json=payload).status_code == 200


# ── PLUS štatistiky ──

def test_stats_include_plus_for_plus_user(client, db_factory):
    client.post("/api/v1/register", json={"email": "st@example.com", "password": "Abcdef12"})
    _set_plus(db_factory, "st@example.com", True)
    data = client.get("/api/user/stats").json()
    assert data["is_plus"] is True
    assert "plus_stats" in data
    assert "weakest_words" in data["plus_stats"]


def test_stats_no_plus_for_free_user(client):
    client.post("/api/v1/register", json={"email": "st2@example.com", "password": "Abcdef12"})
    data = client.get("/api/user/stats").json()
    assert data["is_plus"] is False
    assert "plus_stats" not in data
