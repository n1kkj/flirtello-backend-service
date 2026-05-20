drop view if exists "public"."characters";

create or replace view "public"."characters" as  SELECT cc.id,
    cc.status,
    cc.sort,
    cc.user_created,
    cc.date_created,
    cc.user_updated,
    cc.date_updated,
    cc.name,
    cc.personality,
    COALESCE(array_remove(array_agg(DISTINCT ct.name), NULL::character varying), '{}'::character varying[]) AS traits,
    COALESCE(array_remove(array_agg(DISTINCT cf.name), NULL::character varying), '{}'::character varying[]) AS filters,
    COALESCE(array_remove(array_agg(DISTINCT cl.name), NULL::character varying), '{}'::character varying[]) AS locations,
    df.filename_disk AS main_photo
   FROM (((((((content.content_characters cc
     LEFT JOIN content.content_traits_content_characters ctc ON ((cc.id = ctc.content_characters_id)))
     LEFT JOIN content.content_traits ct ON ((ctc.content_traits_id = ct.id)))
     LEFT JOIN content.content_locations_content_characters clc ON ((cc.id = clc.content_characters_id)))
     LEFT JOIN content.content_locations cl ON ((clc.content_locations_id = cl.id)))
     LEFT JOIN content.content_character_filters_content_characters cfc ON ((cc.id = cfc.content_characters_id)))
     LEFT JOIN content.content_character_filters cf ON ((cfc.content_character_filters_id = cf.id)))
     LEFT JOIN content.directus_files df ON ((cc.main_photo = df.id)))
  GROUP BY cc.id, df.filename_disk;



