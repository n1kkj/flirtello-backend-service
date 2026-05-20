alter table "content"."landings" add column "main_button_link" character varying(255);

alter table "content"."landings" add column "main_button_text" character varying(255);

alter table "content"."landings_main_subsection" add column "image" uuid;

alter table "content"."landings_main_subsection" add constraint "landings_main_subsection_image_foreign" FOREIGN KEY (image) REFERENCES content.directus_files(id) ON DELETE SET NULL not valid;

alter table "content"."landings_main_subsection" validate constraint "landings_main_subsection_image_foreign";


