ALTER TABLE "content"."transactions"
ADD CONSTRAINT "transactions_id_unique" UNIQUE ("id");

ALTER TABLE "content"."transactions"
ADD CONSTRAINT "transactions_pkey" PRIMARY KEY ("id");

ALTER TABLE "content"."transactions"
ALTER COLUMN "id" SET DEFAULT gen_random_uuid();


alter table "content"."balances" add column "is_official" boolean not null default false;

alter table "content"."paid_actions" add column "description" text;

alter table "content"."transactions" alter column "source_name" drop not null;

alter table "content"."user_plans" add column "next_top_up" timestamp with time zone;

CREATE INDEX idx_additional_data_image_id ON content.transactions USING btree (((additional_data ->> 'image_id'::text)));

CREATE INDEX idx_user_id ON content.transactions USING btree (user_id);
grant USAGE on SCHEMA content to supabase_auth_admin;
grant insert on table content.transactions to supabase_auth_admin;
grant insert on table content.balances to supabase_auth_admin;
grant UPDATE on table content.balances to supabase_auth_admin;
grant SELECT on table content.balances to supabase_auth_admin;
grant insert on table content.user_plans to supabase_auth_admin;
grant SELECT on table content.tariff_plans to supabase_auth_admin;
grant SELECT on table content.currency_types to supabase_auth_admin;

grant select on table "content"."tariff_plans" to "authenticated";

grant select on table "content"."currency_types" to "authenticated";

create policy "Allow insert to authenticated"
on "content"."balances"
as permissive
for insert
to postgres, service_role, supabase_auth_admin
with check (true);


create policy "Allow select for auth"
on "content"."balances"
as permissive
for select
to supabase_auth_admin
using (true);


create policy "Allow update to authenticated"
on "content"."balances"
as permissive
for update
to postgres, supabase_auth_admin, service_role
using (true);


create policy "Allow insert to authenticated"
on "content"."user_plans"
as permissive
for insert
to postgres, service_role, supabase_auth_admin
with check (true);



drop view if exists "public"."user_balances";

create or replace view "public"."user_balances" with(security_invoker = true) as  SELECT ub.id,
    ub.user_id,
    ub.balance_amount,
    ub.currency_type_id
   FROM (content.balances ub
     JOIN content.currency_types ct ON ((ub.currency_type_id = ct.id)))
  WHERE (ct.name = 'TOKEN'::text);


create or replace view "public"."user_plans" with(security_invoker = true) as  
SELECT up.user_id,
    up.tariff_plan_id,
    up.expired_at,
    tp.name,
    tp.duration_in_month,
    tp.tariff_info
   FROM (content.user_plans up
     JOIN content.tariff_plans tp ON ((up.tariff_plan_id = tp.id)));

set check_function_bodies = off;

create or replace view "public"."paid_actions" with(security_invoker = true) as  SELECT paid_actions.id,
    paid_actions.name,
    paid_actions.price,
    paid_actions.description
   FROM content.paid_actions
  WHERE (paid_actions.is_archived = false);


create or replace view "public"."token_packs" with(security_invoker = true) as  SELECT token_packs.id,
    token_packs.amount,
    token_packs.currency_type_id,
    token_packs.price,
    token_packs.is_archived,
    token_packs.name
   FROM content.token_packs
  WHERE (token_packs.is_archived = false);


CREATE OR REPLACE FUNCTION public.handle_new_user()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$DECLARE
    -- Declare variables
    company_trial_tokens_balance_id INTEGER := 572450034;
    trial_tokens INTEGER := 5;
    user_token_balance_id INTEGER;
    first_transaction_id UUID;
    second_transaction_id UUID;
