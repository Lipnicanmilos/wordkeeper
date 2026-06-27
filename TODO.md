# LexiNova – TODO

## 🔒 Bezpečnosť & GDPR — pred komerčnou propagáciou
> Audit 2026-06-26. Zoradené podľa závažnosti.

### 🔴 Kritické (bezpečnostné diery)
- [x] **Únik e-mailov** — `/api/v1/users` len pre admina, `/api/debug/users` + `/api/debug/categories` zmazané (commit 72a3a6e3, 2026-06-26)
- [x] **Server-side validácia registrácie** (`app/routers/auth.py`) — 2026-06-27
  - Email: `EmailStr` na `UserRegister` aj `UserLogin`
  - Heslo: `password_strength_error()` (8+/veľké/malé/číslica) cez Pydantic `field_validator` na registrácii aj resete
  - `/api/v1/reset-password` prepojený na `PasswordReset` model; reset frontend dostal rovnaké 4 pravidlá; `detailMsg()` v register/login/reset rieši 422 zoznam
- [x] **Rate limiting na zneužiteľné endpointy** — 2026-06-27
  - `POST /api/inquiry` → `@limiter.limit("5/hour")` (per IP)
  - `POST /api/v1/categories/ai-create` → `@limiter.limit("10/hour")` (chráni AI kredity)
  - Frontend (site-footer.js, ai_create_category.js) ošetruje 429 zrozumiteľnou hláškou

### 🟠 GDPR / právne (nutné pre komerciu)
- [x] **AI poskytovatelia v Privacy Policy** — 2026-06-27. Sekcia „Tretie strany" (SK+EN) doplnená o Groq/Gemini/Anthropic; uvedené, že sa posiela iba text promptu + jazyky (overené v ai_category_service.py)
- [x] **Obchodné podmienky (Terms of Service)** — 2026-06-27. Nová `terms.html` (SK+EN, 12 sekcií), route `/terms`, odkazy v registrácii + pätičke. Ceny/odstúpenie sú `[DOPLNIŤ]` placeholdery — doplniť po spustení Stripe.
- [x] **Identifikácia prevádzkovateľa + retention** v Privacy — 2026-06-27. Prevádzkovateľ: Miloš Lipničan (fyzická osoba, SK) + sekcia „Doba uchovávania" (SK+EN).
- [x] **Self-hostovať Google Fonts** — 2026-06-27. Inter v20 (variabilný, latin+latin-ext) v `app/static/fonts/`, `app/static/css/fonts.css`; nahradené v 12 šablónach; MIME `font/woff2` v main.py; sw.js precache v22. Žiadne volania na Google CDN.
- [x] Export dát + zmazanie účtu — funguje správne (ORM cascade maže aj kategórie aj slovíčka)

### 🟡 Stredné (bezpečnosť / produkcia)
- [x] **Security hlavičky** — 2026-06-27. `security_headers` middleware v main.py: CSP (unsafe-inline pre inline style/script), X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, HSTS (len v prod/DEBUG=false)
- [x] **CORS zúžiť** — 2026-06-27. Origins podľa prostredia (localhost len v debug), voliteľná vlastná doména cez env `FRONTEND_ORIGIN`, explicitné metódy + hlavičky namiesto `*`
- [x] **Leak detailov chýb** — 2026-06-27. `register` aj `login` vracajú generickú hlášku; detail sa len loguje
- [ ] **Vlastná doména** — beží na `lexinova-...run.app`; pre dôveryhodnosť komerčnej služby treba vlastnú doménu (nie kód; CORS env `FRONTEND_ORIGIN` je pripravený)
- [x] `@app.on_event("startup")` → migrované na FastAPI lifespan (`asynccontextmanager`) — 2026-06-27

### ⚪ Upratovanie
- [x] Zmazané zbytočné súbory: `category_words copy.html`, `test.html`, starý `Readme` (WordKeeper), `procedure.txt` — 2026-06-27
- [ ] Pridať automatické testy + monitoring (Sentry)

### ⚙️ Nasadenie
- [x] `ADMIN_EMAILS` nastavené na Cloud Run — overené 2026-06-27, admin prístup pod lipnicanmilos@gmail.com funguje

---

## Platobná brána (Stripe) — implementovať

### Pred začatím — rozhodnúť
- [ ] Ceny a plány (napr. PLUS Monthly €4.99 / PLUS Annual €39.99?)
- [ ] Chceš nechať admin manuálny override (toggle is_plus) ako záložku?
- [ ] Trial period? (napr. 7 dní zadarmo)

### 1. Databáza — migrácia User modelu
- [ ] Pridať stĺpce do `User`:
  - `plus_expires_at` (DateTime, nullable)
  - `stripe_customer_id` (String, nullable)
  - `stripe_subscription_id` (String, nullable)
  - `plus_plan` (String: 'monthly' / 'annual', nullable)
  - `plus_cancelled_at` (DateTime, nullable)
- [ ] Spustiť migráciu (`RUN_DB_CREATE_ALL=1`)

### 2. Stripe setup
- [ ] Vytvoriť Stripe účet (test mode)
- [ ] Vytvoriť produkt + ceny v Stripe dashboarde
- [ ] Nastaviť env vars: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_MONTHLY`, `STRIPE_PRICE_ANNUAL`

### 3. Backend — nové endpointy
- [ ] `POST /api/v1/checkout` — vytvorí Stripe Checkout Session, vráti URL
- [ ] `GET /api/v1/billing/portal` — vráti URL na Stripe Customer Portal
- [ ] `POST /api/webhooks/stripe` — prijíma webhooky (podpisová verifikácia!):
  - `checkout.session.completed` → aktivuj Plus, nastav `plus_expires_at`
  - `invoice.paid` → predlž `plus_expires_at`
  - `customer.subscription.deleted` → deaktivuj Plus po expirácii
  - `invoice.payment_failed` → notifikuj emailom
- [ ] `GET /api/v1/subscription` — stav predplatného pre prihláseného užívateľa

### 4. Automatická expirácia
- [ ] Background job (APScheduler alebo Cloud Scheduler):
  - Každý deň: `plus_expires_at < now()` → `is_plus = False`

### 5. Frontend — profil stránka
- [ ] Zobraziť "Predplatné aktívne do: DD.MM.YYYY"
- [ ] Tlačidlo "Upgradovať na PLUS" → Checkout
- [ ] Tlačidlo "Spravovať predplatné" → Stripe Portal
- [ ] Banner pri expirácii

### 6. Admin stránka
- [ ] Dátum expirácie predplatného pre každého užívateľa
- [ ] Subscription status (active / cancelled / expired / payment_failed)
- [ ] Manuálny grant Plus s dátumom (+30 dní)
- [ ] MRR štatistika

---

## Ďalšie nápady / backlog
- [ ] Pridať pätičku (site-footer.js) aj na dashboard, test, repeat stránky
- [ ] Import slovíčok (Excel/CSV) — overiť že funguje
