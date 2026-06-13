from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from app.database.connection import Base, SessionLocal, engine
from app.models.user import User
from app.routers import words
from app.routers.auth import router as auth_router
from app.routers.categories import router as categories_router
from app.routers.pages import router as pages_router
from app.routers.users import router as users_router
from app.services.auth_service import hash_password, verify_password
from app.services.runtime import STATIC_DIR, SECRET_KEY, is_debug_mode, limiter, logger

app = FastAPI()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    https_only=not is_debug_mode(),
    same_site="lax",
    max_age=2592000,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "https://wordkeeper-1096007793591.us-central1.run.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pages_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(categories_router)
app.include_router(words.router)

from app.routers.admin import router as admin_router
app.include_router(admin_router)


@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)
    logger.info("Application starting up...")

    if not is_debug_mode():
        return

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


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
