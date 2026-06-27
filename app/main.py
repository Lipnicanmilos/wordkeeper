import mimetypes
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from app.database.connection import Base, SessionLocal, engine
from app.models.user import User
from app.models.payment import Payment  # noqa: F401  (registrácia tabuľky pre create_all)
from app.models.inquiry import Inquiry  # noqa: F401  (registrácia tabuľky pre create_all)
from app.routers import words
from app.routers.auth import router as auth_router
from app.routers.categories import router as categories_router
from app.routers.pages import router as pages_router
from app.routers.users import router as users_router
from app.services.auth_service import hash_password, verify_password
from app.services.runtime import STATIC_DIR, SECRET_KEY, is_debug_mode, limiter, logger, templates

@asynccontextmanager
async def lifespan(app: FastAPI):
    # === startup ===
    # Schemu nevytvarame pri kazdom starte (spomaluje cold start a zbytocne
    # kontaktuje Supabase). Spusti sa len ked je explicitne vyziadane cez
    # env premennu RUN_DB_CREATE_ALL=1 (napr. pri prvom deployi/migracii).
    if os.environ.get("RUN_DB_CREATE_ALL") == "1":
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema ensured (RUN_DB_CREATE_ALL=1)")

    logger.info("Application starting up...")

    # Testovaci pouzivatel iba v debug rezime.
    if is_debug_mode():
        db = SessionLocal()
        try:
            test_user = db.query(User).filter(User.email == "test@example.com").first()
            hashed_password = hash_password("test123")

            if not test_user:
                test_user = User(
                    email="test@example.com",
                    name="Test User",
                    is_plus=False,
                    password=hashed_password,
                )
                db.add(test_user)
                logger.info("Test user created with password 'test123'")
            elif not verify_password("test123", test_user.password):
                test_user.password = hashed_password
                logger.info("Test user password updated to bcrypt hash")
            else:
                logger.info("Test user already exists with correct password")

            db.commit()
        except Exception as exc:
            logger.error(f"Error creating/updating test user: {exc}")
        finally:
            db.close()

    yield
    # === shutdown === (nic netreba)


app = FastAPI(lifespan=lifespan)

# Windows nemá woff2/ttf v registri MIME typov — bez tohto sa font servíruje ako text/plain.
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("font/ttf", ".ttf")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Povolene originy pre CORS. V produkcii len vlastna domena/Cloud Run URL;
# localhost sa pridava iba v debug rezime. Volitelna vlastna domena cez env.
ALLOWED_ORIGINS = [
    "https://lexinova-1096007793591.us-central1.run.app",
]
_extra_origin = os.getenv("FRONTEND_ORIGIN")
if _extra_origin:
    ALLOWED_ORIGINS.append(_extra_origin)
if is_debug_mode():
    ALLOWED_ORIGINS += [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

# Bezpecnostne hlavicky na kazdej odpovedi. CSP povoluje 'unsafe-inline'
# pre script/style, lebo sablony pouzivaju inline <style>/<script>.
CSP = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "img-src 'self' data: https:; "
    # inline scripty v šablónach (Chart.js je self-hostovaný)
    "script-src 'self' 'unsafe-inline'; "
    # inline štýly v šablónach (Font Awesome je self-hostovaný)
    "style-src 'self' 'unsafe-inline'; "
    # self-hostovaný Inter + Font Awesome
    "font-src 'self'; "
    "connect-src 'self'; "
    "form-action 'self'"
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Content-Security-Policy", CSP)
    if not is_debug_mode():
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


# POZOR: Starlette spracuva middleware v OPACNOM poradi registracie.
# CORSMiddleware musi byt pridany SKOR (v kode vyssie), aby sa SessionMiddleware
# spracoval ako prvy a session cookie bola spravne nastavena/precitana uz pri
# prvom requeste (inak Google OAuth prihlasi az na druhy pokus).
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    https_only=not is_debug_mode(),
    same_site="lax",
    max_age=2592000,
)

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse(request, "404.html", status_code=404)


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error(f"500 error: {exc}")
    return templates.TemplateResponse(request, "500.html", status_code=500)


app.include_router(pages_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(categories_router)
app.include_router(words.router)

from app.routers.admin import router as admin_router
app.include_router(admin_router)

from app.routers.inquiry import router as inquiry_router
app.include_router(inquiry_router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
