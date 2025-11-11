-- Script na pridanie stlpca last_login do tabulky users
-- Spustite tento script v PostgreSQL databáze

-- Pridanie stlpca last_login s typom TIMESTAMP WITH TIME ZONE
-- Poznámka: IF NOT EXISTS nie je podporované vo všetkých verziách PostgreSQL
-- Ak používate staršiu verziu, odstráňte "IF NOT EXISTS"
ALTER TABLE users
ADD COLUMN last_login TIMESTAMP WITH TIME ZONE;

-- Alternatívne s kontrolou existencie (pre novšie verzie PostgreSQL)
-- DO $$
-- BEGIN
--     IF NOT EXISTS (SELECT 1 FROM information_schema.columns
--                    WHERE table_name = 'users' AND column_name = 'last_login') THEN
--         ALTER TABLE users ADD COLUMN last_login TIMESTAMP WITH TIME ZONE;
--     END IF;
-- END $$;

-- Overenie, že stlpec bol pridaný
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'last_login';
