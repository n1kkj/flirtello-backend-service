create sequence "content"."content_blogs_files_id_seq";

create table "content"."content_blogs_files" (
    "id" integer not null default nextval('content.content_blogs_files_id_seq'::regclass),
    "content_blogs_id" bigint,
    "directus_files_id" uuid
);

drop view if exists "public"."blog";

create or replace view "public"."blogs" as  SELECT content_blogs.id,
    content_blogs.date_created AS created_at,
    content_blogs.title,
    content_blogs.description,
    content_blogs.announcement
   FROM content.content_blogs;

alter table "content"."content_blogs" drop column "images";

alter sequence "content"."content_blogs_files_id_seq" owned by "content"."content_blogs_files"."id";

CREATE UNIQUE INDEX content_blogs_files_pkey ON content.content_blogs_files USING btree (id);

alter table "content"."content_blogs_files" add constraint "content_blogs_files_pkey" PRIMARY KEY using index "content_blogs_files_pkey";

alter table "content"."content_blogs_files" add constraint "content_blogs_files_content_blogs_id_foreign" FOREIGN KEY (content_blogs_id) REFERENCES content.content_blogs(id) ON DELETE SET NULL not valid;

alter table "content"."content_blogs_files" validate constraint "content_blogs_files_content_blogs_id_foreign";

alter table "content"."content_blogs_files" add constraint "content_blogs_files_directus_files_id_foreign" FOREIGN KEY (directus_files_id) REFERENCES content.directus_files(id) ON DELETE SET NULL not valid;

alter table "content"."content_blogs_files" validate constraint "content_blogs_files_directus_files_id_foreign";
