create or replace view "public"."characters" as SELECT *
   FROM content.content_characters
  WHERE ((content_characters.status)::text = 'published'::text)
  ORDER BY content_characters.sort;



