create table "content"."character_configs" (
    "id" uuid not null default gen_random_uuid(),
    "public_name" text not null,
    "description" text,
    "character_id" bigint not null,
    "config" text not null,
    "path" text not null,
    "status" character varying(255) not null default 'draft'::character varying,
    "created_at" timestamp with time zone not null default (now() AT TIME ZONE 'utc'::text)
);


CREATE UNIQUE INDEX character_configs_pkey ON content.character_configs USING btree (id);

alter table "content"."character_configs" add constraint "character_configs_pkey" PRIMARY KEY using index "character_configs_pkey";


alter table "public"."channels" add column "config_id" uuid;

alter table "public"."channels" add column "stage_name" text;

alter table "public"."messages" add column "stage_name" text;


