alter table "content"."content_images" add column "char_name" character varying(255);

alter table "content"."content_images" add column "image_blurred" uuid;

alter table "content"."content_images" add constraint "content_images_image_blurred_foreign" FOREIGN KEY (image_blurred) REFERENCES content.directus_files(id) ON DELETE SET NULL not valid;

alter table "content"."content_images" validate constraint "content_images_image_blurred_foreign";

