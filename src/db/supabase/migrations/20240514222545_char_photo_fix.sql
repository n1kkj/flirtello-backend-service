drop view if exists "public"."characters";

create or replace view "public"."characters" as  SELECT cc.id,
    cc.status,
    cc.sort,
    cc.name,
    cc.personality,
    COALESCE(array_remove(array_agg(ct.name), NULL::character varying), '{}'::character varying[]) AS traits,
    df.filename_disk AS main_photo
   FROM (((content.content_characters cc
     LEFT JOIN content.content_traits_content_characters ctc ON ((cc.id = ctc.content_characters_id)))
     LEFT JOIN content.content_traits ct ON ((ctc.content_traits_id = ct.id)))
     LEFT JOIN content.directus_files df ON ((cc.main_photo = df.id)))
  GROUP BY cc.id, df.filename_disk;



