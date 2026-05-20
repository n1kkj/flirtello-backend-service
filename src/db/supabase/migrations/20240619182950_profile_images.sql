create sequence "content"."content_characters_files_id_seq";

create table "content"."content_characters_files" (
    "id" integer not null default nextval('content.content_characters_files_id_seq'::regclass),
    "content_characters_id" integer,
    "directus_files_id" uuid
);


alter sequence "content"."content_characters_files_id_seq" owned by "content"."content_characters_files"."id";

CREATE UNIQUE INDEX content_characters_files_pkey ON content.content_characters_files USING btree (id);

alter table "content"."content_characters_files" add constraint "content_characters_files_pkey" PRIMARY KEY using index "content_characters_files_pkey";

alter table "content"."content_characters_files" add constraint "content_characters_files_content_characters_id_foreign" FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON DELETE SET NULL not valid;

alter table "content"."content_characters_files" validate constraint "content_characters_files_content_characters_id_foreign";

alter table "content"."content_characters_files" add constraint "content_characters_files_directus_files_id_foreign" FOREIGN KEY (directus_files_id) REFERENCES content.directus_files(id) ON DELETE SET NULL not valid;

alter table "content"."content_characters_files" validate constraint "content_characters_files_directus_files_id_foreign";

set check_function_bodies = off;

create or replace view "public"."characters" as  SELECT cc.id,
    cc.status,
    cc.sort,
    cc.name,
    cc.public_description,
    COALESCE(array_remove(array_agg(DISTINCT ct.name), NULL::character varying), '{}'::character varying[]) AS traits,
    COALESCE(array_remove(array_agg(DISTINCT cf.name), NULL::character varying), '{}'::character varying[]) AS filters,
    COALESCE(array_remove(array_agg(DISTINCT cl.name), NULL::character varying), '{}'::character varying[]) AS locations,
    df.filename_disk AS main_photo,
    COALESCE(array_remove(array_agg(DISTINCT df2.filename_disk), NULL::character varying), '{}'::character varying[]) AS additional_files
   FROM (((((((((content.content_characters cc
     LEFT JOIN content.content_traits_content_characters ctc ON ((cc.id = ctc.content_characters_id)))
     LEFT JOIN content.content_traits ct ON ((ctc.content_traits_id = ct.id)))
     LEFT JOIN content.content_locations_content_characters clc ON ((cc.id = clc.content_characters_id)))
     LEFT JOIN content.content_locations cl ON ((clc.content_locations_id = cl.id)))
     LEFT JOIN content.content_character_filters_content_characters cfc ON ((cc.id = cfc.content_characters_id)))
     LEFT JOIN content.content_character_filters cf ON ((cfc.content_character_filters_id = cf.id)))
     LEFT JOIN content.directus_files df ON ((cc.main_photo = df.id)))
     LEFT JOIN content.content_characters_files ccf ON ((cc.id = ccf.content_characters_id)))
     LEFT JOIN content.directus_files df2 ON ((ccf.directus_files_id = df2.id)))
  GROUP BY cc.id, df.filename_disk;


