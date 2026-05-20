drop view if exists "public"."texts";

create or replace view "public"."texts" as  SELECT content_texts.id,
    content_texts.slug,
    content_texts.header,
    content_texts.text
   FROM content.content_texts;

