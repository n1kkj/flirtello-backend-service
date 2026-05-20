create extension if not exists "hstore" with schema "extensions";
set search_path to extensions, public;

alter table "public"."users" add column "settings" hstore;


