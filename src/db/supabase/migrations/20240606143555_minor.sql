grant insert on table "public"."users" to "supabase_auth_admin";

alter table "public"."users" alter column "settings" set not null;




