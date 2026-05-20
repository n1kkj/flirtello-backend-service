create sequence "content"."content_texts_id_seq";

create table "content"."content_texts" (
    "id" integer not null default nextval('content.content_texts_id_seq'::regclass),
    "slug" text,
    "text" text
);


alter sequence "content"."content_texts_id_seq" owned by "content"."content_texts"."id";

CREATE UNIQUE INDEX content_texts_pkey ON content.content_texts USING btree (id);

CREATE UNIQUE INDEX content_texts_slug_unique ON content.content_texts USING btree (slug);

alter table "content"."content_texts" add constraint "content_texts_pkey" PRIMARY KEY using index "content_texts_pkey";

alter table "content"."content_texts" add constraint "content_texts_slug_unique" UNIQUE using index "content_texts_slug_unique";


alter table "public"."channels" add column "current_char_context" integer;

alter table "public"."channels" add constraint "public_channels_current_char_context_fkey" FOREIGN KEY (current_char_context) REFERENCES content.content_contexts(id) ON UPDATE CASCADE ON DELETE SET NULL not valid;

alter table "public"."channels" validate constraint "public_channels_current_char_context_fkey";

create or replace view "public"."texts" as  SELECT content_texts.id,
    content_texts.slug,
    content_texts.text
   FROM content.content_texts;



