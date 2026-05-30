from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

# Importy z vašich modulov
from app.database.connection import get_db, SessionLocal, engine, Base
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.models.category import Category
from app.models.user import User
from app.models.word import Word
from app.routers import words  # Import words routeru
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

# STARÉ - odstrán toto:
#load_dotenv()

# NOVÉ - Cloud Run načíta secrets automaticky ako env variables
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

app = FastAPI()

# Pripojenie statických súborov (pre CSS, JS, obrázky, favicon)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Endpoint pre favicon.ico
@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse("app/static/favicon.ico")

# Pridajte words router do aplikácie - IBA RAZ
app.include_router(words.router)

# ✅ FIX 1: Session middleware MUSÍ byť pridaný PRED CORSMiddleware
# (Starlette spracováva middleware v opačnom poradí ako sú pridané)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "your-secret-key-12345"),
    https_only=True,    # ✅ FIX 2: Potrebné pre Cloud Run (HTTPS)
    same_site="lax",    # ✅ FIX 3: Potrebné pre Google OAuth redirect
    max_age=3600,       # ✅ FIX 4: Session vydrží 1 hodinu
)

# ✅ FIX 5: CORS middleware s produkčnou URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "https://wordkeeper-1096007793591.us-central1.run.app",  # ✅ Produkčná URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth configuration
config = Config('.env')
oauth = OAuth(config)

oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    access_token_url='https://oauth2.googleapis.com/token',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Auth service imports
from app.services.auth_service import hash_password, verify_password, create_access_token
from passlib.hash import argon2

# Email imports
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from datetime import datetime, timedelta
import secrets

mail_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

# ============================================================
# PAGE ROUTES
# ============================================================

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard")
async def dashboard_page(request: Request):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login', status_code=303)
    return templates.TemplateResponse("dashboard.html", {"request": request, "email": user.get('email', '')})

