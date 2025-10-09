from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.user import User
from app.schemas.user import UserResponse, PlusStatusUpdate

router = APIRouter(tags=["users"])

def get_language_from_request(request: Request) -> str:
    """Získa jazyk z request headers alebo query parametrov."""
    lang = request.query_params.get("lang")
    if lang in ["en", "sk"]:
        return lang
    accept_language = request.headers.get("accept-language", "")
    if "sk" in accept_language.lower():
        return "sk"
    return "en"

@router.get("/users/me", response_model=UserResponse)
def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    # TODO: Implementovať autentifikáciu a získanie aktuálneho používateľa
    # Pre teraz vrátime prvého používateľa z databázy
    user = db.query(User).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.patch("/users/me/plus", response_model=UserResponse)
def update_plus_status(
    plus_update: PlusStatusUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    lang = get_language_from_request(request)
    
    # TODO: Implementovať autentifikáciu
    user = db.query(User).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_plus = plus_update.is_plus
    db.commit()
    db.refresh(user)
    
    return user

@router.get("/users/me/plus")
def get_plus_status(
    request: Request,
    db: Session = Depends(get_db)
):
    # TODO: Implementovať autentifikáciu
    user = db.query(User).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"is_plus": user.is_plus}