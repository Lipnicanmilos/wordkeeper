import logging
import os

from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from fastapi_mail import ConnectionConfig
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.config import Config

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(APP_DIR, "static")
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

limiter = Limiter(key_func=get_remote_address)

config = Config(".env")
oauth = OAuth(config)
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    client_kwargs={"scope": "openid email profile"},
)

mail_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)


def is_debug_mode() -> bool:
    return os.getenv("DEBUG", "false").lower() == "true"


def get_secret_key() -> str:
    key = os.getenv("SECRET_KEY") or os.getenv("SESSION_SECRET")
    if key:
        # Produkcia: vynúť minimálnu silu kľúča (session + JWT)
        if not is_debug_mode() and len(key) < 32:
            raise RuntimeError("SECRET_KEY must be at least 32 characters when DEBUG=false")
        return key
    if is_debug_mode():
        logger.warning("SECRET_KEY not set — using dev fallback (DEBUG mode only)")
        return "dev-secret-123"
    raise RuntimeError("SECRET_KEY must be set when DEBUG=false")


SECRET_KEY = get_secret_key()
