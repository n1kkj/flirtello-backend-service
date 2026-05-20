alter table "content"."content_banners" add column "desktop_background" uuid;

alter table "content"."content_banners" add column "is_prioritized" boolean;

alter table "content"."content_banners" add column "mobile_background" uuid;

alter table "content"."tariff_plans" add column "created_at" timestamp with time zone default (now() AT TIME ZONE 'utc'::text);

alter table "content"."content_banners" add constraint "content_banners_desktop_background_foreign" FOREIGN KEY (desktop_background) REFERENCES content.directus_files(id) ON DELETE SET NULL not valid;

alter table "content"."content_banners" validate constraint "content_banners_desktop_background_foreign";

alter table "content"."content_banners" add constraint "content_banners_mobile_background_foreign" FOREIGN KEY (mobile_background) REFERENCES content.directus_files(id) ON DELETE SET NULL not valid;

alter table "content"."content_banners" validate constraint "content_banners_mobile_background_foreign";


CREATE OR REPLACE VIEW public.tariff_plans AS
SELECT
  tp.id,
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
FROM
  content.tariff_plans AS tp
LEFT JOIN LATERAL (
  SELECT
    price
  FROM
    content.tariff_plans AS archived_tp
  WHERE
    archived_tp.name = tp.name
    AND archived_tp.duration_in_month = tp.duration_in_month
    AND archived_tp.is_archived = true
    AND archived_tp.is_trial = false
  ORDER BY
    archived_tp.created_at DESC -- Replace with the appropriate timestamp field
  LIMIT 1
) AS latest_archived ON true
WHERE
  tp.is_trial = false AND
  tp.is_archived = false;

create or replace view "public"."user_plans" with(security_invoker = true) as  
SELECT up.user_id,
    up.tariff_plan_id,
    up.expired_at,
    tp.name,
    tp.duration_in_month,
    tp.tariff_info,
    tp.is_trial
   FROM (content.user_plans up
     JOIN content.tariff_plans tp ON ((up.tariff_plan_id = tp.id)));