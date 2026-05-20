alter table "content"."content_images" add column "config_id" uuid;

alter table "content"."content_images" add constraint "content_images_config_id_fkey" FOREIGN KEY (config_id) REFERENCES content.character_configs(id) ON UPDATE CASCADE not valid;

alter table "content"."content_images" validate constraint "content_images_config_id_fkey";


