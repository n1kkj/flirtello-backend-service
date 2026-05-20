alter table "content"."content_characters" add column "message_addendum_override" text;

alter table "content"."content_characters" add column "system_prompt_override" text;

alter table "content"."content_characters" add column "use_message_addendum_override" boolean;

alter table "content"."content_characters" add column "use_system_prompt_override" boolean;
