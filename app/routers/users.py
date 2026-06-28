import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from passlib.hash import argon2
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.category import Category
from app.models.inquiry import Inquiry
from app.models.user import User
from app.models.word import Word
from app.routers.auth import password_strength_error
from app.services.auth_service import hash_password, verify_password
from app.services.session_auth import get_authenticated_user
from app.services.stats_service import get_user_level_counts
from app.services.runtime import ADMIN_EMAILS
from app.utils import utcnow

router = APIRouter(tags=["users"])


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


def _verify_current_password(plain: str, hashed: str) -> bool:
    """Overí súčasné heslo (bcrypt; fallback na legacy argon2 ako pri logine)."""
    try:
        return verify_password(plain, hashed)
    except ValueError:
        try:
            return argon2.verify(plain, hashed)
        except Exception:
            return False


def _require_admin(current_user: User):
    # Admin autorizácia cez allow-list emailov z ENV (ADMIN_EMAILS)
    email = (getattr(current_user, "email", "") or "").lower().strip()
    if ADMIN_EMAILS and email in ADMIN_EMAILS:
        return
    raise HTTPException(status_code=403, detail="Admin access denied")


@router.get("/api/user")
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user),
):
    return JSONResponse(
        {
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "picture": request.session.get("user", {}).get("picture", ""),
            "is_plus": current_user.is_plus,
            "dark_mode": current_user.dark_mode,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        }
    )


@router.patch("/api/user/dark-mode")
async def toggle_user_dark_mode(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user),
):
    current_user.dark_mode = not current_user.dark_mode
    db.commit()
    db.refresh(current_user)

    user_session = request.session.get("user", {})
    user_session["dark_mode"] = current_user.dark_mode
    request.session["user"] = user_session

    return JSONResponse(
        {"message": "Dark mode status updated successfully", "dark_mode": current_user.dark_mode}
    )


@router.post("/api/user/change-password")
async def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user),
):
    if not _verify_current_password(data.current_password, current_user.password):
        raise HTTPException(status_code=400, detail="Súčasné heslo je nesprávne.")

    error = password_strength_error(data.new_password)
    if error:
        raise HTTPException(status_code=400, detail=error)

    current_user.password = hash_password(data.new_password)
    db.commit()
    return JSONResponse({"message": "Heslo bolo zmenené."})


@router.delete("/api/user")
async def delete_user(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user),
):
    # GDPR: zmaž aj kontaktné správy (inquiries) viazané na e-mail používateľa.
    # Guard pre prípad, že tabuľka inquiries ešte neexistuje na danom deployi.
    if current_user.email:
        try:
            db.query(Inquiry).filter(Inquiry.email == current_user.email).delete(
                synchronize_session=False
            )
        except (ProgrammingError, OperationalError):
            db.rollback()

    db.delete(current_user)
    db.commit()
    request.session.clear()
    return JSONResponse({"message": "User account and associated data deleted successfully"})


@router.get("/api/user/stats")
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user),
):
    words_count = db.query(func.count(Word.id)).filter(Word.user_id == current_user.id).scalar() or 0
    categories_count = (
        db.query(func.count(Category.id)).filter(Category.user_id == current_user.id).scalar() or 0
    )
    tests_taken = (
        db.query(func.coalesce(func.sum(Word.times_tested), 0))
        .filter(Word.user_id == current_user.id)
        .scalar()
        or 0
    )
    times_correct = (
        db.query(func.coalesce(func.sum(Word.times_correct), 0))
        .filter(Word.user_id == current_user.id)
        .scalar()
        or 0
    )

    success_rate = 0
    if tests_taken > 0:
        success_rate = round((times_correct / tests_taken) * 100, 2)

    return JSONResponse(
        {
            "total_words": words_count,
            "total_categories": categories_count,
            "tests_taken": tests_taken,
            "success_rate": success_rate,
            "words_by_level": get_user_level_counts(db, current_user.id),
        }
    )


@router.get("/api/user/export")
async def export_user_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user),
):
    categories = db.query(Category).filter(Category.user_id == current_user.id).all()
    words = db.query(Word).filter(Word.user_id == current_user.id).all()

    # Kontaktné správy používateľa (guard, ak tabuľka inquiries ešte neexistuje).
    inquiries = []
    if current_user.email:
        try:
            inquiries = db.query(Inquiry).filter(Inquiry.email == current_user.email).all()
        except (ProgrammingError, OperationalError):
            db.rollback()
            inquiries = []

    export_data = {
        "export_info": {
            "exported_at": utcnow().isoformat(),
            "user_id": current_user.id,
            "user_email": current_user.email,
            "user_name": current_user.name,
            "is_plus": current_user.is_plus,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        },
        "categories": [
            {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "created_at": category.created_at.isoformat() if category.created_at else None,
            }
            for category in categories
        ],
        "words": [
            {
                "id": word.id,
                "original_word": word.original_word,
                "translation": word.translation,
                "category_id": word.category_id,
                "knowledge_level": word.knowledge_level.value if word.knowledge_level else None,
                "times_tested": word.times_tested,
                "times_correct": word.times_correct,
                "last_tested": word.last_tested.isoformat() if word.last_tested else None,
                "created_at": word.created_at.isoformat() if word.created_at else None,
            }
            for word in words
        ],
        "inquiries": [
            {
                "id": inq.id,
                "name": inq.name,
                "message": inq.message,
                "page": inq.page,
                "created_at": inq.created_at.isoformat() if inq.created_at else None,
            }
            for inq in inquiries
        ],
    }

    def generate():
        yield json.dumps(export_data, indent=2, ensure_ascii=False)

    filename = (
        f"lexinova_data_{current_user.email}_{utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    )
    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/api/v1/users")
async def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user),
):
    # Iba admin smie vidieť zoznam všetkých používateľov (ochrana osobných údajov).
    _require_admin(current_user)
    users = db.query(User).all()
    return [{"id": user.id, "email": user.email, "name": user.name} for user in users]
