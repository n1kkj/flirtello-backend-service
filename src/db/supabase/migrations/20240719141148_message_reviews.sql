create type "public"."review_types" as enum ('TEXT', 'IMAGE');

create table "content"."content_review_categories" (
    "id" uuid not null default gen_random_uuid(),
    "review_type" review_types not null,
    "category_name" text not null
);

CREATE UNIQUE INDEX content_review_categories_pkey ON content.content_review_categories USING btree (id);

alter table "content"."content_review_categories" add constraint "content_review_categories_pkey" PRIMARY KEY using index "content_review_categories_pkey";

create type "public"."message_review_status" as enum ('LIKE', 'DISLIKE', 'NEUTRAL');

alter table "public"."messages" add column "review_categories" text[];

alter table "public"."messages" add column "review_status" message_review_status not null default 'NEUTRAL'::message_review_status;

alter table "public"."messages" add column "review_text" text;

create or replace view "public"."content_review_categories" as  SELECT content_review_categories.id,
    content_review_categories.review_type,
    content_review_categories.category_name
   FROM content.content_review_categories;
