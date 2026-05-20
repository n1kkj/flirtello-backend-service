alter table "content"."content_contexts" add column "first_image" uuid DEFAULT NULL;

alter table "content"."content_contexts" add constraint "fk_first_image" FOREIGN KEY (first_image) REFERENCES content.content_images(id) ON DELETE SET NULL not valid;

alter table "content"."content_contexts" validate constraint "fk_first_image";


