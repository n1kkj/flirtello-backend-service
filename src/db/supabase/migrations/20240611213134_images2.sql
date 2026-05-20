alter table "content"."content_images" drop constraint "content_images_character_foreign";

alter table "content"."content_images" add column "name" character varying(255) not null;

CREATE UNIQUE INDEX content_images_name_unique ON content.content_images USING btree (name);

alter table "content"."content_images" add constraint "content_images_name_unique" UNIQUE using index "content_images_name_unique";

alter table "content"."content_images" add constraint "content_images_character_foreign" FOREIGN KEY ("character") REFERENCES content.content_characters(id) ON DELETE CASCADE not valid;

alter table "content"."content_images" validate constraint "content_images_character_foreign";

