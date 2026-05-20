alter table "content"."token_packs" add column "is_highlighted" boolean default false;

alter table "content"."token_packs" add column "order" smallint;


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



