CREATE SCHEMA IF NOT EXISTS translator;
CREATE TABLE translator.translations (
    id SERIAL PRIMARY KEY,
    "key" VARCHAR NOT NULL,
    "language" VARCHAR NOT NULL,
    source_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    is_verified_by_human BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
CREATE INDEX idx_translations_key ON translator.translations ("key");
CREATE INDEX idx_translations_language ON translator.translations ("language");
CREATE INDEX idx_translations_is_verified_by_human ON translator.translations (is_verified_by_human);
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$ language 'plpgsql';
CREATE TRIGGER update_translations_updated_at BEFORE
UPDATE ON translator.translations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();