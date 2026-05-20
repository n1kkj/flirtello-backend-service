alter table "content"."message_archive" add column "archive_id" uuid not null;

alter table "content"."message_archive" add column "archive_time" timestamp with time zone;


