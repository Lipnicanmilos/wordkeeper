from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.word import Word
from app.models.category import Category
from app.schemas.user import UserUpdate
from app.services.session_auth import get_authenticated_user
from app.services.runtime import ADMIN_EMAILS

router = APIRouter(tags=["admin"])



def _require_admin(current_user: User):
    # Admin autorizácia cez allow-list emailov z ENV
    # ADMIN_EMAILS=mail1@gmail.com,mail2@gmail.com
    if not getattr(current_user, "email", None):
        raise HTTPException(status_code=403, detail="Admin access denied")

    email = current_user.email.lower().strip()
    if ADMIN_EMAILS and email in ADMIN_EMAILS:
        return

    # Ak ADMIN_EMAILS nie je nastavené, admin nikto nemá.
    raise HTTPException(status_code=403, detail="Admin access denied")



@router.get("/admin")
async def admin_page(
    request: Request,
    current_user: User = Depends(get_authenticated_user),
):
    _require_admin(current_user)
    # Render HTML admin template
    from app.services.runtime import templates

    return templates.TemplateResponse("admin.html", {"request": request, "email": current_user.email})



@router.get("/api/admin/users")
async def admin_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user),
):
    _require_admin(current_user)


    # words_count + categories_count + last_login
    # Použi poddotazy aby sa neprepočítavali counts kvôli násobeniu joinov
    categories_subq = (
        db.query(
            Category.user_id.label("user_id"),
            func.count(Category.id).label("categories_count"),
        )
        .group_by(Category.user_id)
        .subquery()
    )

    words_subq = (
        db.query(
            Word.user_id.label("user_id"),
            func.count(Word.id).label("words_count"),
        )
        .group_by(Word.user_id)
        .subquery()
    )

    users = (
        db.query(
            User.id,
            User.email,
            User.is_plus,
            User.last_login,
            func.coalesce(categories_subq.c.categories_count, 0).label("categories_count"),
            func.coalesce(words_subq.c.words_count, 0).label("words_count"),
        )
        .outerjoin(categories_subq, categories_subq.c.user_id == User.id)
        .outerjoin(words_subq, words_subq.c.user_id == User.id)
        .order_by(User.id)
        .all()
    )

    total_words_all_users = db.query(func.coalesce(func.sum(Word.id), 0)).scalar() or 0

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


@router.patch("/api/admin/users/{user_id}")
async def admin_update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user),
):
    _require_admin(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.email is not None:
        # Overiť unikátnosť emailu
        existing = db.query(User).filter(User.email == payload.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = payload.email

    if payload.is_plus is not None:
        user.is_plus = bool(payload.is_plus)

    db.commit()
    db.refresh(user)

    return JSONResponse(
        {
            "id": user.id,
            "email": user.email,
            "is_plus": bool(user.is_plus),
        }
    )


