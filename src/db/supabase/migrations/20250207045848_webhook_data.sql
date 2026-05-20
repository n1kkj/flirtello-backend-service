create table "content"."content_webhook_data" (
    "id" uuid not null default gen_random_uuid (),
    "data" jsonb not null,
    "payment_system_name" TEXT,
    "created_at" timestamp with time zone not null default (now() AT TIME ZONE 'utc'::text),
    "is_handled" boolean not null,
    "status" TEXT
);


CREATE UNIQUE INDEX content_webhook_data_pkey ON content.content_webhook_data USING btree (id);

alter table "content"."content_webhook_data" add constraint "content_webhook_data_pkey" PRIMARY KEY using index "content_webhook_data_pkey";


