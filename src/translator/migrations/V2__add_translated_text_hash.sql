-- V2: Add translated_text_hash to translations table for bidirectional lookup.
-- This is a non-breaking change that allows finding the original text from a translated version.
-- 1. Add the new nullable column for the translated text hash.
-- It's nullable to ensure backward compatibility. Existing rows will have NULL.
ALTER TABLE translator.translations
ADD COLUMN translated_text_hash VARCHAR;
-- 2. Create an index on the new column for efficient reverse lookups.
-- A CONCURRENTLY build would be better in a high-traffic production env, but this is simpler for migrations.
CREATE INDEX ix_translator_translations_translated_text_hash ON translator.translations(translated_text_hash);