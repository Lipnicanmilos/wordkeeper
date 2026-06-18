import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.category import Category
from app.models.user import User
from app.models.word import Word
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.ai_category import AICategoryCreateRequest, AICategoryCreateResponse
from app.services.ai_category_service import (
    generate_category_and_words_claude,
    generate_category_and_words_gemini,
    validate_ai_category_payload,
)
from app.services.runtime import logger
from app.services.stats_service import (
    empty_level_counts,
    empty_level_counts_float,
    get_category_word_summary,
)


router = APIRouter(prefix="/api/v1/categories", tags=["categories"])

CATEGORY_LIMIT_FREE = 5
CATEGORY_LIMIT_PLUS = 20


def _get_category_limit(user: User) -> int:
    return CATEGORY_LIMIT_PLUS if user.is_plus else CATEGORY_LIMIT_FREE


def _get_current_user(request: Request, db: Session) -> User:
    user_session = request.session.get("user")
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == user_session["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("", response_model=list[CategoryResponse])
async def get_categories(request: Request, db: Session = Depends(get_db)):
    user = _get_current_user(request, db)
    categories = db.query(Category).filter(Category.user_id == user.id).all()
    summaries = get_category_word_summary(db, user.id, [category.id for category in categories])

    result = []
    for category in categories:
        summary = summaries.get(
            category.id,
            {
                "total_words": 0,
                "level_counts": empty_level_counts(),
                "level_percentages": empty_level_counts_float(),
            },
        )
        result.append(
            CategoryResponse(
                id=category.id,
                name=category.name,
                description=category.description,
                user_id=category.user_id,
                created_at=category.created_at,
                total_words=summary["total_words"],
                level_counts=summary["level_counts"],
                level_percentages=summary["level_percentages"],
            )
        )
    return result


@router.post("", response_model=CategoryResponse)
async def create_category(
    category_data: CategoryCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _get_current_user(request, db)

    category_count = db.query(Category).filter(Category.user_id == user.id).count()
    limit = _get_category_limit(user)
    if category_count >= limit:
        raise HTTPException(status_code=400, detail=f"Maximum limit of {limit} categories reached")

    existing_category = (
        db.query(Category)
        .filter(Category.name == category_data.name, Category.user_id == user.id)
        .first()
    )
    if existing_category:
        raise HTTPException(status_code=400, detail="Category with this name already exists")

    new_category = Category(
        name=category_data.name,
        description=category_data.description,
        user_id=user.id,
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _get_current_user(request, db)
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.user_id == user.id)
        .first()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    for field, value in category_update.dict(exclude_unset=True).items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)

    summary = get_category_word_summary(db, user.id, [category.id])[category.id]
    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        created_at=category.created_at,
        user_id=category.user_id,
        total_words=summary["total_words"],
        level_counts=summary["level_counts"],
        level_percentages=summary["level_percentages"],
    )


@router.delete("/{category_id}")
async def delete_category(category_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_current_user(request, db)

    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.user_id == user.id)
        .first()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    db.delete(category)
    db.commit()
    return {"message": "Category deleted successfully"}


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category_detail(category_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_current_user(request, db)
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.user_id == user.id)
        .first()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    summary = get_category_word_summary(db, user.id, [category.id])[category.id]
    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        user_id=category.user_id,
        created_at=category.created_at,
        total_words=summary["total_words"],
        level_counts=summary["level_counts"],
        level_percentages=summary["level_percentages"],
    )


