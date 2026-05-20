alter table "content"."content_blogs" add column "meta_description" character varying(255);

alter table "content"."content_blogs" add column "meta_title" character varying(255);

alter table "content"."content_blogs" add column "slug" character varying(255);

create or replace view "public"."blogs" as  SELECT content_blogs.id,
    content_blogs.date_created AS created_at,
    content_blogs.title,
    content_blogs.description,
    content_blogs.announcement,
    content_blogs.slug,
    content_blogs.meta_title,
    content_blogs.meta_description
   FROM content.content_blogs;
