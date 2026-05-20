alter table "content"."invoices" add column "callback_url" text not null;

alter table "content"."tariff_plans" add column "is_highlighted" boolean;

alter table "content"."tariff_plans" add column "order" smallint;


create or replace view "public"."tariff_plans" as  SELECT tariff_plans.id,
    tariff_plans.name,
    tariff_plans.tokens_per_month,
    tariff_plans.duration_in_month,
    tariff_plans.currency_type_id,
    tariff_plans.price,
    tariff_plans.is_trial,
    tariff_plans.is_archived,
    tariff_plans.tariff_info,
    tariff_plans.is_highlighted,
    tariff_plans."order"
   FROM content.tariff_plans
  WHERE ((tariff_plans.is_archived = false) AND (tariff_plans.is_trial = false));



