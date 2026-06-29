-- LexiNova — denný limit AI generovania (Fáza 5, Free vs PLUS). Idempotentné.
-- Spustiť ručne na Supabase (SQL Editor) alebo psql — create_all nepridá stĺpce
-- do existujúcej tabuľky. Bezpečné spustiť opakovane.

ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_uses_date  DATE    NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_uses_count INTEGER NOT NULL DEFAULT 0;
