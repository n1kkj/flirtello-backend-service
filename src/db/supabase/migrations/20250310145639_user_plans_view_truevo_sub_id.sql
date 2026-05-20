create or replace view "public"."user_plans" with(security_invoker = true) as  SELECT up.user_id,
    up.tariff_plan_id,
    up.expired_at,
    tp.name,
    tp.duration_in_month,
    tp.tariff_info,
    tp.is_trial,
    up.truevo_subscription_id
   FROM (content.user_plans up
     JOIN content.tariff_plans tp ON ((up.tariff_plan_id = tp.id)));



