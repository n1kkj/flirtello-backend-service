create sequence "content"."content_settings_id_seq";

create table "content"."content_settings" (
    "id" integer not null default nextval('content.content_settings_id_seq'::regclass),
    "status" character varying(255) not null default 'draft'::character varying,
    "sort" integer,
    "user_created" uuid,
    "date_created" timestamp with time zone,
    "user_updated" uuid,
    "date_updated" timestamp with time zone,
    "txt_option" text,
    "bool_option" boolean,
    "name" character varying(255)
);

alter sequence "content"."content_settings_id_seq" owned by "content"."content_settings"."id";

CREATE UNIQUE INDEX content_settings_pkey ON content.content_settings USING btree (id);

alter table "content"."content_settings" add constraint "content_settings_pkey" PRIMARY KEY using index "content_settings_pkey";

alter table "content"."content_settings" add constraint "content_settings_user_created_foreign" FOREIGN KEY (user_created) REFERENCES content.directus_users(id) not valid;

alter table "content"."content_settings" validate constraint "content_settings_user_created_foreign";

alter table "content"."content_settings" add constraint "content_settings_user_updated_foreign" FOREIGN KEY (user_updated) REFERENCES content.directus_users(id) not valid;

alter table "content"."content_settings" validate constraint "content_settings_user_updated_foreign";