@router.post("/ai-create", response_model=AICategoryCreateResponse)
async def ai_create_category_and_words(
    ai_data: AICategoryCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _get_current_user(request, db)

    # Skontroluj limit PRED volanim AI (setri API credits)
    category_count = db.query(Category).filter(Category.user_id == user.id).count()
    limit = _get_category_limit(user)
    if category_count >= limit:
        raise HTTPException(status_code=400, detail=f"Maximum limit of {limit} categories reached")

    if ai_data.ai_provider == "claude":
        claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        claude_model = os.getenv("CLAUDE_MODEL", "claude-opus-4-8")
        if not claude_api_key:
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
        generated = await generate_category_and_words_claude(
            api_key=claude_api_key,
            model=claude_model,
            prompt=ai_data.prompt,
            language_from=ai_data.language_from,
            language_to=ai_data.language_to,
            count=ai_data.count,
        )
    else:
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        if not gemini_api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
        generated = await generate_category_and_words_gemini(
            api_key=gemini_api_key,
            model=gemini_model,
            prompt=ai_data.prompt,
            language_from=ai_data.language_from,
            language_to=ai_data.language_to,
            count=ai_data.count,
        )

    try:
        validate_ai_category_payload(generated)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"AI payload validation failed: {exc}")

    category_name = generated.get("category_name")
    if not category_name:
        raise HTTPException(status_code=400, detail="AI did not return category_name")

    category_description = generated.get("category_description")

    existing_category = (
        db.query(Category)
        .filter(Category.name == category_name, Category.user_id == user.id)
        .first()
    )
    if existing_category:
        category = existing_category
    else:
        # Limit sa skontroloval uz pred AI volanim, priamo vytvorime
        category = Category(name=category_name, description=category_description, user_id=user.id)
        db.add(category)
        db.commit()
        db.refresh(category)

    words = generated.get("words") or []
    if not isinstance(words, list):
        raise HTTPException(status_code=400, detail="AI payload words must be a list")

    inserted = 0
    updated = 0
    skipped = 0
    saved_words_preview: list[dict] = []

    for w in words:
        try:
            original_word = str(w.get("original_word", "")).strip()
            translation = str(w.get("translation", "")).strip()
            language_from = str(w.get("language_from", ai_data.language_from)).strip()
            language_to = str(w.get("language_to", ai_data.language_to)).strip()
        except Exception:
            skipped += 1
            continue

        if not original_word or not translation:
            skipped += 1
            continue

        existing_word = (
            db.query(Word)
            .filter(
                Word.category_id == category.id,
                Word.original_word == original_word,
                Word.user_id == user.id,
            )
            .first()
        )

        if existing_word:
            if existing_word.translation != translation:
                existing_word.translation = translation
                existing_word.language_from = language_from
                existing_word.language_to = language_to
                updated += 1
            else:
                skipped += 1
            continue

        new_word = Word(
            original_word=original_word,
            translation=translation,
            category_id=category.id,
            user_id=user.id,
            language_from=language_from,
            language_to=language_to,
        )
        db.add(new_word)
        inserted += 1

        saved_words_preview.append(
            {
                "original_word": original_word,
                "translation": translation,
                "language_from": language_from,
                "language_to": language_to,
            }
        )

    db.commit()

    return AICategoryCreateResponse(
        category_id=category.id,
        category_name=category.name,
        category_description=category.description,
        inserted_words=inserted,
        skipped_words=skipped + updated,
        words=[
            {
                "original_word": sw["original_word"],
                "translation": sw["translation"],
                "language_from": sw["language_from"],
                "language_to": sw["language_to"],
            }
            for sw in saved_words_preview
        ],
    )


@router.get("/{category_id}/stats")
async def get_category_stats(category_id: int, request: Request, db: Session = Depends(get_db)):
    user = _get_current_user(request, db)

    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.user_id == user.id)
        .first()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    summary = get_category_word_summary(db, user.id, [category_id])[category_id]
    total_words = summary["total_words"]
    level_counts = summary["level_counts"]

    stats = {
        "total_words": total_words,
        "dont_know_percentage": round((level_counts.get("dont_know", 0) / total_words * 100), 1)
        if total_words > 0
        else 0,
        "learning_percentage": round((level_counts.get("learning", 0) / total_words * 100), 1)
        if total_words > 0
        else 0,
        "know_percentage": round((level_counts.get("know", 0) / total_words * 100), 1)
        if total_words > 0
        else 0,
    }
    return JSONResponse(stats)
