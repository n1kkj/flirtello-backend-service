drop view if exists "public"."tariff_plans";

drop view if exists "public"."user_plans";

alter table "content"."tariff_plans" add column "internal_name" text;

alter table "content"."tariff_plans" alter column "tariff_info" set data type text using "tariff_info"::text;

create or replace view "public"."token_packs" as  SELECT token_packs.id,
    token_packs.amount,
    token_packs.currency_type_id,
    token_packs.price,
    token_packs.is_archived,
    token_packs.name
   FROM content.token_packs
  WHERE (token_packs.is_archived = false);

create or replace view "public"."tariff_plans" as  SELECT tariff_plans.id,
    tariff_plans.name,
    tariff_plans.tokens_per_month,
    tariff_plans.duration_in_month,
    tariff_plans.currency_type_id,
    tariff_plans.price,
    tariff_plans.is_trial,
    tariff_plans.is_archived,
    tariff_plans.tariff_info
   FROM content.tariff_plans
  WHERE ((tariff_plans.is_archived = false) AND (tariff_plans.is_trial = false));

drop view if exists "public"."paid_actions";

create or replace view "public"."paid_actions" as  SELECT paid_actions.id,
    paid_actions.price,
    paid_actions.description
   FROM content.paid_actions
  WHERE (paid_actions.is_archived = false);

create or replace view "public"."user_plans" with(security_invoker = true) as  
SELECT up.user_id,
    up.tariff_plan_id,
    up.expired_at,
    tp.name,
    tp.duration_in_month,
    tp.tariff_info
   FROM (content.user_plans up
     JOIN content.tariff_plans tp ON ((up.tariff_plan_id = tp.id)));