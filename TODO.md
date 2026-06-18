# TODO - WordKeeper: AI generovanie kategórií a slovíčok

## Plán (navrhnutý)
1. Preskúmať existujúce modely/schema pre Category a Word.
2. Pridať `app/services/ai_category_service.py` (volanie AI a validácia JSON).
3. Pridať request/response schema pre endpoint `ai-create`.
4. Pridať endpoint do `app/routers/categories.py` (alebo nový router):
   - `POST /api/v1/categories/ai-create`
   - vytvorí kategóriu ak neexistuje
   - vloží slová do DB (skip/update pri duplicitách)
5. Pridať konfiguráciu pre AI provider (env vars).
6. Urobiť quick test:
   - zavolať endpoint z curl/JS
   - skontrolovať DB: kategória + vložené wordy
7. Voliteľne: cache podľa (user_id + prompt_hash) kvôli nižším nákladom.

