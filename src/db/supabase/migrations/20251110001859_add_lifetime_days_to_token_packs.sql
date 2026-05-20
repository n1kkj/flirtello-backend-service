-- Add lifetime_days column to content.token_packs
ALTER TABLE "content"."token_packs" ADD COLUMN "lifetime_days" INTEGER DEFAULT 9999 NOT NULL;

-- Recreate the public.token_packs view to include the new column
DROP VIEW IF EXISTS "public"."token_packs";
CREATE OR REPLACE VIEW "public"."token_packs" AS
SELECT
    id,
    amount,
    currency_type_id,
    price,
    is_archived,
    name,
    "order",
    is_highlighted,
    lifetime_days
FROM
    content.token_packs
WHERE
    (is_archived = FALSE);
