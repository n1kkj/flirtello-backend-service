CREATE OR REPLACE VIEW "public"."characters" AS
SELECT
    cc.id,
    cc.status,
    cc.sort,
    cc.user_created,
    cc.date_created,
    cc.user_updated,
    cc.date_updated,
    cc.name,
    cc.personality,
    COALESCE(array_remove(array_agg(ct.name), NULL), '{}') AS traits
FROM
    content.content_characters cc
    LEFT JOIN content.content_traits_content_characters ctc ON cc.id = ctc.content_characters_id
    LEFT JOIN content.content_traits ct ON ctc.content_traits_id = ct.id
GROUP BY
    cc.id;
