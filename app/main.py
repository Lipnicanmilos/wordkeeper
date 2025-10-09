from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
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
from app.schemas.category import CategoryCreate, CategoryResponse
from app.models.category import Category
from app.models.user import User
from app.models.word import Word
from app.routers import words  # Import words routeru
from sqlalchemy.orm import Session
from sqlalchemy import func

load_dotenv()

app = FastAPI()

# Pridajte words router do aplikácie - IBA RAZ
app.include_router(words.router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "your-secret-key-12345"))

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

# Routes
@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register")  # PRIDAJTE TENTO ENDPOINT
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard")
async def dashboard_page(request: Request):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login', status_code=303)
    return templates.TemplateResponse("dashboard.html", {"request": request, "email": user.get('email', '')})

@app.get("/profile")
async def profile_page(request: Request):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login', status_code=303)
    return templates.TemplateResponse("profile.html", {"request": request, "email": user.get('email', '')})

@app.get("/category/{category_id}/words")
async def category_words_page(request: Request, category_id: int, db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login', status_code=303)

    # Get category details
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        return RedirectResponse(url='/dashboard', status_code=303)

    return templates.TemplateResponse("category_words.html", {
        "request": request,
        "email": user.get('email', ''),
        "category": category
    })

@app.get("/test")
async def test_page(request: Request, category: int = None, level: str = None, db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/login', status_code=303)

    # Get category details if provided
    category_data = None
    if category:
        category_data = db.query(Category).filter(Category.id == category).first()
        if not category_data:
            return RedirectResponse(url='/dashboard', status_code=303)

    return templates.TemplateResponse("flashcard_test.html", {
        "request": request,
        "email": user.get('email', ''),
        "category": category_data,
        "level": level
    })

from passlib.hash import argon2

# REGISTER ENDPOINT - PRIDAJTE TENTO ENDPOINT
@app.post("/api/v1/register")
async def register(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name', email.split('@')[0])  # Použije email ak meno nie je zadané
        
        print(f"Register attempt: {email}")
        
        if email and password:
            # Skontrolujte či používateľ už existuje
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="User with this email already exists")
            
            # Hashovanie hesla pomocou argon2
            hashed_password = argon2.hash(password)
            
            # Vytvorte nového používateľa
            new_user = User(
                email=email,
                name=name,
                is_plus=False,
                password=hashed_password
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            # Uložte do session
            session_user = {
                "id": new_user.id,
                "email": new_user.email,
                "name": new_user.name,
                "is_plus": new_user.is_plus
            }
            
            request.session['user'] = session_user
            
            return JSONResponse({
                "message": "Registration successful",
                "user": session_user
            })
        else:
            raise HTTPException(status_code=400, detail="Email and password required")
            
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# LOGIN ENDPOINT
@app.post("/api/v1/login")
async def login(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        email = data.get('email')
        password = data.get('password')
        
        print(f"Login attempt: {email}")
        
        if email and password:
            # Skontrolujte či používateľ už existuje v DB
            user = db.query(User).filter(User.email == email).first()
            
            if not user:
                raise HTTPException(status_code=400, detail="User not found. Please register first.")
            
            # Overenie hesla pomocou argon2
            if not argon2.verify(password, user.password):
                raise HTTPException(status_code=400, detail="Incorrect password")
            
            # Uložte do session
            session_user = {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "is_plus": user.is_plus
            }
            
            request.session['user'] = session_user
            
            return JSONResponse({
                "message": "Login successful",
                "user": session_user
            })
        else:
            raise HTTPException(status_code=400, detail="Email and password required")
            
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out successfully"}

# Google OAuth routes
@app.get('/auth/google')
async def google_login(request: Request):
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/auth/google/callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get('/auth/google/callback', name='google_callback')
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')

        if not user_info or not user_info.get('email'):
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        email = user_info.email
        name = user_info.get('name', email.split('@')[0])
        picture = user_info.get('picture', '')

        # Find or create user
        user = db.query(User).filter(User.email == email).first()
        new_user = False

        if not user:
            # Create new user with dummy password
            hashed_password = argon2.hash("google_auth_dummy_password")
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
        else:
            # Update name if not set
            if not user.name and name:
                user.name = name
                db.commit()

        # Set session for web auth
        session_user = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": picture,
            "is_plus": user.is_plus
        }
        request.session['user'] = session_user

        # Generate JWT token for API auth (as expected by frontend)
        from app.services.auth_service import create_access_token
        jwt_token = create_access_token(data={"sub": user.email})

        # Redirect to callback page with token
        callback_url = f"/auth/callback?token={jwt_token}&new_user={'1' if new_user else '0'}&email={email}"
        return RedirectResponse(url=callback_url)

    except Exception as e:
        print(f"Google auth error: {e}")
        return RedirectResponse(url='/login?error=google_auth_failed')

@app.get("/auth/callback")
async def auth_callback(request: Request):
    return templates.TemplateResponse("auth-callback.html", {"request": request})

# API endpoints
@app.get("/api/user")
async def get_current_user(request: Request):
    user = request.session.get('user')
    if user:
        return JSONResponse({
            "id": user.get('id'),
            "email": user['email'],
            "name": user.get('name', ''),
            "picture": user.get('picture', ''),
            "is_plus": user.get('is_plus', False)
        })
    else:
        raise HTTPException(status_code=401, detail="Not authenticated")

@app.patch("/api/user/plus")
async def toggle_user_plus(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get('user')
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == user_session['id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Toggle the is_plus status
    user.is_plus = not user.is_plus
    db.commit()
    db.refresh(user)

    # Update session
    user_session['is_plus'] = user.is_plus
    request.session['user'] = user_session

    return JSONResponse({
        "message": "Plus status updated successfully",
        "is_plus": user.is_plus
    })

@app.delete("/api/user")
async def delete_user(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get('user')
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == user_session['id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete the user (cascade will delete categories and words)
    db.delete(user)
    db.commit()

    # Clear session
    request.session.clear()

    return JSONResponse({
        "message": "User account and associated data deleted successfully"
    })

# KATEGÓRIE S DATABÁZOU
@app.get("/api/v1/categories", response_model=list[CategoryResponse])
async def get_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    print(f"Loaded {len(categories)} categories from database")
    return categories

@app.post("/api/v1/categories", response_model=CategoryResponse)
async def create_category(category_data: CategoryCreate, db: Session = Depends(get_db)):
    # Skontrolujte či používateľ existuje
    user = db.query(User).filter(User.id == category_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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

@app.delete("/api/v1/categories/{category_id}")
async def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db.delete(category)
    db.commit()
    
    return {"message": "Category deleted successfully"}

# Endpoint na získanie používateľov
@app.get("/api/v1/users")
async def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [
        {"id": user.id, "email": user.email, "name": user.name}
        for user in users
    ]

# Debug endpointy
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

# Automaticky vytvor tabuľky pri štarte
@app.on_event("startup")
async def startup_event():
    # Najprv vytvoríme všetky tabuľky
    Base.metadata.create_all(bind=engine)
    print("Database tables created")
    
    # Potom vytvoríme testovacieho používateľa
    db = SessionLocal()
    try:
        test_user = db.query(User).filter(User.email == "test@example.com").first()
        if not test_user:
            hashed_password = argon2.hash("test123")
            test_user = User(email="test@example.com", name="Test User", is_plus=False, password=hashed_password)
            db.add(test_user)
            db.commit()
            print("Test user created with password 'test123'")
        else:
            print("Test user already exists")
    except Exception as e:
        print(f"Error creating test user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

# New endpoint to get user statistics
@app.get("/api/user/stats")
async def get_user_stats(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get('user')
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user_session['id']

    # Count words for user
    words_count = db.query(func.count(Word.id)).filter(Word.user_id == user_id).scalar() or 0

    # Count categories for user
    categories_count = db.query(func.count(Category.id)).filter(Category.user_id == user_id).scalar() or 0

    # Sum tests taken and times correct for user's words
    tests_taken = db.query(func.coalesce(func.sum(Word.times_tested), 0)).filter(Word.user_id == user_id).scalar() or 0
    times_correct = db.query(func.coalesce(func.sum(Word.times_correct), 0)).filter(Word.user_id == user_id).scalar() or 0

    # Calculate success rate
    success_rate = 0
    if tests_taken > 0:
        success_rate = round((times_correct / tests_taken) * 100, 2)

    # Count words by knowledge level
    from app.schemas.word import KnowledgeLevel
    level_counts = {}
    for level in KnowledgeLevel:
        count = db.query(func.count(Word.id)).filter(
            Word.user_id == user_id,
            Word.knowledge_level == level.value
        ).scalar() or 0
        level_counts[level.value] = count

    return JSONResponse({
        "words_count": words_count,
        "categories_count": categories_count,
        "tests_taken": tests_taken,
        "success_rate": success_rate,
        "words_by_level": level_counts
    })

from fastapi.responses import StreamingResponse
import json
from datetime import datetime

@app.get("/api/user/export")
async def export_user_data(request: Request, db: Session = Depends(get_db)):
    user_session = request.session.get('user')
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user_session['id']

    # Get user data
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all categories for user
    categories = db.query(Category).filter(Category.user_id == user_id).all()

    # Get all words for user
    words = db.query(Word).filter(Word.user_id == user_id).all()

    # Prepare export data
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
                "word": word.word,
                "translation": word.translation,
                "category_id": word.category_id,
                "knowledge_level": word.knowledge_level,
                "times_tested": word.times_tested,
                "times_correct": word.times_correct,
                "last_tested": word.last_tested.isoformat() if word.last_tested else None,
                "created_at": word.created_at.isoformat() if word.created_at else None
            }
            for word in words
        ]
    }

    # Create JSON response for download
    def generate():
        yield json.dumps(export_data, indent=2, ensure_ascii=False)

    filename = f"wordkeeper_data_{user.email}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
