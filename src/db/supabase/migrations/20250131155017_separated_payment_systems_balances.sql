alter table "content"."invoices" add column "payment_system_name" text;

-- Add balances for truevo payment system
INSERT INTO
  content.balances (id, currency_type_id, is_official)
VALUES
  (1129648012, 3, true);

create or replace view public.token_packs as
select
  tp.id,
  tp.amount,
  tp.currency_type_id,
  tp.price,
  tp.is_archived,
  tp.name
from
  content.token_packs tp
where
  tp.is_archived = false
order by
  tp.price;