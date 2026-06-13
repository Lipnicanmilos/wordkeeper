from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.word import Word
from app.models.category import Category
from app.services.session_auth import get_authenticated_user

router = APIRouter(tags=["admin"])


def _require_admin(current_user: User):
    # V tomto projekte nemáš rolu admina — preto používame jednoduchú podmienku:
    # ak user je_plus, ber ho ako admin pre debug/prehlad.
    # Ak chceš striktný admin, pridáme field (napr. is_admin) do User modelu.
    if not getattr(current_user, "is_plus", False):
        raise HTTPException(status_code=403, detail="Admin access denied")


@router.get("/admin")
async def admin_page(request: Request):
    # Template sa renderuje v pages.py; tu len API.
    return JSONResponse({"message": "Admin page"})


@router.get("/api/admin/users")
async def admin_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user),
):
    _require_admin(current_user)

    # words_count + categories_count + last_login
    users = db.query(
        User.id,
        User.email,
        User.is_plus,
        User.last_login,
        func.count(Category.id).label("categories_count"),
        func.count(Word.id).label("words_count"),
    ).outerjoin(Category, Category.user_id == User.id) \
     .outerjoin(Word, Word.user_id == User.id) \
     .group_by(User.id, User.email, User.is_plus, User.last_login) \
     .all()

    total_words_all_users = (
        db.query(func.coalesce(func.sum(Word.id), 0)).scalar() or 0
    )

    return JSONResponse(
        {
            "total_users": len(users),
            "total_words_all_users": total_words_all_users,
            "users": [
                {
                    "id": u.id,
                    "email": u.email,
                    "is_plus": bool(u.is_plus),
                    "last_login": u.last_login.isoformat() if u.last_login else None,
                    "categories_count": int(u.categories_count or 0),
                    "words_count": int(u.words_count or 0),
                }
                for u in users
            ],
        }
    )

