drop view paid_actions;
drop view tariff_plans;
drop view token_packs;
drop view "public"."characters";
drop view user_plans;

# --------------------

create or replace view "public"."paid_actions" as  SELECT paid_actions.id,
    paid_actions.price,
    paid_actions.description
   FROM content.paid_actions
  WHERE ((paid_actions.is_archived = false) AND (paid_actions.is_public = true));

create or replace view "public"."token_packs" as  SELECT token_packs.id,
    token_packs.amount,
    token_packs.currency_type_id,
    token_packs.price,
    token_packs.is_archived,
    token_packs.name,
    token_packs."order",
    token_packs.is_highlighted
   FROM content.token_packs
  WHERE (token_packs.is_archived = false);

create or replace view "public"."tariff_plans" as  SELECT tp.id,
    tp.name,
    tp.tokens_per_month,
    tp.duration_in_month,
    tp.currency_type_id,
    tp.price,
    tp.is_trial,
    tp.is_archived,
    tp.tariff_info,
    tp.is_highlighted,
    tp."order",
    latest_archived.price AS previous_price
   FROM (content.tariff_plans tp
     LEFT JOIN LATERAL ( SELECT archived_tp.price
           FROM content.tariff_plans archived_tp
          WHERE ((archived_tp.name = tp.name) AND (archived_tp.duration_in_month = tp.duration_in_month) AND (archived_tp.is_archived = true) AND (archived_tp.is_trial = false) AND (archived_tp.price > tp.price))
          ORDER BY archived_tp.created_at
         LIMIT 1) latest_archived ON (true))
  WHERE ((tp.is_trial = false) AND (tp.is_archived = false));

create or replace view "public"."characters" as  WITH trait_agg AS (
         SELECT ctc.content_characters_id,
            array_remove(array_agg(DISTINCT ct.name), NULL::character varying) AS traits
           FROM (content.content_traits_content_characters ctc
             JOIN content.content_traits ct ON ((ctc.content_traits_id = ct.id)))
          GROUP BY ctc.content_characters_id
        ), filter_agg AS (
         SELECT cfc.content_characters_id,
            array_remove(array_agg(DISTINCT cf.name), NULL::character varying) AS filters
           FROM (content.content_character_filters_content_characters cfc
             JOIN content.content_character_filters cf ON ((cfc.content_character_filters_id = cf.id)))
          GROUP BY cfc.content_characters_id
        ), location_agg AS (
         SELECT clc.content_characters_id,
            array_remove(array_agg(DISTINCT cl.name), NULL::character varying) AS locations
           FROM (content.content_locations_content_characters clc
             JOIN content.content_locations cl ON ((clc.content_locations_id = cl.id)))
          GROUP BY clc.content_characters_id
        ), additional_files_agg AS (
         SELECT ccf.content_characters_id,
            array_remove(array_agg(DISTINCT df2.filename_disk), NULL::character varying) AS additional_files
           FROM (content.content_characters_files ccf
             JOIN content.directus_files df2 ON ((ccf.directus_files_id = df2.id)))
          GROUP BY ccf.content_characters_id
        ), profile_images_agg AS (
         SELECT cci.character_id,
            array_agg(cci.image_id) AS profile_images_ids
           FROM content.content_character_images cci
          GROUP BY cci.character_id
        ), tags_agg AS (
         SELECT cct.content_characters_id,
            jsonb_agg(jsonb_build_object('name', ct.name, 'plate_color', ct.plate_color, 'icon', ct.icon)) AS tags
           FROM (content.content_characters_content_tags cct
             JOIN content.content_tags ct ON ((cct.content_tags_id = ct.id)))
          GROUP BY cct.content_characters_id
        )
SELECT cc.id,
    cc.status,
    cc.sort,
    cc.name,
    cc.public_description,
    COALESCE(t.traits, '{}'::character varying[]) AS traits,
    COALESCE(f.filters, '{}'::character varying[]) AS filters,
    COALESCE(l.locations, '{}'::character varying[]) AS locations,
    df.filename_disk AS main_photo,
    COALESCE(a.additional_files, '{}'::character varying[]) AS profile_images,
    COALESCE(p.profile_images_ids, '{}'::uuid[]) AS profile_images_ids,
    COALESCE(tag.tags, '[]'::jsonb) AS tags,
    cc.caption,
    df_video.filename_disk AS video_preview,
    cc.onboarding_message,
    df_background.filename_disk AS background_image
   FROM ((((((((content.content_characters cc
     LEFT JOIN trait_agg t ON ((cc.id = t.content_characters_id)))
     LEFT JOIN filter_agg f ON ((cc.id = f.content_characters_id)))
     LEFT JOIN location_agg l ON ((cc.id = l.content_characters_id)))
     LEFT JOIN content.directus_files df ON ((cc.main_photo = df.id)))
     LEFT JOIN additional_files_agg a ON ((cc.id = a.content_characters_id)))
     LEFT JOIN profile_images_agg p ON ((cc.id = p.character_id)))
     LEFT JOIN tags_agg tag ON ((cc.id = tag.content_characters_id)))
     LEFT JOIN content.directus_files df_video ON ((cc.video_preview = df_video.id))
     LEFT JOIN content.directus_files df_background ON ((cc.background_image_id = df_background.id)));


create or replace view "public"."user_plans" with(security_invoker = true) as  
SELECT up.user_id,
    up.tariff_plan_id,
    up.expired_at,
    tp.name,
    tp.duration_in_month,
    tp.tariff_info,
    tp.is_trial,
    up.truevo_subscription_id
   FROM (content.user_plans up
     JOIN content.tariff_plans tp ON ((up.tariff_plan_id = tp.id)));