@app.get("/profile")
async def profile_page(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get('user')
    if not user_session:
        return RedirectResponse(url='/login', status_code=303)

    # ✅ FIX 6: Vždy načítavaj user dáta z DB, nie len zo session
    user = db.query(User).filter(User.id == user_session['id']).first()
    if not user:
        request.session.clear()
        return RedirectResponse(url='/login', status_code=303)

    context = {"request": request, "email": user.email, "user": user}
    return templates.TemplateResponse("profile.html", context)

@app.get("/category/{category_id}/words")
async def category_words_page(request: Request, category_id: int, db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login', status_code=303)

    user_id = user['id']

    # ✅ FIX 7: is_plus vždy čítaj z DB, nie zo session (session môže byť stará)
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        request.session.clear()
        return RedirectResponse(url='/login', status_code=303)
    is_plus_user = db_user.is_plus

    # Get category details
    category = db.query(Category).filter(Category.id == category_id, Category.user_id == user_id).first()
    if not category:
        return RedirectResponse(url='/dashboard', status_code=303)

    # Security check: Non-plus users can only access their newest category.
    if not is_plus_user:
        newest_category = db.query(Category)\
            .filter(Category.user_id == user_id)\
            .order_by(Category.created_at.desc())\
            .first()
        if newest_category and newest_category.id != category_id:
            return RedirectResponse(url='/dashboard', status_code=303)

    # Calculate level percentages for the category
    from app.models.word import KnowledgeLevel
    total_words = db.query(func.count(Word.id)).filter(Word.category_id == category.id, Word.user_id == user_id).scalar() or 0

    level_counts = {}
    for level in KnowledgeLevel:
        count = db.query(func.count(Word.id)).filter(
            Word.category_id == category.id,
            Word.knowledge_level == level.value,
            Word.user_id == user_id
        ).scalar() or 0
        level_counts[level.value] = count

    level_percentages = {}
    if total_words > 0:
        for level, count in level_counts.items():
            level_percentages[level] = round((count / total_words) * 100, 1)
    else:
        for level in KnowledgeLevel:
            level_percentages[level.value] = 0.0

    category_data = {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "level_percentages": level_percentages
    }

    return templates.TemplateResponse("category_words.html", {
        "request": request,
        "email": user.get('email', ''),
        "category": category_data,
        "dark_mode": db_user.dark_mode  # ✅ FIX 8: dark_mode vždy z DB
    })

@app.get("/test")
async def test_page(request: Request, category: int = None, level: str = None, db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login', status_code=303)

    user_id = user['id']

    # ✅ is_plus z DB
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        request.session.clear()
        return RedirectResponse(url='/login', status_code=303)
    is_plus_user = db_user.is_plus

    category_data = None
    if category:
        category_data = db.query(Category).filter(Category.id == category, Category.user_id == user_id).first()
        if not category_data:
            return RedirectResponse(url='/dashboard', status_code=303)

        if not is_plus_user:
            newest_category = db.query(Category)\
                .filter(Category.user_id == user_id)\
                .order_by(Category.created_at.desc())\
                .first()
            if newest_category and newest_category.id != category:
                return RedirectResponse(url='/dashboard', status_code=303)

    return templates.TemplateResponse("flashcard_test.html", {
        "request": request,
        "email": user.get('email', ''),
        "category": category_data,
        "level": level
    })

@app.get("/repeat")
async def repeat_page(request: Request, category: int = None, level: str = None, db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login', status_code=303)

    user_id = user['id']

    # ✅ is_plus z DB
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        request.session.clear()
        return RedirectResponse(url='/login', status_code=303)
    is_plus_user = db_user.is_plus

    category_data = None
    if category:
        category_data = db.query(Category).filter(Category.id == category, Category.user_id == user_id).first()
        if not category_data:
            return RedirectResponse(url='/dashboard', status_code=303)

        if not is_plus_user:
            newest_category = db.query(Category)\
                .filter(Category.user_id == user_id)\
                .order_by(Category.created_at.desc())\
                .first()
            if newest_category and newest_category.id != category:
                return RedirectResponse(url='/dashboard', status_code=303)

    return templates.TemplateResponse("repeat.html", {
        "request": request,
        "email": user.get('email', ''),
        "category": category_data,
        "level": level
    })

# ============================================================
# AUTH API ENDPOINTS
# ============================================================

@app.post("/api/v1/register")
async def register(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name', email.split('@')[0])

        print(f"Register attempt: {email}")

        if email and password:
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="User with this email already exists")

            hashed_password = hash_password(password)

            new_user = User(
                email=email,
                name=name,
                is_plus=False,
                password=hashed_password
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            # Uvítací email
            from app.services.email_service import send_welcome_email
            try:
                send_welcome_email(new_user.email, new_user.name)
            except Exception as e:
                print(f"Welcome email error: {e}")

            session_user = {
                "id": new_user.id,
                "email": new_user.email,
                "name": new_user.name,
                "is_plus": new_user.is_plus,
                "dark_mode": new_user.dark_mode
            }
            request.session['user'] = session_user

            return JSONResponse({
                "message": "Registration successful",
                "user": session_user
            })
        else:
            raise HTTPException(status_code=400, detail="Email and password required")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/login")
async def login(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        email = data.get('email')
        password = data.get('password')

        print(f"Login attempt: {email}")

        if email and password:
            user = db.query(User).filter(User.email == email).first()

            if not user:
                raise HTTPException(status_code=400, detail="User not found. Please register first.")

            # Overenie hesla - bcrypt alebo argon2 s migráciou na bcrypt
            verified = False
            try:
                if verify_password(password, user.password):
                    verified = True
            except ValueError:
                if argon2.verify(password, user.password):
                    user.password = hash_password(password)
                    db.commit()
                    verified = True

            if not verified:
                raise HTTPException(status_code=400, detail="Incorrect password")

            user.last_login = datetime.utcnow()
            db.commit()

            session_user = {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "is_plus": user.is_plus,
                "dark_mode": user.dark_mode
            }
            request.session['user'] = session_user

            return JSONResponse({
                "message": "Login successful",
                "user": session_user
            })
        else:
            raise HTTPException(status_code=400, detail="Email and password required")

    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out successfully"}


# ============================================================
# GOOGLE OAUTH
# ============================================================

@app.get('/auth/google')
async def google_login(request: Request):
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/auth/google/callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get('/auth/google/callback', name='google_callback')
async def google_callback(request: Request, db: Session = Depends(get_db)):
    print("Google callback started")
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = await oauth.google.userinfo(token=token)
        print(f"User info: {user_info}")

        if not user_info or not user_info.get('email'):
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        email = user_info['email']
        name = user_info.get('name', email.split('@')[0])
        picture = user_info.get('picture', '')

        user = db.query(User).filter(User.email == email).first()
        new_user = False

        if not user:
            hashed_password = hash_password("google_auth_dummy_password")
            user = User(
                email=email,
                name=name,
                password=hashed_password,
                is_plus=False
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            new_user = True
            print(f"New user created: {user.email}")

            # Uvítací email pre nového Google užívateľa
            try:
                message = MessageSchema(
                    subject="Vitajte v WordKeeper! 🎉",
                    recipients=[email],
                    body=f"""Ahoj {name},

vitajte v WordKeeper! Sme radi, že ste sa k nám pridali cez Google.

Začnite učiť nové slovíčka ešte dnes:
https://wordkeeper-1096007793591.us-central1.run.app/dashboard

S pozdravom,
Tím WordKeeper
""",
                    subtype="plain"
                )
                fm = FastMail(mail_config)
                await fm.send_message(message)
            except Exception as e:
                print(f"Welcome email error: {e}")
        else:
            if not user.name and name:
                user.name = name
            user.last_login = datetime.utcnow()
            db.commit()
            print(f"Existing user found: {user.email}")

        session_user = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": picture,
            "is_plus": user.is_plus,
            "dark_mode": user.dark_mode
        }
        request.session['user'] = session_user
        print(f"Session set for user: {user.email}")

        jwt_token = create_access_token(data={"sub": user.email})
        callback_url = f"{request.base_url}auth/callback?token={jwt_token}&new_user={'1' if new_user else '0'}&email={email}&name={name}"
        print(f"Redirecting to callback: {callback_url}")
        return RedirectResponse(url=callback_url)

    except Exception as e:
        print(f"Google auth error: {e}")
        return RedirectResponse(url='/login?error=google_auth_failed')


@app.get("/auth/callback")
async def auth_callback(request: Request):
    return templates.TemplateResponse("auth-callback.html", {"request": request})


# ============================================================
# USER API ENDPOINTS
# ============================================================

@app.get("/api/user")
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get('user')
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == user_session['id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return JSONResponse({
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user_session.get('picture', ''),
        "is_plus": user.is_plus,
        "dark_mode": user.dark_mode,
        "created_at": user.created_at.isoformat() if user.created_at else None
    })


@app.patch("/api/user/plus")
async def toggle_user_plus(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get('user')
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == user_session['id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_plus = not user.is_plus
    db.commit()
    db.refresh(user)

    # ✅ Aktualizuj session
    user_session['is_plus'] = user.is_plus
    request.session['user'] = user_session

    return JSONResponse({
        "message": "Plus status updated successfully",
        "is_plus": user.is_plus
    })


@app.patch("/api/user/dark-mode")
async def toggle_user_dark_mode(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get('user')
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == user_session['id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.dark_mode = not user.dark_mode
    db.commit()
    db.refresh(user)

    # ✅ Aktualizuj session
    user_session['dark_mode'] = user.dark_mode
    request.session['user'] = user_session

    return JSONResponse({
        "message": "Dark mode status updated successfully",
        "dark_mode": user.dark_mode
    })


@app.delete("/api/user")
async def delete_user(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get('user')
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == user_session['id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    request.session.clear()

    return JSONResponse({
        "message": "User account and associated data deleted successfully"
    })


@app.get("/api/user/stats")
async def get_user_stats(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get('user')
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user_session['id']

    words_count = db.query(func.count(Word.id)).filter(Word.user_id == user_id).scalar() or 0
    categories_count = db.query(func.count(Category.id)).filter(Category.user_id == user_id).scalar() or 0
    tests_taken = db.query(func.coalesce(func.sum(Word.times_tested), 0)).filter(Word.user_id == user_id).scalar() or 0
    times_correct = db.query(func.coalesce(func.sum(Word.times_correct), 0)).filter(Word.user_id == user_id).scalar() or 0

    success_rate = 0
    if tests_taken > 0:
        success_rate = round((times_correct / tests_taken) * 100, 2)

    from app.schemas.word import KnowledgeLevel
    level_counts = {}
    for level in KnowledgeLevel:
        count = db.query(func.count(Word.id)).filter(
            Word.user_id == user_id,
            Word.knowledge_level == level.value
        ).scalar() or 0
        level_counts[level.value] = count

    return JSONResponse({
        "total_words": words_count,
        "total_categories": categories_count,
        "tests_taken": tests_taken,
        "success_rate": success_rate,
        "words_by_level": level_counts
    })


from fastapi.responses import StreamingResponse
import json

@app.get("/api/user/export")
async def export_user_data(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get('user')
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user_session['id']

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    categories = db.query(Category).filter(Category.user_id == user_id).all()
    words = db.query(Word).filter(Word.user_id == user_id).all()

    export_data = {
        "export_info": {
            "exported_at": datetime.utcnow().isoformat(),
            "user_id": user.id,
            "user_email": user.email,
            "user_name": user.name,
            "is_plus": user.is_plus
        },
        "categories": [
            {
                "id": cat.id,
                "name": cat.name,
                "description": cat.description,
                "created_at": cat.created_at.isoformat() if cat.created_at else None
            }
            for cat in categories
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
                "created_at": word.created_at.isoformat() if word.created_at else None
            }
            for word in words
        ]
    }

    def generate():
        yield json.dumps(export_data, indent=2, ensure_ascii=False)

    filename = f"wordkeeper_data_{user.email}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============================================================
# CATEGORIES API ENDPOINTS
# ============================================================

@app.get("/api/v1/categories", response_model=list[CategoryResponse])
async def get_categories(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get('user')
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user_session['id']
    categories = db.query(Category).filter(Category.user_id == user_id).all()

    from app.models.word import KnowledgeLevel

    result = []
    for category in categories:
        total_words = db.query(func.count(Word.id)).filter(Word.category_id == category.id, Word.user_id == user_id).scalar() or 0

        level_counts = {}
        for level in KnowledgeLevel:
            count = db.query(func.count(Word.id)).filter(
                Word.category_id == category.id,
                Word.knowledge_level == level.value,
                Word.user_id == user_id
            ).scalar() or 0
            level_counts[level.value] = count

        level_percentages = {}
        if total_words > 0:
            for level, count in level_counts.items():
                level_percentages[level] = round((count / total_words) * 100, 1)
        else:
            for level in KnowledgeLevel:
                level_percentages[level.value] = 0.0

        category_response = CategoryResponse(
            id=category.id,
            name=category.name,
            description=category.description,
            user_id=category.user_id,
            created_at=category.created_at,
            total_words=total_words,
            level_counts=level_counts,
            level_percentages=level_percentages
        )
        result.append(category_response)

    return result


@app.post("/api/v1/categories", response_model=CategoryResponse)
async def create_category(category_data: CategoryCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == category_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    category_count = db.query(Category).filter(Category.user_id == category_data.user_id).count()
    if category_count >= 5:
        raise HTTPException(status_code=400, detail="Maximum limit of 5 categories reached")

    existing_category = db.query(Category).filter(
        Category.name == category_data.name,
        Category.user_id == category_data.user_id
    ).first()
    if existing_category:
        raise HTTPException(status_code=400, detail="Category with this name already exists")

    new_category = Category(
        name=category_data.name,
        description=category_data.description,
        user_id=category_data.user_id
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)

    print(f"Category saved to database with ID: {new_category.id}")
    return new_category


@app.put("/api/v1/categories/{category_id}", response_model=CategoryResponse)
async def update_category(category_id: int, category_update: CategoryUpdate, request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get('user')
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user_session['id']
    category = db.query(Category).filter(Category.id == category_id, Category.user_id == user_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    for field, value in category_update.dict(exclude_unset=True).items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)

    from app.models.word import KnowledgeLevel

    total_words = db.query(func.count(Word.id)).filter(Word.category_id == category.id, Word.user_id == user_id).scalar() or 0

    level_counts = {}
    for level in KnowledgeLevel:
        count = db.query(func.count(Word.id)).filter(
            Word.category_id == category.id,
            Word.knowledge_level == level.value,
            Word.user_id == user_id
        ).scalar() or 0
        level_counts[level.value] = count

    level_percentages = {}
    if total_words > 0:
        for level, count in level_counts.items():
            level_percentages[level] = round((count / total_words) * 100, 1)
    else:
        for level in KnowledgeLevel:
            level_percentages[level.value] = 0.0

    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        created_at=category.created_at,
        user_id=category.user_id,
        total_words=total_words,
        level_counts=level_counts,
        level_percentages=level_percentages
    )


@app.delete("/api/v1/categories/{category_id}")
async def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    db.delete(category)
    db.commit()

    return {"message": "Category deleted successfully"}


@app.get("/api/v1/categories/{category_id}", response_model=CategoryResponse)
async def get_category_detail(category_id: int, request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get('user')
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user_session['id']
    category = db.query(Category).filter(Category.id == category_id, Category.user_id == user_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    from app.models.word import KnowledgeLevel

    total_words = db.query(func.count(Word.id)).filter(Word.category_id == category.id, Word.user_id == user_id).scalar() or 0

    level_counts = {}
    for level in KnowledgeLevel:
        count = db.query(func.count(Word.id)).filter(
            Word.category_id == category.id,
            Word.knowledge_level == level.value,
            Word.user_id == user_id
        ).scalar() or 0
        level_counts[level.value] = count

    level_percentages = {}
    if total_words > 0:
        for level, count in level_counts.items():
            level_percentages[level] = round((count / total_words) * 100, 1)
    else:
        for level in KnowledgeLevel:
            level_percentages[level.value] = 0.0

    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        user_id=category.user_id,
        created_at=category.created_at,
        total_words=total_words,
        level_counts=level_counts,
        level_percentages=level_percentages
    )


@app.get("/api/v1/categories/{category_id}/stats")
async def get_category_stats(category_id: int, request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get('user')
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    category = db.query(Category).filter(Category.id == category_id, Category.user_id == user_session['id']).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    total_words = db.query(func.count(Word.id)).filter(Word.category_id == category_id, Word.user_id == user_session['id']).scalar() or 0

    from app.models.word import KnowledgeLevel
    level_counts = {}
    for level in KnowledgeLevel:
        count = db.query(func.count(Word.id)).filter(
            Word.category_id == category_id,
            Word.knowledge_level == level.value,
            Word.user_id == user_session['id']
        ).scalar() or 0
        level_counts[level.value] = count

    stats = {
        "total_words": total_words,
        "dont_know_percentage": round((level_counts.get('dont_know', 0) / total_words * 100), 1) if total_words > 0 else 0,
        "learning_percentage": round((level_counts.get('learning', 0) / total_words * 100), 1) if total_words > 0 else 0,
        "know_percentage": round((level_counts.get('know', 0) / total_words * 100), 1) if total_words > 0 else 0
    }

    return JSONResponse(stats)


# ============================================================
# MISC API ENDPOINTS
# ============================================================

@app.get("/api/v1/users")
async def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [
        {"id": user.id, "email": user.email, "name": user.name}
        for user in users
    ]


@app.get("/api/debug/categories")
async def debug_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    return {
        "total_categories": len(categories),
        "categories": [
            {"id": cat.id, "name": cat.name, "description": cat.description, "user_id": cat.user_id}
            for cat in categories
        ]
    }


@app.get("/api/debug/users")
async def debug_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return {
        "total_users": len(users),
        "users": [
            {"id": user.id, "email": user.email, "name": user.name}
            for user in users
        ]
    }


# ============================================================
# STARTUP EVENT
# ============================================================

@app.on_event("startup")
async def startup_event():
    print("Database tables created")
    db = SessionLocal()
    try:
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        hashed_password = hash_password("test123")
        if not test_user:
            test_user = User(email="test@example.com", name="Test User", is_plus=False, password=hashed_password)
            db.add(test_user)
            print("Test user created with password 'test123'")
        else:
            if not verify_password("test123", test_user.password):
                test_user.password = hashed_password
                db.commit()
                print("Test user password updated to bcrypt hash")
            else:
                print("Test user already exists with correct password")
        db.commit()
    except Exception as e:
        print(f"Error creating/updating test user: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


# ============================================================
# EMAIL / PASSWORD RESET ENDPOINTS
# ============================================================

@app.get("/forgot-password")
async def forgot_password_page(request: Request):
    return templates.TemplateResponse("forgot_password.html", {"request": request})


@app.post("/api/v1/forgot-password")
async def forgot_password(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    email = data.get("email")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return JSONResponse({"message": "Ak email existuje, poslali sme odkaz."})

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.commit()

    reset_url = f"{request.base_url}reset-password?token={token}"
    message = MessageSchema(
        subject="Reset hesla – WordKeeper",
        recipients=[email],
        body=f"Klikni na odkaz pre reset hesla:\n\n{reset_url}\n\nOdkaz je platný 1 hodinu.",
        subtype="plain"
    )
    fm = FastMail(mail_config)
    await fm.send_message(message)

    return JSONResponse({"message": "Ak email existuje, poslali sme odkaz."})


@app.get("/reset-password")
async def reset_password_page(request: Request, token: str):
    return templates.TemplateResponse("reset_password.html", {"request": request, "token": token})


@app.post("/api/v1/reset-password")
async def reset_password(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    token = data.get("token")
    new_password = data.get("password")

    user = db.query(User).filter(User.reset_token == token).first()

    if not user or user.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token je neplatný alebo vypršal.")

    user.password = hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return JSONResponse({"message": "Heslo bolo zmenené."})
