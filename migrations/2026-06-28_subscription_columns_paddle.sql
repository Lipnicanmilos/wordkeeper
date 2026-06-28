-- LexiNova — predplatné stĺpce pre Paddle (idempotentné).
-- Nahrádza pôvodnú LS migráciu: pridá plus_* stĺpce a premenuje ls_* -> paddle_*.
-- Spustiť ručne na Supabase (SQL Editor) alebo psql — create_all nepridá stĺpce
-- do existujúcej tabuľky. Bezpečné spustiť opakovane.

ALTER TABLE users ADD COLUMN IF NOT EXISTS plus_expires_at   TIMESTAMP   NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS plus_plan         VARCHAR(20) NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS plus_status       VARCHAR(20) NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS plus_cancelled_at TIMESTAMP   NULL;

-- Premenovanie zo starých Lemon Squeezy názvov (ak existujú).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'users' AND column_name = 'ls_customer_id') THEN
        ALTER TABLE users RENAME COLUMN ls_customer_id TO paddle_customer_id;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'users' AND column_name = 'ls_subscription_id') THEN
        ALTER TABLE users RENAME COLUMN ls_subscription_id TO paddle_subscription_id;
    END IF;
END $$;

ALTER TABLE users ADD COLUMN IF NOT EXISTS paddle_customer_id     VARCHAR(64) NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS paddle_subscription_id VARCHAR(64) NULL;
