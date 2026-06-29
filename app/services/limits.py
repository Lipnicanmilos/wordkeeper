"""Limity pre Free vs PLUS účet (Fáza 5 — PLUS benefity).

- Free: max CATEGORY_LIMIT_FREE kategórií, WORD_LIMIT_FREE slov/kategóriu,
  AI_DAILY_LIMIT_FREE AI generovaní za deň (prompt + fotka spolu).
- PLUS: všetko neobmedzene.
"""
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.utils import utcnow


CATEGORY_LIMIT_FREE = 5
WORD_LIMIT_FREE = 30
AI_DAILY_LIMIT_FREE = 3


def word_limit_for(user: User) -> Optional[int]:
    """None = neobmedzene (PLUS)."""
    return None if user.is_plus else WORD_LIMIT_FREE


def consume_ai_quota(db: Session, user: User) -> None:
    """Započíta jedno AI generovanie do denného limitu Free účtu.

    PLUS = neobmedzene (no-op). Pri Free účte resetuje počítadlo pri zmene dňa
    a vyhodí HTTP 429, ak je limit vyčerpaný. Volať PRED samotným AI volaním."""
    if user.is_plus:
        return

    today = utcnow().date()
    if user.ai_uses_date != today:
        user.ai_uses_date = today
        user.ai_uses_count = 0

    if (user.ai_uses_count or 0) >= AI_DAILY_LIMIT_FREE:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Dosiahli ste denný limit {AI_DAILY_LIMIT_FREE} AI generovaní. "
                "Aktivujte PLUS pre neobmedzené generovanie."
            ),
        )

    user.ai_uses_count = (user.ai_uses_count or 0) + 1
    db.commit()
