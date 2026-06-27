# LexiNova

**LexiNova** je moderná webová aplikácia na učenie sa slovíčok s AI generovaním sád, flashcard testami a inteligentným opakovaním. Funguje aj offline ako PWA.

**Live demo:** [lexinova-1096007793591.us-central1.run.app](https://lexinova-1096007793591.us-central1.run.app)
**Vyskúšaj bez registrácie:** [/demo](https://lexinova-1096007793591.us-central1.run.app/demo)

---

## ✨ Funkcie

- **AI generovanie slovíčok** — napíš tému, vyber jazyky a AI vytvorí celú sadu (Groq / Gemini / Claude)
- **Demo bez registrácie** — vyskúšaj flashcard učenie hneď na `/demo`
- **Autentifikácia** — email/heslo (so server-side validáciou sily hesla) alebo Google OAuth
- **Kategórie a slovíčka** — vytváranie, úprava, mazanie, organizácia do tematických sád
- **Flashcard testovanie** — 2 úrovne znalosti (viem / neviem), obojsmerne (originál → preklad aj naopak)
- **Opakovanie** — dedikovaný režim opakovania podľa úrovne znalosti
- **Import slovíčok** — hromadné nahrávanie z Excelu/CSV
- **Štatistiky** — sledovanie pokroku a úspešnosti
- **Dark mode + EN/SK** — svetlý/tmavý režim a dvojjazyčné rozhranie
- **Plus verzia** — rozšírené limity kategórií
- **PWA** — inštalovateľná ako mobilná appka, funguje offline (Service Worker)
- **Email notifikácie** — uvítacie emaily, reset hesla, notifikácie o dotazoch
- **Kontaktný formulár** — v pätičke, bez prihlásenia
- **GDPR** — export dát (JSON), zmazanie účtu (ORM cascade), Privacy Policy + Obchodné podmienky (SK/EN)
- **Bezpečnosť** — rate limiting, security hlavičky (CSP/HSTS/…), self-hostované fonty
- **Admin panel** — správa používateľov, prehľad platieb, správa dopytov

---

## 🛠️ Technológie

### Backend
- **FastAPI** 0.118.0 — Python web framework (s `lifespan` namiesto `on_event`)
- **SQLAlchemy** 2.0.43 — ORM
- **PostgreSQL** (Supabase) — databáza
- **Bcrypt** — hashovanie hesiel
- **Python-JOSE** — JWT tokeny
- **FastAPI-Mail** — email služba
- **Authlib** — Google OAuth
- **Anthropic SDK** — Claude AI
- **httpx** — async HTTP klient (Groq & Gemini REST API)
- **slowapi** — rate limiting

### AI poskytovatelia
| Poskytovateľ | Model (default) | Cena |
|--------------|-----------------|------|
| **Groq** (predvolený) | `llama-3.3-70b-versatile` | free tier (~14 400 req/deň) |
| **Google Gemini** | `gemini-2.0-flash` | free tier cez AI Studio |
| **Anthropic Claude** | `claude-opus-4-8` | platený |

> Do AI sa posiela **iba text zadania (prompt) + zvolené jazyky** — žiadne identifikačné údaje používateľa.

### Frontend
- **Jinja2** — template engine
- **Vanilla JavaScript** — bez frameworkov
- **CSS3** — moderný dizajn, dark mode, CSS premenné
- **Inter** — self-hostovaný variabilný font (žiadne volania na Google Fonts CDN)
- **Font Awesome 6.4** — self-hostované ikony v `static/vendor/fontawesome/` (žiadny CDN)
- **Chart.js 4.5** — self-hostované grafy v `static/vendor/chartjs/` (žiadny CDN)
- **Service Worker** — PWA / offline

> Aplikácia **nevolá žiadny externý CDN** — všetky fonty, ikony aj skripty sú self-hostované (GDPR-friendly, prísna CSP `'self'`).

---

## 🔒 Bezpečnosť a súkromie

- **Heslá** — bcrypt hash; server-side validácia sily (min. 8 znakov, veľké + malé písmeno, číslica) na registrácii aj resete
- **Validácia vstupov** — `EmailStr` na registrácii/prihlásení, Pydantic schémy
- **Rate limiting** (per IP, slowapi):
  - `register` 5/h · `login` 10/min · `forgot-password` 3/h · `reset-password` 5/h
  - `inquiry` 5/h · `ai-create` 10/h (ochrana AI kreditov)
- **Security hlavičky** (middleware): `Content-Security-Policy`, `Strict-Transport-Security` (v produkcii), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`
- **CORS** — origins podľa prostredia (localhost len v DEBUG; vlastná doména cez env `FRONTEND_ORIGIN`)
- **Session** — `HttpOnly` + `Secure` (v produkcii) cookie, `SameSite=Lax`
- **Admin** — endpointy chránené allow-listom emailov (`ADMIN_EMAILS`)
- **Chyby** — interné detaily sa logujú, klientovi sa vracia generická hláška
- **GDPR** — self-hostované fonty (žiadny leak IP na Google), Privacy Policy (`/privacy`) s identifikáciou prevádzkovateľa a dobou uchovávania, Obchodné podmienky (`/terms`), export dát a zmazanie účtu

---

## 📋 Požiadavky

- Python 3.12+
- PostgreSQL databáza (Supabase)
- Gmail účet pre SMTP (email služba)
- Google Cloud projekt (pre OAuth)
- API kľúč pre AI (Groq odporúčaný — zadarmo na [console.groq.com](https://console.groq.com))

---

## 🚀 Inštalácia a spustenie

```bash
# 1. Klonovanie
git clone https://github.com/Lipnicanmilos/lexinova.git
cd lexinova

# 2. Virtuálne prostredie
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac

# 3. Závislosti
pip install -r requirements.txt

# 4. Konfigurácia — vytvor .env (viď nižšie)

# 5. Spustenie
uvicorn app.main:app --reload --port 8000
# alebo: python -m app.main
```

Aplikácia beží na `http://localhost:8000`.

### `.env` súbor

```env
# Databáza
DATABASE_URL=postgresql://user:password@host:port/database

# Bezpečnosť
SECRET_KEY=your-super-secret-key-min-32-characters   # min. 32 znakov pri DEBUG=false

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Email (Gmail SMTP)
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-specific-password
MAIL_FROM=your-email@gmail.com

# Prostredie
DEBUG=true                        # false v produkcii (zapne HSTS, secure cookies, vypne localhost CORS)
# FRONTEND_ORIGIN=https://tvoja-domena.sk   # voliteľné — pridá vlastnú doménu do CORS

# AI poskytovatelia (stačí jeden)
GROQ_API_KEY=gsk_...              # Groq — zadarmo, odporúčané
GEMINI_API_KEY=AIzaSy...          # Google Gemini — zadarmo cez AI Studio
ANTHROPIC_API_KEY=sk-ant-...      # Claude — platený

# Admin (voliteľné)
ADMIN_EMAILS=admin@example.com,other@example.com
INQUIRY_TO=admin@example.com      # kam posielať notifikácie o dotazoch

# Logy a monitoring (voliteľné)
ERROR_ALERT_EMAIL=admin@example.com   # e-mail upozornenia pri chybách (ERROR+); prázdne = vypnuté
# LOG_DIR=logs                        # priečinok pre rotujúce logy (default: ./logs)

# Migrácia — spusti create_all len pri explicitnom požiadaní
# RUN_DB_CREATE_ALL=1

# Override modelov (voliteľné)
# GROQ_MODEL=llama-3.3-70b-versatile
# GEMINI_MODEL=gemini-2.0-flash
# CLAUDE_MODEL=claude-opus-4-8
```

---

## 🧪 Testy

Automatické testy (pytest) bežia proti dočasnej **SQLite** databáze — nepotrebujú Supabase ani internet, neposielajú reálne e-maily a rate limiting majú vypnutý (okrem testu, ktorý ho overuje).

### Príprava (raz)

```powershell
# Aktivuj virtuálne prostredie
.\venv\Scripts\Activate.ps1        # Windows PowerShell
# venv\Scripts\activate.bat        # Windows cmd
# source venv/bin/activate         # Linux/Mac

# Nainštaluj závislosti (vrátane pytest)
python -m pip install -r requirements.txt
```

### Spustenie

```bash
python -m pytest                       # všetky testy
python -m pytest -v                    # podrobný výpis (každý test zvlášť)
python -m pytest tests/test_auth.py    # konkrétny súbor
python -m pytest -k password           # len testy s "password" v názve
```

> Tip: `python -m pytest` (namiesto holého `pytest`) funguje vždy, aj keď bol venv premenovaný/presunutý.

Pokrývajú: načítanie verejných stránok, security hlavičky, self-hostované fonty, validáciu registrácie (email + sila hesla), prihlásenie a rate limiting (429). Aktuálne **20 testov**.

## 📊 Logy a monitoring

- **Konzola** — všetky logy idú na stdout (na Cloud Run ich zbiera Cloud Logging).
- **Rotujúci súbor** — `logs/lexinova.log`, rotácia každú polnoc, **drží sa ~48h**, staršie sa automaticky mažú. Priečinok cez `LOG_DIR`.
- **Admin prehliadač logov** — záložka **Logy** v admin paneli (`/admin`) zobrazuje posledné riadky logu naživo (`GET /api/admin/logs`, len admin), s voliteľnou auto-obnovou každých 10 s.
- **E-mail upozornenia** — pri chybách (`ERROR+`) sa pošle e-mail na `ERROR_ALERT_EMAIL` (cez Gmail SMTP, neblokujúco cez frontu). Aktívne iba ak je `ERROR_ALERT_EMAIL` aj MAIL údaje nastavené.

> ⚠️ Na **Cloud Run** je súborový systém efemérny — admin prehliadač ukáže logy len aktuálnej inštancie od posledného reštartu. Pre trvalé online logy (~30 dní) použi **Google Cloud Logging**.

## 🗄️ Databázová štruktúra

- **Users** — `id`, `email` (unikátny), `name`, `password` (bcrypt), `is_plus`, `dark_mode`, `created_at`, `last_login`, `reset_token`, `reset_token_expires`
- **Categories** — `id`, `name`, `description`, `user_id` → users, `created_at`, `updated_at`
- **Words** — `id`, `original_word`, `translation`, `language_from`, `language_to`, `category_id` → categories (CASCADE), `user_id`, `knowledge_level` (enum `dont_know`/`learning`/`know` — UI používa 2 úrovne, `learning` sa mapuje na `dont_know`), `times_tested`, `times_correct`, `last_tested`, `created_at`, `updated_at`
- **Payments** — `id`, `user_id` → users (SET NULL), `email`, `provider`, `provider_payment_id`, `provider_subscription_id`, `status`, `amount`, `currency` (default `EUR`), `description`, `created_at`
- **Inquiries** — `id`, `name`, `email`, `message`, `page`, `user_agent`, `is_read`, `created_at`

---

## 📁 Štruktúra projektu

```
LexiNova/
├── app/
│   ├── database/connection.py   # DB pripojenie
│   ├── models/                  # SQLAlchemy modely (user, category, word, payment, inquiry)
│   ├── routers/                 # Endpointy a stránky
│   │   ├── pages.py             # HTML stránky
│   │   ├── auth.py · users.py · categories.py · words.py
│   │   ├── admin.py             # Admin panel
│   │   └── inquiry.py           # Kontaktné dopyty
│   ├── schemas/                 # Pydantic schémy
│   ├── services/                # Business logika
│   │   ├── auth_service.py · email_service.py · ai_category_service.py
│   │   ├── session_auth.py · stats_service.py · runtime.py
│   ├── static/
│   │   ├── css/fonts.css        # @font-face pre self-hostovaný Inter
│   │   ├── fonts/               # Inter woff2 (latin + latin-ext)
│   │   ├── icons/ · img/
│   │   ├── js/                  # ai_create_category.js, offline-cache.js, site-footer.js
│   │   └── sw.js                # Service Worker (PWA)
│   ├── templates/               # Jinja2 šablóny (vrátane privacy.html, terms.html)
│   └── main.py                  # Vstupný bod (lifespan, middleware, security hlavičky)
├── requirements.txt
├── runtime.txt                  # Python verzia
└── README.md
```

---

## 🌐 API Endpointy

### Autentifikácia
- `POST /api/v1/register` · `POST /api/v1/login` · `GET /api/v1/logout`
- `GET /auth/google` — Google OAuth
- `POST /api/v1/forgot-password` · `POST /api/v1/reset-password`

### Používateľ
- `GET /api/user` · `PATCH /api/user/plus` · `PATCH /api/user/dark-mode`
- `DELETE /api/user` — zmazať účet (vrátane všetkých dát)
- `GET /api/user/stats` · `GET /api/user/export` — export dát (JSON)

### Kategórie
- `GET|POST /api/v1/categories` · `GET|PUT|DELETE /api/v1/categories/{id}`
- `GET /api/v1/categories/{id}/stats`
- `POST /api/v1/categories/ai-create` — AI generovanie sady

```json
{
  "prompt": "základné slovíčka pri cestovaní",
  "language_from": "en",
  "language_to": "sk",
  "count": 25,
  "ai_provider": "groq"
}
```
> `ai_provider`: `"groq"` (predvolený) · `"gemini"` · `"claude"`

### Slovíčka
- `GET|POST /api/v1/words` · `GET|PUT|DELETE /api/v1/words/{id}`
- `PATCH /api/v1/words/{id}/knowledge`
- `POST /api/v1/words/test/start` · `POST /api/v1/words/test/submit`
- `POST /api/v1/words/import` — import z Excelu/CSV

### Verejné / stránky
- `POST /api/inquiry` — kontaktný dotaz (bez prihlásenia)
- `GET /privacy` · `GET /terms` — právne stránky (SK/EN)

### Admin (vyžaduje email v `ADMIN_EMAILS`)
- `GET /admin` — panel (HTML)
- `GET /api/admin/users` · `PATCH|DELETE /api/admin/users/{id}`
- `GET /api/admin/payments`
- `GET /api/admin/inquiries` · `PATCH|DELETE /api/admin/inquiries/{id}`

---

## ☁️ Deployment (Google Cloud Run)

```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/lexinova
gcloud run deploy lexinova --image gcr.io/PROJECT_ID/lexinova --platform managed
```

V Cloud Run nastav environment variables (viď `.env` vyššie) — najmä `DATABASE_URL`, `SECRET_KEY`, OAuth, MAIL, aspoň jeden AI kľúč, `ADMIN_EMAILS` a `DEBUG=false`.

Prvotná migrácia schémy:

```bash
gcloud run jobs execute lexinova --update-env-vars RUN_DB_CREATE_ALL=1
```

> Pri bežnom štarte sa `create_all` nespúšťa — zrýchľuje to cold start a šetrí pripojenia na Supabase.

---

## 📄 Licencia

MIT License — voľne použiteľné pre osobné aj komerčné účely.

## 👤 Autor

**Miloš Lipničan**
- GitHub: [@Lipnicanmilos](https://github.com/Lipnicanmilos)
- Email: lipnicanmilos@gmail.com

## 🤝 Prispievanie

Pull requesty sú vítané! Pre väčšie zmeny prosím najprv otvor issue.
