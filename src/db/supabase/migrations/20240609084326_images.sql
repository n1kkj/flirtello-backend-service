create sequence "content"."content_images_path_id_seq";

create table "content"."content_images" (
    "id" uuid not null,
    "hash" character varying(255) not null,
    "character" integer not null,
    "image" uuid,
    "location" character varying(255) not null,
    "cloths" character varying(255) not null,
    "rating" character varying(255) not null,
    "behavior" character varying(255) not null,
    "prompt" text not null
);


create table "content"."content_images_path" (
    "id" integer not null default nextval('content.content_images_path_id_seq'::regclass),
    "content_images_id" uuid,
    "item" character varying(255),
    "collection" character varying(255)
);


alter sequence "content"."content_images_path_id_seq" owned by "content"."content_images_path"."id";

CREATE UNIQUE INDEX content_images_path_pkey ON content.content_images_path USING btree (id);

CREATE UNIQUE INDEX content_images_pkey ON content.content_images USING btree (id);

alter table "content"."content_images" add constraint "content_images_pkey" PRIMARY KEY using index "content_images_pkey";

alter table "content"."content_images_path" add constraint "content_images_path_pkey" PRIMARY KEY using index "content_images_path_pkey";

alter table "content"."content_images" add constraint "content_images_character_foreign" FOREIGN KEY ("character") REFERENCES content.content_characters(id) not valid;

alter table "content"."content_images" validate constraint "content_images_character_foreign";

alter table "content"."content_images" add constraint "content_images_image_foreign" FOREIGN KEY (image) REFERENCES content.directus_files(id) ON DELETE SET NULL not valid;

alter table "content"."content_images" validate constraint "content_images_image_foreign";



create table "content"."images_user_settings" (
    "id" uuid not null,
    "settings" hstore
);


create table "content"."images_views" (
    "id" uuid not null,
    "image_id" uuid not null,
    "user_id" uuid not null
);


CREATE UNIQUE INDEX images_user_settings_pkey ON content.images_user_settings USING btree (id);

CREATE UNIQUE INDEX images_views_pkey ON content.images_views USING btree (id);

alter table "content"."images_user_settings" add constraint "images_user_settings_pkey" PRIMARY KEY using index "images_user_settings_pkey";

alter table "content"."images_views" add constraint "images_views_pkey" PRIMARY KEY using index "images_views_pkey";


