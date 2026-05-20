alter table "content"."character_configs" add column "background_file_id" uuid;

alter table "content"."character_configs" add column "style_name" character varying;

alter table "content"."character_configs" add constraint "character_configs_background_file_id_fkey" FOREIGN KEY (background_file_id) REFERENCES content.directus_files(id) ON UPDATE CASCADE ON DELETE SET NULL not valid;

alter table "content"."character_configs" validate constraint "character_configs_background_file_id_fkey";

alter table "content"."character_configs" add constraint "character_configs_character_id_fkey" FOREIGN KEY (character_id) REFERENCES content.content_characters(id) ON UPDATE CASCADE not valid;

alter table "content"."character_configs" validate constraint "character_configs_character_id_fkey";


