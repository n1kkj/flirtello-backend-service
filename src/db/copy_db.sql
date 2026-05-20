TRUNCATE TABLE content.balances;

INSERT INTO
  content.balances (id, currency_type_id, is_official)
VALUES
  (572450034, 1, true),
  (50805419, 1, true),
  (62811734, 2, true),
  (981206493, 3, true),
  (7361852548, 3, true),
  (331924282, 1, true);

TRUNCATE TABLE public.channels CASCADE;

TRUNCATE TABLE public.messages CASCADE;

TRUNCATE TABLE public.users CASCADE;

TRUNCATE TABLE content.clearings CASCADE;

TRUNCATE TABLE content.images_user_settings CASCADE;

TRUNCATE TABLE content.images_views CASCADE;

TRUNCATE TABLE content.invoices CASCADE;

TRUNCATE TABLE content.message_archive CASCADE;

TRUNCATE TABLE content.token_batches CASCADE;

TRUNCATE TABLE content.transactions CASCADE;

TRUNCATE TABLE content.user_plans CASCADE;
