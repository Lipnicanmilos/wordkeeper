import atexit
import logging
import os
import queue
from logging.handlers import (
    QueueHandler,
    QueueListener,
    SMTPHandler,
    TimedRotatingFileHandler,
)

from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from fastapi_mail import ConnectionConfig
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.config import Config

load_dotenv()

# Cesta k log súboru (rotujúci) — využíva ju aj admin endpoint na zobrazenie logov.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.getenv("LOG_DIR", os.path.join(_PROJECT_ROOT, "logs"))
LOG_FILE = os.path.join(LOG_DIR, "lexinova.log")


def _setup_logging() -> logging.Logger:
    """Konzola + rotujúci súbor (drží ~48h) + voliteľné e-mail alerty.

    - Súbor: rotácia každú polnoc, `backupCount=1` → drží sa current deň +
      1 predošlý ⇒ záznamy staršie ako ~48h sa automaticky mažú.
    - E-mail: posiela sa pri ERROR+ cez frontu (neblokuje requesty); aktívne
      iba ak je nastavené `ERROR_ALERT_EMAIL` + MAIL prihlasovacie údaje.
    """
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in list(root.handlers):  # vyčisti basicConfig/predošlé pri reloade
        root.removeHandler(handler)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    # Rotujúci súbor — ~48h retencia. Na read-only FS ticho preskočíme.
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            LOG_FILE,
            when="midnight",
            interval=1,
            backupCount=1,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except OSError:
        pass

    # E-mail upozornenia pri chybách (ERROR+), neblokujúco cez frontu.
    alert_to = os.getenv("ERROR_ALERT_EMAIL")
    mail_user = os.getenv("MAIL_USERNAME")
    mail_pass = os.getenv("MAIL_PASSWORD")
    if alert_to and mail_user and mail_pass:
        smtp_handler = SMTPHandler(
            mailhost=("smtp.gmail.com", 587),
            fromaddr=os.getenv("MAIL_FROM", mail_user),
            toaddrs=[e.strip() for e in alert_to.split(",") if e.strip()],
            subject="[LexiNova] Chyba v aplikacii",
            credentials=(mail_user, mail_pass),
            secure=(),  # STARTTLS
        )
        smtp_handler.setLevel(logging.ERROR)
        smtp_handler.setFormatter(fmt)
        log_queue: queue.Queue = queue.Queue(-1)
        root.addHandler(QueueHandler(log_queue))
        listener = QueueListener(log_queue, smtp_handler, respect_handler_level=True)
        listener.start()
        atexit.register(listener.stop)

    return logging.getLogger("lexinova")


logger = _setup_logging()

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

# Admin allow-list (comma separated) for admin endpoints
ADMIN_EMAILS = [
    e.strip().lower()
    for e in (os.getenv("ADMIN_EMAILS", "") or "").split(",")
    if e.strip()
]



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