BEGIN
    -- Generate UUIDs for correlation IDs
    first_transaction_id := gen_random_uuid();
    second_transaction_id := gen_random_uuid();

    -- Log the start of the function
    -- INSERT INTO auth.trigger_log(action) VALUES ('Trigger fired with new id: ' || NEW.id);

    -- Perform the insert into the users table
    INSERT INTO public.users (id, tg_id)
    VALUES (NEW.id, 123);

    -- Log successful insert
    -- INSERT INTO auth.trigger_log(action) VALUES ('Successfully inserted new id: ' || NEW.id);

    -- Insert the user into the 'Trial' tariff plan
    INSERT INTO content.user_plans (user_id, tariff_plan_id)
    VALUES (NEW.id, (SELECT id FROM content.tariff_plans WHERE name = 'Trial'));

    -- 1. Insert balance for "TOKEN" with balance_amount = trial_tokens
    INSERT INTO content.balances (user_id, balance_amount, currency_type_id)
    VALUES (NEW.id, trial_tokens, (SELECT id FROM content.currency_types WHERE name = 'TOKEN'))
    RETURNING id INTO user_token_balance_id;

    -- 2. Insert balance for "SERVICE" with balance_amount = 0
    INSERT INTO content.balances (user_id, balance_amount, currency_type_id)
    VALUES (NEW.id, 0, (SELECT id FROM content.currency_types WHERE name = 'SERVICE'));

    -- 3. Insert balance for "USD" with balance_amount = 0
    INSERT INTO content.balances (user_id, balance_amount, currency_type_id)
    VALUES (NEW.id, 0, (SELECT id FROM content.currency_types WHERE name = 'USD'));

    -- 4. Decrease company trial token balance by trial_tokens
    UPDATE content.balances
    SET balance_amount = balance_amount - trial_tokens
    WHERE id = company_trial_tokens_balance_id;

    -- 5. Insert records into the transactions table
    INSERT INTO content.transactions (id, balance_id_from, balance_id_to, amount, transaction_type, user_id, correlation_id)
    VALUES (first_transaction_id, company_trial_tokens_balance_id, user_token_balance_id, -trial_tokens, 'BALANCE_WITHDRAW', NEW.id, second_transaction_id);

    INSERT INTO content.transactions (id, balance_id_from, balance_id_to, amount, transaction_type, user_id, correlation_id)
    VALUES (second_transaction_id, user_token_balance_id, company_trial_tokens_balance_id, trial_tokens, 'BALANCE_TOP_UP', NEW.id, first_transaction_id);

    RETURN NEW;
EXCEPTION
    WHEN OTHERS THEN
        -- Log the error
        RAISE EXCEPTION 'Error in handle_new_user: % | Role: % | User: %', SQLERRM, current_role, session_user;
END;$function$
;

create or replace view "public"."tariff_plans" with(security_invoker = true) as  SELECT tariff_plans.id,
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

INSERT INTO content.tariff_plans (name, is_trial) VALUES
('Trial', true);

INSERT INTO content.currency_types (id, name) VALUES
(1, 'TOKEN'),
(2, 'SERVICE'),
(3, 'EUR');

INSERT INTO content.balances (id, currency_type_id, is_official) VALUES
(572450034, 1, true),
(50805419, 1, true),
(62811734, 2, true),
(981206493, 3, true);

INSERT INTO content.paid_actions (name, price, description) VALUES
('MESSAGE', 0.1, 'Стоимость одного сообщения'),
('SAFE_PHOTO', 1, 'Стоимость одного фото категории "safe"'),
('QUEST_PHOTO', 2, 'Стоимость одного фото категории "quest"'),
('NUDE_PHOTO', 3, 'Стоимость одного фото категории "nude"'),
('EXPLICIT_PHOTO', 4, 'Стоимость одного фото категории "explicit"'),
('UNBLUR_SAFE_PHOTO', 1, 'Стоимость одного разблюра фото категории "safe"'),
('UNBLUR_QUEST_PHOTO', 2, 'Стоимость одного разблюра фото категории "quest"'),
('UNBLUR_NUDE_PHOTO', 3, 'Стоимость одного разблюра фото категории "nude"'),
('UNBLUR_EXPLICIT_PHOTO', 4, 'Стоимость одного разблюра фото категории "explicit"'),
('UNBLUR_PROFILE_PHOTO', 1, 'Стоимость одного разблюра фото в профиле персонажа');
