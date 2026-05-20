DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'llm_stats' AND column_name = 'llm_provider') THEN
        ALTER TABLE "content"."llm_stats" ADD COLUMN "llm_provider" text;
    END IF;
END $$;
