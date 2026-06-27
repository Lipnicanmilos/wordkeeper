import os
import re
import secrets
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi_mail import FastMail, MessageSchema
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.hash import argon2
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.utils import utcnow
from app.services.auth_service import hash_password, verify_password
from app.services.email_service import send_welcome_email
from app.services.runtime import SECRET_KEY, limiter, logger, mail_config, oauth

_signer = URLSafeTimedSerializer(SECRET_KEY, salt="oauth-finalize")

router = APIRouter(tags=["authentication"])

# Sila hesla – musí sedieť s frontend validáciou v register.html
# (aspoň 8 znakov, veľké písmeno, malé písmeno, číslica).
PASSWORD_MIN_LENGTH = 8


def password_strength_error(password: str) -> Optional[str]:
    """Vráti chybovú hlášku ak heslo nespĺňa požiadavky, inak None."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Heslo musí mať aspoň {PASSWORD_MIN_LENGTH} znakov."
    if not re.search(r"[A-Z]", password):
        return "Heslo musí obsahovať veľké písmeno."
    if not re.search(r"[a-z]", password):
        return "Heslo musí obsahovať malé písmeno."
    if not re.search(r"[0-9]", password):
        return "Heslo musí obsahovať číslicu."
    return None


def _validate_password_field(value: str) -> str:
    error = password_strength_error(value)
    if error:
        raise ValueError(error)
    return value


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

    _check_password = field_validator("password")(_validate_password_field)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class PasswordReset(BaseModel):
    token: str
    password: str

    _check_password = field_validator("password")(_validate_password_field)


@router.post("/api/v1/register")
@limiter.limit("5/hour")
async def register(
    request: Request,
    user_data: UserRegister,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        email = user_data.email
        password = user_data.password
        name = user_data.name or email.split("@")[0]

        if not (email and password):
            raise HTTPException(status_code=400, detail="Email and password required")

        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="User with this email already exists")

        new_user = User(
            email=email,
            name=name,
            is_plus=False,
            password=hash_password(password),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        background_tasks.add_task(send_welcome_email, new_user.email, new_user.name)

        session_user = {
            "id": new_user.id,
            "email": new_user.email,
            "name": new_user.name,
            "is_plus": new_user.is_plus,
            "dark_mode": new_user.dark_mode,
        }
        request.session["user"] = session_user

        return JSONResponse({"message": "Registration successful", "user": session_user})
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Registration error: {exc}")
        raise HTTPException(status_code=400, detail="Registration failed. Please try again.")


@router.post("/api/v1/login")
@limiter.limit("10/minute")
async def login(request: Request, user_data: UserLogin, db: Session = Depends(get_db)):
    try:
        email = user_data.email
        password = user_data.password

        if not (email and password):
            raise HTTPException(status_code=400, detail="Email and password required")

        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=400, detail="User not found. Please register first.")

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

        user.last_login = utcnow()
        db.commit()

        session_user = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_plus": user.is_plus,
            "dark_mode": user.dark_mode,
        }
        request.session["user"] = session_user

        return JSONResponse({"message": "Login successful", "user": session_user})
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Login error: {exc}")
        raise HTTPException(status_code=400, detail="Login failed. Please try again.")


@router.get("/api/v1/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out successfully"}


@router.get("/auth/google")
async def google_login(request: Request):
    redirect_uri = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "https://lexinova-1096007793591.us-central1.run.app/auth/google/callback",
    )
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback", name="google_callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    logger.info("Google callback started")
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = await oauth.google.userinfo(token=token)
        logger.info(f"User info received for: {user_info.get('email')}")

        if not user_info or not user_info.get("email"):
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        email = user_info["email"]
        name = user_info.get("name", email.split("@")[0])
        picture = user_info.get("picture", "")

        user = db.query(User).filter(User.email == email).first()
        new_user = False

        if not user:
            user = User(
                email=email,
                name=name,
                password=hash_password("google_auth_dummy_password"),
                is_plus=False,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            new_user = True
            logger.info(f"New user created: {user.email}")

            try:
                message = MessageSchema(
                    subject="Vitajte v LexiNova! 🎉",
                    recipients=[email],
                    body=f"""Ahoj {name},

vitajte v LexiNova! Sme radi, že ste sa k nám pridali cez Google.

Začnite učiť nové slovíčka ešte dnes:
https://lexinova-1096007793591.us-central1.run.app/dashboard

S pozdravom,
Tím LexiNova
""",
                    subtype="plain",
                )
                fm = FastMail(mail_config)
                await fm.send_message(message)
            except Exception as exc:
                logger.error(f"Welcome email error: {exc}")
        else:
            if not user.name and name:
                user.name = name
            user.last_login = utcnow()
            db.commit()

        session_user = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": picture,
            "is_plus": user.is_plus,
            "dark_mode": user.dark_mode,
        }
        logger.info(f"OAuth success for user_id: {session_user['id']}, redirecting to finalize")

        # Podpísaný URL token (60s TTL) — session nastavíme až v /auth/finalize,
        # nie tu, aby sme obišli Cloud Run bug kde Set-Cookie z callback response
        # sa stratí pred tým, než browser pošle /dashboard request.
        token = _signer.dumps(session_user)
        return RedirectResponse(url=f"/auth/finalize?t={token}", status_code=303)
    except Exception as exc:
        logger.error(f"Google auth error: {exc}")
        return RedirectResponse(url="/login?error=google_auth_failed")


@router.get("/auth/finalize")
async def google_finalize(request: Request, t: str):
    try:
        session_user = _signer.loads(t, max_age=60)
    except SignatureExpired:
        logger.warning("OAuth finalize: token expired")
        return RedirectResponse(url="/login?error=session_expired")
    except BadSignature:
        logger.warning("OAuth finalize: invalid token")
        return RedirectResponse(url="/login?error=google_auth_failed")

    request.session["user"] = session_user
    logger.info(f"Session finalized for user_id: {session_user['id']}, keys: {list(request.session.keys())}")
    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/api/v1/forgot-password")
@limiter.limit("3/hour")
async def forgot_password(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    email = data.get("email")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return JSONResponse({"message": "Ak email existuje, poslali sme odkaz."})

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = utcnow() + timedelta(hours=1)
    db.commit()

    reset_url = f"{request.base_url}reset-password?token={token}"
    message = MessageSchema(
        subject="Reset hesla – LexiNova",
        recipients=[email],
        body=f"Klikni na odkaz pre reset hesla:\n\n{reset_url}\n\nOdkaz je platný 1 hodinu.",
        subtype="plain",
    )
    fm = FastMail(mail_config)
    await fm.send_message(message)

    return JSONResponse({"message": "Ak email existuje, poslali sme odkaz."})


@router.post("/api/v1/reset-password")
@limiter.limit("5/hour")
async def reset_password(
    request: Request, data: PasswordReset, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.reset_token == data.token).first()
    if not user or user.reset_token_expires < utcnow():
        raise HTTPException(status_code=400, detail="Token je neplatný alebo vypršal.")

    user.password = hash_password(data.password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return JSONResponse({"message": "Heslo bolo zmenené."})
