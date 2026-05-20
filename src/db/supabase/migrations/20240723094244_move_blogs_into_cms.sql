create sequence "content"."content_blogs_id_seq";

create sequence "content"."content_faq_id_seq";

create table "content"."content_blogs" (
    "id" bigint not null default nextval('content.content_blogs_id_seq'::regclass),
    "date_created" timestamp with time zone not null default now(),
    "title" character varying(255),
    "images" jsonb,
    "description" text,
    "announcement" text
);


create table "content"."content_faq" (
    "id" bigint not null default nextval('content.content_faq_id_seq'::regclass),
    "date_created" timestamp with time zone,
    "question" character varying(255),
    "answer" text,
    "order" numeric
);


alter sequence "content"."content_blogs_id_seq" owned by "content"."content_blogs"."id";

alter sequence "content"."content_faq_id_seq" owned by "content"."content_faq"."id";

CREATE UNIQUE INDEX content_blogs_pkey ON content.content_blogs USING btree (id);

CREATE UNIQUE INDEX content_faq_pkey ON content.content_faq USING btree (id);

alter table "content"."content_blogs" add constraint "content_blogs_pkey" PRIMARY KEY using index "content_blogs_pkey";

alter table "content"."content_faq" add constraint "content_faq_pkey" PRIMARY KEY using index "content_faq_pkey";


create or replace view "public"."blog" as  SELECT content_blogs.id,
    content_blogs.date_created AS created_at,
    content_blogs.title,
    content_blogs.description,
    content_blogs.images,
    content_blogs.announcement
   FROM content.content_blogs;


create or replace view "public"."faq" as  SELECT content_faq.id,
    content_faq.date_created AS created_at,
    content_faq.question,
    content_faq.answer,
    content_faq."order"
   FROM content.content_faq;



