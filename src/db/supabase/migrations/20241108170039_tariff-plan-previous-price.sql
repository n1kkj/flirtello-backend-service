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



