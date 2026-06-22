from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.category import Category
from app.models.user import User
from app.routers.localization import get_language
from app.services.runtime import STATIC_DIR, templates
from app.services.stats_service import get_category_word_summary

router = APIRouter(tags=["pages"])


def _get_session_user(request: Request):
    from app.services.runtime import logger
    user = request.session.get("user")
    logger.info(f"Session keys in dashboard: {list(request.session.keys())}, has_user: {user is not None}")
    return user


def _get_db_user_or_redirect(request: Request, db: Session):
    user_session = _get_session_user(request)
    if not user_session:
        return None, RedirectResponse(url="/login", status_code=303)

    user = db.query(User).filter(User.id == user_session["id"]).first()
    if not user:
        request.session.clear()
        return None, RedirectResponse(url="/login", status_code=303)
    return user, None


def _check_category_access(
    db: Session,
    user_id: int,
    category_id: int,
    is_plus_user: bool,
):
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.user_id == user_id)
        .first()
    )
    if not category:
        return None, RedirectResponse(url="/dashboard", status_code=303)

    if not is_plus_user:
        newest_category = (
            db.query(Category)
            .filter(Category.user_id == user_id)
            .order_by(Category.created_at.desc())
            .first()
        )
        if newest_category and newest_category.id != category_id:
            return None, RedirectResponse(url="/dashboard", status_code=303)

    return category, None


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(f"{STATIC_DIR}/favicon.ico")


@router.get("/apple-touch-icon.png", include_in_schema=False)
async def apple_touch_icon():
    return FileResponse(f"{STATIC_DIR}/apple-touch-icon.png")


@router.get("/manifest.json", include_in_schema=False)
async def get_manifest():
    return FileResponse(
        f"{STATIC_DIR}/manifest.json",
        media_type="application/manifest+json",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.get("/sw.js", include_in_schema=False)
async def get_sw():
    return FileResponse(
        f"{STATIC_DIR}/sw.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "lang": get_language(request)},
    )


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.get("/dashboard")
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    db_user, redirect = _get_db_user_or_redirect(request, db)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "email": db_user.email,
            "is_plus": db_user.is_plus,
            "dark_mode": db_user.dark_mode,
        },
    )


@router.get("/profile")
async def profile_page(request: Request, db: Session = Depends(get_db)):
    db_user, redirect = _get_db_user_or_redirect(request, db)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "email": db_user.email, "user": db_user},
    )


@router.get("/category/{category_id}/words")
async def category_words_page(request: Request, category_id: int, db: Session = Depends(get_db)):
    user_session = _get_session_user(request)
    if not user_session:
        return RedirectResponse(url="/login", status_code=303)

    db_user = db.query(User).filter(User.id == user_session["id"]).first()
    if not db_user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    category, redirect = _check_category_access(db, db_user.id, category_id, db_user.is_plus)
    if redirect:
        return redirect

    summary = get_category_word_summary(db, db_user.id, [category.id])[category.id]
    category_data = {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "level_percentages": summary["level_percentages"],
    }

    return templates.TemplateResponse(
        "category_words.html",
        {
            "request": request,
            "email": user_session.get("email", ""),
            "category": category_data,
            "dark_mode": db_user.dark_mode,
        },
    )


@router.get("/test")
async def test_page(
    request: Request,
    category: int = None,
    level: str = None,
    db: Session = Depends(get_db),
):
    user_session = _get_session_user(request)
    if not user_session:
        return RedirectResponse(url="/login", status_code=303)

    db_user = db.query(User).filter(User.id == user_session["id"]).first()
    if not db_user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    category_data = None
    if category:
        category_data, redirect = _check_category_access(db, db_user.id, category, db_user.is_plus)
        if redirect:
            return redirect

    return templates.TemplateResponse(
        "flashcard_test.html",
        {
            "request": request,
            "email": user_session.get("email", ""),
            "category": category_data,
            "level": level,
        },
    )


@router.get("/repeat")
async def repeat_page(
    request: Request,
    category: int = None,
    level: str = None,
    db: Session = Depends(get_db),
):
    user_session = _get_session_user(request)
    if not user_session:
        return RedirectResponse(url="/login", status_code=303)

    db_user = db.query(User).filter(User.id == user_session["id"]).first()
    if not db_user:
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    category_data = None
    if category:
        category_data, redirect = _check_category_access(db, db_user.id, category, db_user.is_plus)
        if redirect:
            return redirect

    return templates.TemplateResponse(
        "repeat.html",
        {
            "request": request,
            "email": user_session.get("email", ""),
            "category": category_data,
            "level": level,
        },
    )


@router.get("/demo")
async def demo_page(request: Request):
    return templates.TemplateResponse("demo.html", {"request": request})


@router.get("/auth/callback")
async def auth_callback(request: Request):
    return templates.TemplateResponse("auth-callback.html", {"request": request})


@router.get("/forgot-password")
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})


@router.get("/reset-password")
async def reset_password_page(request: Request, token: str):
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})
