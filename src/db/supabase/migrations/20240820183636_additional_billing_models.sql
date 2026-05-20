alter table "content"."token_batches" drop constraint "token_batches_user_stats_id_fkey";
create table "content"."user_plans" (
    "user_id" uuid not null,
    "tariff_plan_id" uuid,
    "expired_at" timestamp with time zone
);
alter table "content"."user_plans" enable row level security;
alter table "content"."balances" enable row level security;
alter table "content"."tariff_plans" drop column "month_price";
alter table "content"."tariff_plans" add column "price" numeric;
alter table "content"."token_batches" drop column "user_stats_id";
alter table "content"."token_batches" add column "user_plans_id" uuid;
alter table "content"."token_packs" add column "name" text not null;
alter table "content"."transactions" add column "correlation_id" uuid;
alter table "content"."transactions" alter column "id" drop identity;
alter table "content"."transactions" add column "temp_id" uuid default gen_random_uuid();
update "content"."transactions" set "temp_id" = gen_random_uuid();
alter table "content"."transactions" drop column "id";
alter table "content"."transactions" rename column "temp_id" to "id";
alter table "content"."transactions" alter column "id" set default gen_random_uuid();
CREATE UNIQUE INDEX user_plans_pkey ON content.user_plans USING btree (user_id);
alter table "content"."user_plans" add constraint "user_plans_pkey" PRIMARY KEY using index "user_plans_pkey";
alter table "content"."token_batches" add constraint "token_batches_user_plans_id_fkey" FOREIGN KEY (user_plans_id) REFERENCES content.user_plans(user_id) not valid;
alter table "content"."token_batches" validate constraint "token_batches_user_plans_id_fkey";
alter table "content"."user_plans" add constraint "user_plans_tariff_plan_id_fkey" FOREIGN KEY (tariff_plan_id) REFERENCES content.tariff_plans(id) ON DELETE SET NULL not valid;
alter table "content"."user_plans" validate constraint "user_plans_tariff_plan_id_fkey";
grant select on table "content"."balances" to "authenticated";
grant select on table "content"."user_plans" to "authenticated";
create policy "Allow read user balances"
on "content"."balances"
as permissive
for select
to public
using ((( SELECT auth.uid() AS uid) = user_id));
create policy "Read access to user plan"
on "content"."user_plans"
as permissive
for select
to public
using ((( SELECT auth.uid() AS uid) = user_id));
REVOKE ALL ON TABLE "public"."user_stats" FROM "anon", "authenticated", "service_role";
alter table "public"."user_stats" drop constraint "user_stats_tariff_plan_id_fkey";
alter table "public"."user_stats" drop constraint "user_stats_pkey";
drop index if exists "public"."user_stats_pkey";
drop table "public"."user_stats";
create or replace view "public"."tariff_plans" as  SELECT tariff_plans.id,
    tariff_plans.name,
    tariff_plans.tokens_per_month,
    tariff_plans.duration_in_month,
    tariff_plans.currency_type_id,
    tariff_plans.price,
    tariff_plans.is_trial,
    tariff_plans.is_archived,
    tariff_plans.tariff_info
   FROM content.tariff_plans;
create or replace view "public"."user_balances" with(security_invoker = true) as  SELECT balances.id,
    balances.user_id,
    balances.currency_type_id,
    balances.balance_amount
   FROM content.balances;
create or replace view "public"."user_plans" with(security_invoker = true) as  SELECT user_plans.user_id,
    user_plans.tariff_plan_id,
    user_plans.expired_at
   FROM content.user_plans;