import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.category import Category
from app.models.user import User
from app.models.word import Word
from app.services.session_auth import get_authenticated_user
from app.services.stats_service import get_user_level_counts
from app.services.runtime import ADMIN_EMAILS
from app.utils import utcnow

router = APIRouter(tags=["users"])


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


@router.patch("/api/user/plus")
async def toggle_user_plus(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user),
):
    current_user.is_plus = not current_user.is_plus
    db.commit()
    db.refresh(current_user)

    user_session = request.session.get("user", {})
    user_session["is_plus"] = current_user.is_plus
    request.session["user"] = user_session

    return JSONResponse(
        {"message": "Plus status updated successfully", "is_plus": current_user.is_plus}
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


@router.delete("/api/user")
async def delete_user(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_authenticated_user),
):
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

    export_data = {
        "export_info": {
            "exported_at": utcnow().isoformat(),
            "user_id": current_user.id,
            "user_email": current_user.email,
            "user_name": current_user.name,
            "is_plus": current_user.is_plus,
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
