from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.services.auth_service import hash_password, verify_password, create_access_token

# Pridaj prefix /api k routeru
# router = APIRouter(prefix="/api", tags=["authentication"])  # <-- DÔLEŽITÉ: prefix="/api"
router = APIRouter(prefix="/api/v1", tags=["authentication"])  # <-- pridaj /v1

def get_error_message(lang: str, key: str) -> str:
    """Vráti chybovú správu v zvolenom jazyku."""
    messages = {
        "en": {
            "email_exists": "Email already registered",
            "invalid_credentials": "Incorrect email or password",
            "registration_failed": "Registration failed",
            "login_failed": "Login failed"
        },
        "sk": {
            "email_exists": "Email je už zaregistrovaný",
            "invalid_credentials": "Nesprávny email alebo heslo",
            "registration_failed": "Registrácia zlyhala",
            "login_failed": "Prihlásenie zlyhalo"
        }
    }
    return messages.get(lang, messages["en"]).get(key, key)

def get_language_from_request(request: Request) -> str:
    """Získa jazyk z request headers alebo query parametrov."""
    # Skontrolovať query parameter
    lang = request.query_params.get("lang")
    if lang in ["en", "sk"]:
        return lang
    
    # Skontrolovať Accept-Language header
    accept_language = request.headers.get("accept-language", "")
    if "sk" in accept_language.lower():
        return "sk"
    
    # Predvolený jazyk
    return "en"

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, request: Request, db: Session = Depends(get_db)):
    lang = get_language_from_request(request)
    
    # Skontrolovať, či používateľ už existuje
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_error_message(lang, "email_exists")
        )
    
    # Vytvoriť nového používateľa s Plus deaktivovaným
    try:
        hashed_password = hash_password(user.password)
        db_user = User(
            email=user.email, 
            hashed_password=hashed_password,
            is_plus=False  # NOVÝ ÚČET MÁ PLUS DEAKTIVOVANÉ
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_error_message(lang, "registration_failed")
        )

@router.post("/login")
def login(user: UserLogin, request: Request, db: Session = Depends(get_db)):
    lang = get_language_from_request(request)
    
    # Nájsť používateľa
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=get_error_message(lang, "invalid_credentials")
        )
    
    # Vytvoriť access token
    access_token = create_access_token(data={"sub": db_user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": db_user.id,
        "email": db_user.email
    }