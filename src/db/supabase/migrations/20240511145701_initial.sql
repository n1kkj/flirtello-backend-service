
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

CREATE SCHEMA IF NOT EXISTS "content";

ALTER SCHEMA "content" OWNER TO "postgres";

CREATE EXTENSION IF NOT EXISTS "pg_net" WITH SCHEMA "extensions";

CREATE EXTENSION IF NOT EXISTS "pgsodium" WITH SCHEMA "pgsodium";

COMMENT ON SCHEMA "public" IS 'standard public schema';

CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";

CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";

CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";

CREATE EXTENSION IF NOT EXISTS "pgjwt" WITH SCHEMA "extensions";

CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";

SET default_tablespace = '';

SET default_table_access_method = "heap";

CREATE TABLE IF NOT EXISTS "content"."content_characters" (
    "id" integer NOT NULL,
    "status" character varying(255) DEFAULT 'draft'::character varying NOT NULL,
    "sort" integer,
    "user_created" "uuid",
    "date_created" timestamp with time zone,
    "user_updated" "uuid",
    "date_updated" timestamp with time zone,
    "name" character varying(255)
);

ALTER TABLE "content"."content_characters" OWNER TO "postgres";

CREATE SEQUENCE IF NOT EXISTS "content"."content_characters_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE "content"."content_characters_id_seq" OWNER TO "postgres";

ALTER SEQUENCE "content"."content_characters_id_seq" OWNED BY "content"."content_characters"."id";

CREATE TABLE IF NOT EXISTS "content"."content_contexts" (
    "id" integer NOT NULL,
    "status" character varying(255) DEFAULT 'draft'::character varying NOT NULL,
    "sort" integer,
    "user_created" "uuid",
    "date_created" timestamp with time zone,
    "user_updated" "uuid",
    "date_updated" timestamp with time zone,
    "name" character varying(255)
);

ALTER TABLE "content"."content_contexts" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."content_contexts_content_characters" (
    "id" integer NOT NULL,
    "content_contexts_id" integer,
    "content_characters_id" integer
);

ALTER TABLE "content"."content_contexts_content_characters" OWNER TO "postgres";

CREATE SEQUENCE IF NOT EXISTS "content"."content_contexts_content_characters_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE "content"."content_contexts_content_characters_id_seq" OWNER TO "postgres";

ALTER SEQUENCE "content"."content_contexts_content_characters_id_seq" OWNED BY "content"."content_contexts_content_characters"."id";

CREATE SEQUENCE IF NOT EXISTS "content"."content_contexts_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE "content"."content_contexts_id_seq" OWNER TO "postgres";

ALTER SEQUENCE "content"."content_contexts_id_seq" OWNED BY "content"."content_contexts"."id";

CREATE TABLE IF NOT EXISTS "content"."directus_activity" (
    "id" integer NOT NULL,
    "action" character varying(45) NOT NULL,
    "user" "uuid",
    "timestamp" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "ip" character varying(50),
    "user_agent" "text",
    "collection" character varying(64) NOT NULL,
    "item" character varying(255) NOT NULL,
    "comment" "text",
    "origin" character varying(255)
);

ALTER TABLE "content"."directus_activity" OWNER TO "postgres";

CREATE SEQUENCE IF NOT EXISTS "content"."directus_activity_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE "content"."directus_activity_id_seq" OWNER TO "postgres";

ALTER SEQUENCE "content"."directus_activity_id_seq" OWNED BY "content"."directus_activity"."id";

CREATE TABLE IF NOT EXISTS "content"."directus_collections" (
    "collection" character varying(64) NOT NULL,
    "icon" character varying(30),
    "note" "text",
    "display_template" character varying(255),
    "hidden" boolean DEFAULT false NOT NULL,
    "singleton" boolean DEFAULT false NOT NULL,
    "translations" "json",
    "archive_field" character varying(64),
    "archive_app_filter" boolean DEFAULT true NOT NULL,
    "archive_value" character varying(255),
    "unarchive_value" character varying(255),
    "sort_field" character varying(64),
    "accountability" character varying(255) DEFAULT 'all'::character varying,
    "color" character varying(255),
    "item_duplication_fields" "json",
    "sort" integer,
    "group" character varying(64),
    "collapse" character varying(255) DEFAULT 'open'::character varying NOT NULL,
    "preview_url" character varying(255),
    "versioning" boolean DEFAULT false NOT NULL
);

ALTER TABLE "content"."directus_collections" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."directus_dashboards" (
    "id" "uuid" NOT NULL,
    "name" character varying(255) NOT NULL,
    "icon" character varying(30) DEFAULT 'dashboard'::character varying NOT NULL,
    "note" "text",
    "date_created" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    "user_created" "uuid",
    "color" character varying(255)
);

ALTER TABLE "content"."directus_dashboards" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."directus_extensions" (
    "enabled" boolean DEFAULT true NOT NULL,
    "id" "uuid" NOT NULL,
    "folder" character varying(255) NOT NULL,
    "source" character varying(255) NOT NULL,
    "bundle" "uuid"
);

ALTER TABLE "content"."directus_extensions" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."directus_fields" (
    "id" integer NOT NULL,
    "collection" character varying(64) NOT NULL,
    "field" character varying(64) NOT NULL,
    "special" character varying(64),
    "interface" character varying(64),
    "options" "json",
    "display" character varying(64),
    "display_options" "json",
    "readonly" boolean DEFAULT false NOT NULL,
    "hidden" boolean DEFAULT false NOT NULL,
    "sort" integer,
    "width" character varying(30) DEFAULT 'full'::character varying,
    "translations" "json",
    "note" "text",
    "conditions" "json",
    "required" boolean DEFAULT false,
    "group" character varying(64),
    "validation" "json",
    "validation_message" "text"
);

ALTER TABLE "content"."directus_fields" OWNER TO "postgres";

CREATE SEQUENCE IF NOT EXISTS "content"."directus_fields_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE "content"."directus_fields_id_seq" OWNER TO "postgres";

ALTER SEQUENCE "content"."directus_fields_id_seq" OWNED BY "content"."directus_fields"."id";

CREATE TABLE IF NOT EXISTS "content"."directus_files" (
    "id" "uuid" NOT NULL,
    "storage" character varying(255) NOT NULL,
    "filename_disk" character varying(255),
    "filename_download" character varying(255) NOT NULL,
    "title" character varying(255),
    "type" character varying(255),
    "folder" "uuid",
    "uploaded_by" "uuid",
    "uploaded_on" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "modified_by" "uuid",
    "modified_on" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "charset" character varying(50),
    "filesize" bigint,
    "width" integer,
    "height" integer,
    "duration" integer,
    "embed" character varying(200),
    "description" "text",
    "location" "text",
    "tags" "text",
    "metadata" "json",
    "focal_point_x" integer,
    "focal_point_y" integer
);

ALTER TABLE "content"."directus_files" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."directus_flows" (
    "id" "uuid" NOT NULL,
    "name" character varying(255) NOT NULL,
    "icon" character varying(30),
    "color" character varying(255),
    "description" "text",
    "status" character varying(255) DEFAULT 'active'::character varying NOT NULL,
    "trigger" character varying(255),
    "accountability" character varying(255) DEFAULT 'all'::character varying,
    "options" "json",
    "operation" "uuid",
    "date_created" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    "user_created" "uuid"
);

ALTER TABLE "content"."directus_flows" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."directus_folders" (
    "id" "uuid" NOT NULL,
    "name" character varying(255) NOT NULL,
    "parent" "uuid"
);

ALTER TABLE "content"."directus_folders" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."directus_migrations" (
    "version" character varying(255) NOT NULL,
    "name" character varying(255) NOT NULL,
    "timestamp" timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE "content"."directus_migrations" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."directus_notifications" (
    "id" integer NOT NULL,
    "timestamp" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    "status" character varying(255) DEFAULT 'inbox'::character varying,
    "recipient" "uuid" NOT NULL,
    "sender" "uuid",
    "subject" character varying(255) NOT NULL,
    "message" "text",
    "collection" character varying(64),
    "item" character varying(255)
);

ALTER TABLE "content"."directus_notifications" OWNER TO "postgres";

CREATE SEQUENCE IF NOT EXISTS "content"."directus_notifications_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE "content"."directus_notifications_id_seq" OWNER TO "postgres";

ALTER SEQUENCE "content"."directus_notifications_id_seq" OWNED BY "content"."directus_notifications"."id";

CREATE TABLE IF NOT EXISTS "content"."directus_operations" (
    "id" "uuid" NOT NULL,
    "name" character varying(255),
    "key" character varying(255) NOT NULL,
    "type" character varying(255) NOT NULL,
    "position_x" integer NOT NULL,
    "position_y" integer NOT NULL,
    "options" "json",
    "resolve" "uuid",
    "reject" "uuid",
    "flow" "uuid" NOT NULL,
    "date_created" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    "user_created" "uuid"
);

ALTER TABLE "content"."directus_operations" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."directus_panels" (
    "id" "uuid" NOT NULL,
    "dashboard" "uuid" NOT NULL,
    "name" character varying(255),
    "icon" character varying(30) DEFAULT NULL::character varying,
    "color" character varying(10),
    "show_header" boolean DEFAULT false NOT NULL,
    "note" "text",
    "type" character varying(255) NOT NULL,
    "position_x" integer NOT NULL,
    "position_y" integer NOT NULL,
    "width" integer NOT NULL,
    "height" integer NOT NULL,
    "options" "json",
    "date_created" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    "user_created" "uuid"
);

ALTER TABLE "content"."directus_panels" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."directus_permissions" (
    "id" integer NOT NULL,
    "role" "uuid",
    "collection" character varying(64) NOT NULL,
    "action" character varying(10) NOT NULL,
    "permissions" "json",
    "validation" "json",
    "presets" "json",
    "fields" "text"
);

ALTER TABLE "content"."directus_permissions" OWNER TO "postgres";

CREATE SEQUENCE IF NOT EXISTS "content"."directus_permissions_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE "content"."directus_permissions_id_seq" OWNER TO "postgres";

ALTER SEQUENCE "content"."directus_permissions_id_seq" OWNED BY "content"."directus_permissions"."id";

CREATE TABLE IF NOT EXISTS "content"."directus_presets" (
    "id" integer NOT NULL,
    "bookmark" character varying(255),
    "user" "uuid",
    "role" "uuid",
    "collection" character varying(64),
    "search" character varying(100),
    "layout" character varying(100) DEFAULT 'tabular'::character varying,
    "layout_query" "json",
    "layout_options" "json",
    "refresh_interval" integer,
    "filter" "json",
    "icon" character varying(30) DEFAULT 'bookmark'::character varying,
    "color" character varying(255)
);

ALTER TABLE "content"."directus_presets" OWNER TO "postgres";

CREATE SEQUENCE IF NOT EXISTS "content"."directus_presets_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE "content"."directus_presets_id_seq" OWNER TO "postgres";

ALTER SEQUENCE "content"."directus_presets_id_seq" OWNED BY "content"."directus_presets"."id";

CREATE TABLE IF NOT EXISTS "content"."directus_relations" (
    "id" integer NOT NULL,
    "many_collection" character varying(64) NOT NULL,
    "many_field" character varying(64) NOT NULL,
    "one_collection" character varying(64),
    "one_field" character varying(64),
    "one_collection_field" character varying(64),
    "one_allowed_collections" "text",
    "junction_field" character varying(64),
    "sort_field" character varying(64),
    "one_deselect_action" character varying(255) DEFAULT 'nullify'::character varying NOT NULL
);

ALTER TABLE "content"."directus_relations" OWNER TO "postgres";

CREATE SEQUENCE IF NOT EXISTS "content"."directus_relations_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE "content"."directus_relations_id_seq" OWNER TO "postgres";

ALTER SEQUENCE "content"."directus_relations_id_seq" OWNED BY "content"."directus_relations"."id";

CREATE TABLE IF NOT EXISTS "content"."directus_revisions" (
    "id" integer NOT NULL,
    "activity" integer NOT NULL,
    "collection" character varying(64) NOT NULL,
    "item" character varying(255) NOT NULL,
    "data" "json",
    "delta" "json",
    "parent" integer,
    "version" "uuid"
);

ALTER TABLE "content"."directus_revisions" OWNER TO "postgres";

CREATE SEQUENCE IF NOT EXISTS "content"."directus_revisions_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE "content"."directus_revisions_id_seq" OWNER TO "postgres";

ALTER SEQUENCE "content"."directus_revisions_id_seq" OWNED BY "content"."directus_revisions"."id";

CREATE TABLE IF NOT EXISTS "content"."directus_roles" (
    "id" "uuid" NOT NULL,
    "name" character varying(100) NOT NULL,
    "icon" character varying(30) DEFAULT 'supervised_user_circle'::character varying NOT NULL,
    "description" "text",
    "ip_access" "text",
    "enforce_tfa" boolean DEFAULT false NOT NULL,
    "admin_access" boolean DEFAULT false NOT NULL,
    "app_access" boolean DEFAULT true NOT NULL
);

ALTER TABLE "content"."directus_roles" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."directus_sessions" (
    "token" character varying(64) NOT NULL,
    "user" "uuid",
    "expires" timestamp with time zone NOT NULL,
    "ip" character varying(255),
    "user_agent" "text",
    "share" "uuid",
    "origin" character varying(255)
);

ALTER TABLE "content"."directus_sessions" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."directus_settings" (
    "id" integer NOT NULL,
    "project_name" character varying(100) DEFAULT 'Directus'::character varying NOT NULL,
    "project_url" character varying(255),
    "project_color" character varying(255) DEFAULT '#6644FF'::character varying NOT NULL,
    "project_logo" "uuid",
    "public_foreground" "uuid",
    "public_background" "uuid",
    "public_note" "text",
    "auth_login_attempts" integer DEFAULT 25,
    "auth_password_policy" character varying(100),
    "storage_asset_transform" character varying(7) DEFAULT 'all'::character varying,
    "storage_asset_presets" "json",
    "custom_css" "text",
    "storage_default_folder" "uuid",
    "basemaps" "json",
    "mapbox_key" character varying(255),
    "module_bar" "json",
    "project_descriptor" character varying(100),
    "default_language" character varying(255) DEFAULT 'en-US'::character varying NOT NULL,
    "custom_aspect_ratios" "json",
    "public_favicon" "uuid",
    "default_appearance" character varying(255) DEFAULT 'auto'::character varying NOT NULL,
    "default_theme_light" character varying(255),
    "theme_light_overrides" "json",
    "default_theme_dark" character varying(255),
    "theme_dark_overrides" "json",
    "report_error_url" character varying(255),
    "report_bug_url" character varying(255),
    "report_feature_url" character varying(255),
    "public_registration" boolean DEFAULT false NOT NULL,
    "public_registration_verify_email" boolean DEFAULT true NOT NULL,
    "public_registration_role" "uuid",
    "public_registration_email_filter" "json"
);

ALTER TABLE "content"."directus_settings" OWNER TO "postgres";

CREATE SEQUENCE IF NOT EXISTS "content"."directus_settings_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE "content"."directus_settings_id_seq" OWNER TO "postgres";

ALTER SEQUENCE "content"."directus_settings_id_seq" OWNED BY "content"."directus_settings"."id";

CREATE TABLE IF NOT EXISTS "content"."directus_shares" (
    "id" "uuid" NOT NULL,
    "name" character varying(255),
    "collection" character varying(64) NOT NULL,
    "item" character varying(255) NOT NULL,
    "role" "uuid",
    "password" character varying(255),
    "user_created" "uuid",
    "date_created" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    "date_start" timestamp with time zone,
    "date_end" timestamp with time zone,
    "times_used" integer DEFAULT 0,
    "max_uses" integer
);

ALTER TABLE "content"."directus_shares" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."directus_translations" (
    "id" "uuid" NOT NULL,
    "language" character varying(255) NOT NULL,
    "key" character varying(255) NOT NULL,
    "value" "text" NOT NULL
);

ALTER TABLE "content"."directus_translations" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."directus_users" (
    "id" "uuid" NOT NULL,
    "first_name" character varying(50),
    "last_name" character varying(50),
    "email" character varying(128),
    "password" character varying(255),
    "location" character varying(255),
    "title" character varying(50),
    "description" "text",
    "tags" "json",
    "avatar" "uuid",
    "language" character varying(255) DEFAULT NULL::character varying,
    "tfa_secret" character varying(255),
    "status" character varying(16) DEFAULT 'active'::character varying NOT NULL,
    "role" "uuid",
    "token" character varying(255),
    "last_access" timestamp with time zone,
    "last_page" character varying(255),
    "provider" character varying(128) DEFAULT 'default'::character varying NOT NULL,
    "external_identifier" character varying(255),
    "auth_data" "json",
    "email_notifications" boolean DEFAULT true,
    "appearance" character varying(255),
    "theme_dark" character varying(255),
    "theme_light" character varying(255),
    "theme_light_overrides" "json",
    "theme_dark_overrides" "json"
);

ALTER TABLE "content"."directus_users" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."directus_versions" (
    "id" "uuid" NOT NULL,
    "key" character varying(64) NOT NULL,
    "name" character varying(255),
    "collection" character varying(64) NOT NULL,
    "item" character varying(255) NOT NULL,
    "hash" character varying(255),
    "date_created" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    "date_updated" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    "user_created" "uuid",
    "user_updated" "uuid"
);

ALTER TABLE "content"."directus_versions" OWNER TO "postgres";

CREATE TABLE IF NOT EXISTS "content"."directus_webhooks" (
    "id" integer NOT NULL,
    "name" character varying(255) NOT NULL,
    "method" character varying(10) DEFAULT 'POST'::character varying NOT NULL,
    "url" character varying(255) NOT NULL,
    "status" character varying(10) DEFAULT 'active'::character varying NOT NULL,
    "data" boolean DEFAULT true NOT NULL,
    "actions" character varying(100) NOT NULL,
    "collections" character varying(255) NOT NULL,
    "headers" "json",
    "was_active_before_deprecation" boolean DEFAULT false NOT NULL,
    "migrated_flow" "uuid"
);

ALTER TABLE "content"."directus_webhooks" OWNER TO "postgres";

CREATE SEQUENCE IF NOT EXISTS "content"."directus_webhooks_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE "content"."directus_webhooks_id_seq" OWNER TO "postgres";

ALTER SEQUENCE "content"."directus_webhooks_id_seq" OWNED BY "content"."directus_webhooks"."id";

ALTER TABLE ONLY "content"."content_characters" ALTER COLUMN "id" SET DEFAULT "nextval"('"content"."content_characters_id_seq"'::"regclass");

ALTER TABLE ONLY "content"."content_contexts" ALTER COLUMN "id" SET DEFAULT "nextval"('"content"."content_contexts_id_seq"'::"regclass");

ALTER TABLE ONLY "content"."content_contexts_content_characters" ALTER COLUMN "id" SET DEFAULT "nextval"('"content"."content_contexts_content_characters_id_seq"'::"regclass");

ALTER TABLE ONLY "content"."directus_activity" ALTER COLUMN "id" SET DEFAULT "nextval"('"content"."directus_activity_id_seq"'::"regclass");

ALTER TABLE ONLY "content"."directus_fields" ALTER COLUMN "id" SET DEFAULT "nextval"('"content"."directus_fields_id_seq"'::"regclass");

ALTER TABLE ONLY "content"."directus_notifications" ALTER COLUMN "id" SET DEFAULT "nextval"('"content"."directus_notifications_id_seq"'::"regclass");

ALTER TABLE ONLY "content"."directus_permissions" ALTER COLUMN "id" SET DEFAULT "nextval"('"content"."directus_permissions_id_seq"'::"regclass");

ALTER TABLE ONLY "content"."directus_presets" ALTER COLUMN "id" SET DEFAULT "nextval"('"content"."directus_presets_id_seq"'::"regclass");

ALTER TABLE ONLY "content"."directus_relations" ALTER COLUMN "id" SET DEFAULT "nextval"('"content"."directus_relations_id_seq"'::"regclass");

ALTER TABLE ONLY "content"."directus_revisions" ALTER COLUMN "id" SET DEFAULT "nextval"('"content"."directus_revisions_id_seq"'::"regclass");

ALTER TABLE ONLY "content"."directus_settings" ALTER COLUMN "id" SET DEFAULT "nextval"('"content"."directus_settings_id_seq"'::"regclass");

ALTER TABLE ONLY "content"."directus_webhooks" ALTER COLUMN "id" SET DEFAULT "nextval"('"content"."directus_webhooks_id_seq"'::"regclass");

ALTER TABLE ONLY "content"."content_characters"
    ADD CONSTRAINT "content_characters_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."content_contexts_content_characters"
    ADD CONSTRAINT "content_contexts_content_characters_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."content_contexts"
    ADD CONSTRAINT "content_contexts_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_activity"
    ADD CONSTRAINT "directus_activity_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_collections"
    ADD CONSTRAINT "directus_collections_pkey" PRIMARY KEY ("collection");

ALTER TABLE ONLY "content"."directus_dashboards"
    ADD CONSTRAINT "directus_dashboards_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_extensions"
    ADD CONSTRAINT "directus_extensions_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_fields"
    ADD CONSTRAINT "directus_fields_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_files"
    ADD CONSTRAINT "directus_files_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_flows"
    ADD CONSTRAINT "directus_flows_operation_unique" UNIQUE ("operation");

ALTER TABLE ONLY "content"."directus_flows"
    ADD CONSTRAINT "directus_flows_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_folders"
    ADD CONSTRAINT "directus_folders_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_migrations"
    ADD CONSTRAINT "directus_migrations_pkey" PRIMARY KEY ("version");

ALTER TABLE ONLY "content"."directus_notifications"
    ADD CONSTRAINT "directus_notifications_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_operations"
    ADD CONSTRAINT "directus_operations_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_operations"
    ADD CONSTRAINT "directus_operations_reject_unique" UNIQUE ("reject");

ALTER TABLE ONLY "content"."directus_operations"
    ADD CONSTRAINT "directus_operations_resolve_unique" UNIQUE ("resolve");

ALTER TABLE ONLY "content"."directus_panels"
    ADD CONSTRAINT "directus_panels_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_permissions"
    ADD CONSTRAINT "directus_permissions_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_presets"
    ADD CONSTRAINT "directus_presets_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_relations"
    ADD CONSTRAINT "directus_relations_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_revisions"
    ADD CONSTRAINT "directus_revisions_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_roles"
    ADD CONSTRAINT "directus_roles_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_sessions"
    ADD CONSTRAINT "directus_sessions_pkey" PRIMARY KEY ("token");

ALTER TABLE ONLY "content"."directus_settings"
    ADD CONSTRAINT "directus_settings_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_shares"
    ADD CONSTRAINT "directus_shares_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_translations"
    ADD CONSTRAINT "directus_translations_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_users"
    ADD CONSTRAINT "directus_users_email_unique" UNIQUE ("email");

ALTER TABLE ONLY "content"."directus_users"
    ADD CONSTRAINT "directus_users_external_identifier_unique" UNIQUE ("external_identifier");

ALTER TABLE ONLY "content"."directus_users"
    ADD CONSTRAINT "directus_users_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_users"
    ADD CONSTRAINT "directus_users_token_unique" UNIQUE ("token");

ALTER TABLE ONLY "content"."directus_versions"
    ADD CONSTRAINT "directus_versions_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."directus_webhooks"
    ADD CONSTRAINT "directus_webhooks_pkey" PRIMARY KEY ("id");

ALTER TABLE ONLY "content"."content_characters"
    ADD CONSTRAINT "content_characters_user_created_foreign" FOREIGN KEY ("user_created") REFERENCES "content"."directus_users"("id");

ALTER TABLE ONLY "content"."content_characters"
    ADD CONSTRAINT "content_characters_user_updated_foreign" FOREIGN KEY ("user_updated") REFERENCES "content"."directus_users"("id");

ALTER TABLE ONLY "content"."content_contexts_content_characters"
    ADD CONSTRAINT "content_contexts_content_characters_conten__36eb00cb_foreign" FOREIGN KEY ("content_contexts_id") REFERENCES "content"."content_contexts"("id") ON DELETE SET NULL;

ALTER TABLE ONLY "content"."content_contexts_content_characters"
    ADD CONSTRAINT "content_contexts_content_characters_conten__4d6f7745_foreign" FOREIGN KEY ("content_characters_id") REFERENCES "content"."content_characters"("id") ON DELETE SET NULL;

ALTER TABLE ONLY "content"."content_contexts"
    ADD CONSTRAINT "content_contexts_user_created_foreign" FOREIGN KEY ("user_created") REFERENCES "content"."directus_users"("id");

ALTER TABLE ONLY "content"."content_contexts"
    ADD CONSTRAINT "content_contexts_user_updated_foreign" FOREIGN KEY ("user_updated") REFERENCES "content"."directus_users"("id");

ALTER TABLE ONLY "content"."directus_collections"
    ADD CONSTRAINT "directus_collections_group_foreign" FOREIGN KEY ("group") REFERENCES "content"."directus_collections"("collection");

ALTER TABLE ONLY "content"."directus_dashboards"
    ADD CONSTRAINT "directus_dashboards_user_created_foreign" FOREIGN KEY ("user_created") REFERENCES "content"."directus_users"("id") ON DELETE SET NULL;

ALTER TABLE ONLY "content"."directus_files"
    ADD CONSTRAINT "directus_files_folder_foreign" FOREIGN KEY ("folder") REFERENCES "content"."directus_folders"("id") ON DELETE SET NULL;

ALTER TABLE ONLY "content"."directus_files"
    ADD CONSTRAINT "directus_files_modified_by_foreign" FOREIGN KEY ("modified_by") REFERENCES "content"."directus_users"("id");

ALTER TABLE ONLY "content"."directus_files"
    ADD CONSTRAINT "directus_files_uploaded_by_foreign" FOREIGN KEY ("uploaded_by") REFERENCES "content"."directus_users"("id");

ALTER TABLE ONLY "content"."directus_flows"
    ADD CONSTRAINT "directus_flows_user_created_foreign" FOREIGN KEY ("user_created") REFERENCES "content"."directus_users"("id") ON DELETE SET NULL;

ALTER TABLE ONLY "content"."directus_folders"
    ADD CONSTRAINT "directus_folders_parent_foreign" FOREIGN KEY ("parent") REFERENCES "content"."directus_folders"("id");

ALTER TABLE ONLY "content"."directus_notifications"
    ADD CONSTRAINT "directus_notifications_recipient_foreign" FOREIGN KEY ("recipient") REFERENCES "content"."directus_users"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "content"."directus_notifications"
    ADD CONSTRAINT "directus_notifications_sender_foreign" FOREIGN KEY ("sender") REFERENCES "content"."directus_users"("id");

ALTER TABLE ONLY "content"."directus_operations"
    ADD CONSTRAINT "directus_operations_flow_foreign" FOREIGN KEY ("flow") REFERENCES "content"."directus_flows"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "content"."directus_operations"
    ADD CONSTRAINT "directus_operations_reject_foreign" FOREIGN KEY ("reject") REFERENCES "content"."directus_operations"("id");

ALTER TABLE ONLY "content"."directus_operations"
    ADD CONSTRAINT "directus_operations_resolve_foreign" FOREIGN KEY ("resolve") REFERENCES "content"."directus_operations"("id");

ALTER TABLE ONLY "content"."directus_operations"
    ADD CONSTRAINT "directus_operations_user_created_foreign" FOREIGN KEY ("user_created") REFERENCES "content"."directus_users"("id") ON DELETE SET NULL;

ALTER TABLE ONLY "content"."directus_panels"
    ADD CONSTRAINT "directus_panels_dashboard_foreign" FOREIGN KEY ("dashboard") REFERENCES "content"."directus_dashboards"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "content"."directus_panels"
    ADD CONSTRAINT "directus_panels_user_created_foreign" FOREIGN KEY ("user_created") REFERENCES "content"."directus_users"("id") ON DELETE SET NULL;

ALTER TABLE ONLY "content"."directus_permissions"
    ADD CONSTRAINT "directus_permissions_role_foreign" FOREIGN KEY ("role") REFERENCES "content"."directus_roles"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "content"."directus_presets"
    ADD CONSTRAINT "directus_presets_role_foreign" FOREIGN KEY ("role") REFERENCES "content"."directus_roles"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "content"."directus_presets"
    ADD CONSTRAINT "directus_presets_user_foreign" FOREIGN KEY ("user") REFERENCES "content"."directus_users"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "content"."directus_revisions"
    ADD CONSTRAINT "directus_revisions_activity_foreign" FOREIGN KEY ("activity") REFERENCES "content"."directus_activity"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "content"."directus_revisions"
    ADD CONSTRAINT "directus_revisions_parent_foreign" FOREIGN KEY ("parent") REFERENCES "content"."directus_revisions"("id");

ALTER TABLE ONLY "content"."directus_revisions"
    ADD CONSTRAINT "directus_revisions_version_foreign" FOREIGN KEY ("version") REFERENCES "content"."directus_versions"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "content"."directus_sessions"
    ADD CONSTRAINT "directus_sessions_share_foreign" FOREIGN KEY ("share") REFERENCES "content"."directus_shares"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "content"."directus_sessions"
    ADD CONSTRAINT "directus_sessions_user_foreign" FOREIGN KEY ("user") REFERENCES "content"."directus_users"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "content"."directus_settings"
    ADD CONSTRAINT "directus_settings_project_logo_foreign" FOREIGN KEY ("project_logo") REFERENCES "content"."directus_files"("id");

ALTER TABLE ONLY "content"."directus_settings"
    ADD CONSTRAINT "directus_settings_public_background_foreign" FOREIGN KEY ("public_background") REFERENCES "content"."directus_files"("id");

ALTER TABLE ONLY "content"."directus_settings"
    ADD CONSTRAINT "directus_settings_public_favicon_foreign" FOREIGN KEY ("public_favicon") REFERENCES "content"."directus_files"("id");

ALTER TABLE ONLY "content"."directus_settings"
    ADD CONSTRAINT "directus_settings_public_foreground_foreign" FOREIGN KEY ("public_foreground") REFERENCES "content"."directus_files"("id");

ALTER TABLE ONLY "content"."directus_settings"
    ADD CONSTRAINT "directus_settings_public_registration_role_foreign" FOREIGN KEY ("public_registration_role") REFERENCES "content"."directus_roles"("id") ON DELETE SET NULL;

ALTER TABLE ONLY "content"."directus_settings"
    ADD CONSTRAINT "directus_settings_storage_default_folder_foreign" FOREIGN KEY ("storage_default_folder") REFERENCES "content"."directus_folders"("id") ON DELETE SET NULL;

ALTER TABLE ONLY "content"."directus_shares"
    ADD CONSTRAINT "directus_shares_collection_foreign" FOREIGN KEY ("collection") REFERENCES "content"."directus_collections"("collection") ON DELETE CASCADE;

ALTER TABLE ONLY "content"."directus_shares"
    ADD CONSTRAINT "directus_shares_role_foreign" FOREIGN KEY ("role") REFERENCES "content"."directus_roles"("id") ON DELETE CASCADE;

ALTER TABLE ONLY "content"."directus_shares"
    ADD CONSTRAINT "directus_shares_user_created_foreign" FOREIGN KEY ("user_created") REFERENCES "content"."directus_users"("id") ON DELETE SET NULL;

ALTER TABLE ONLY "content"."directus_users"
    ADD CONSTRAINT "directus_users_role_foreign" FOREIGN KEY ("role") REFERENCES "content"."directus_roles"("id") ON DELETE SET NULL;

ALTER TABLE ONLY "content"."directus_versions"
    ADD CONSTRAINT "directus_versions_collection_foreign" FOREIGN KEY ("collection") REFERENCES "content"."directus_collections"("collection") ON DELETE CASCADE;

ALTER TABLE ONLY "content"."directus_versions"
    ADD CONSTRAINT "directus_versions_user_created_foreign" FOREIGN KEY ("user_created") REFERENCES "content"."directus_users"("id") ON DELETE SET NULL;

ALTER TABLE ONLY "content"."directus_versions"
    ADD CONSTRAINT "directus_versions_user_updated_foreign" FOREIGN KEY ("user_updated") REFERENCES "content"."directus_users"("id");

ALTER TABLE ONLY "content"."directus_webhooks"
    ADD CONSTRAINT "directus_webhooks_migrated_flow_foreign" FOREIGN KEY ("migrated_flow") REFERENCES "content"."directus_flows"("id") ON DELETE SET NULL;

ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";

GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "service_role";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "service_role";

ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "service_role";

RESET ALL;
SET session_replication_role = replica;

--
-- PostgreSQL database dump
--

-- Dumped from database version 15.1 (Ubuntu 15.1-1.pgdg20.04+1)
-- Dumped by pg_dump version 15.5 (Ubuntu 15.5-1.pgdg20.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


--
-- Data for Name: directus_roles; Type: TABLE DATA; Schema: content; Owner: postgres
--

INSERT INTO "content"."directus_roles" ("id", "name", "icon", "description", "ip_access", "enforce_tfa", "admin_access", "app_access") VALUES
	('34643dfa-93c6-49ec-b8ec-b5937ab2e9af', 'Administrator', 'verified', '$t:admin_description', NULL, false, true, true);


--
-- Data for Name: directus_users; Type: TABLE DATA; Schema: content; Owner: postgres
--

INSERT INTO "content"."directus_users" ("id", "first_name", "last_name", "email", "password", "location", "title", "description", "tags", "avatar", "language", "tfa_secret", "status", "role", "token", "last_access", "last_page", "provider", "external_identifier", "auth_data", "email_notifications", "appearance", "theme_dark", "theme_light", "theme_light_overrides", "theme_dark_overrides") VALUES
	('7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', 'tester', 'User', 'tester@deliverminds.com', '$argon2id$v=19$m=65536,t=3,p=4$Cqm6dATFwzKxHKjQy5OY9g$Ej6iZhmVk034ZsTXOXLlZbTab/o1wPYz7ARmN/B+/Bw', NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'active', '34643dfa-93c6-49ec-b8ec-b5937ab2e9af', '4jeTURqr4ma0aN8ZjUzB7Gd8-Rt-WEDs', '2024-05-11 14:39:08.373+00', '/content/content_contexts', 'default', NULL, NULL, true, NULL, NULL, NULL, NULL, NULL);


--
-- Data for Name: content_characters; Type: TABLE DATA; Schema: content; Owner: postgres
--

INSERT INTO "content"."content_characters" ("id", "status", "sort", "user_created", "date_created", "user_updated", "date_updated", "name") VALUES
	(1, 'published', NULL, '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:42:32.683+00', NULL, NULL, 'Аико');


--
-- Data for Name: content_contexts; Type: TABLE DATA; Schema: content; Owner: postgres
--

INSERT INTO "content"."content_contexts" ("id", "status", "sort", "user_created", "date_created", "user_updated", "date_updated", "name") VALUES
	(1, 'published', NULL, '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:42:32.688+00', NULL, NULL, 'Аико встретила тебя в лесу');


--
-- Data for Name: content_contexts_content_characters; Type: TABLE DATA; Schema: content; Owner: postgres
--

INSERT INTO "content"."content_contexts_content_characters" ("id", "content_contexts_id", "content_characters_id") VALUES
	(1, 1, 1);


--
-- Data for Name: directus_activity; Type: TABLE DATA; Schema: content; Owner: postgres
--

INSERT INTO "content"."directus_activity" ("id", "action", "user", "timestamp", "ip", "user_agent", "collection", "item", "comment", "origin") VALUES
	(1, 'login', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:39:08.368+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_users', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', NULL, 'http://0.0.0.0:8055'),
	(2, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:39:30.568+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '1', NULL, 'http://0.0.0.0:8055'),
	(3, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:39:30.582+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '2', NULL, 'http://0.0.0.0:8055'),
	(4, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:39:30.593+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '3', NULL, 'http://0.0.0.0:8055'),
	(5, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:39:30.603+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '4', NULL, 'http://0.0.0.0:8055'),
	(6, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:39:30.611+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '5', NULL, 'http://0.0.0.0:8055'),
	(7, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:39:30.621+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '6', NULL, 'http://0.0.0.0:8055'),
	(8, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:39:30.63+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '7', NULL, 'http://0.0.0.0:8055'),
	(9, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:39:30.638+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_collections', 'content_characters', NULL, 'http://0.0.0.0:8055'),
	(10, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:39:42.354+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '8', NULL, 'http://0.0.0.0:8055'),
	(11, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:39:59.993+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '9', NULL, 'http://0.0.0.0:8055'),
	(12, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:40:00.01+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '10', NULL, 'http://0.0.0.0:8055'),
	(13, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:40:00.027+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '11', NULL, 'http://0.0.0.0:8055'),
	(14, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:40:00.038+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '12', NULL, 'http://0.0.0.0:8055'),
	(15, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:40:00.044+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '13', NULL, 'http://0.0.0.0:8055'),
	(16, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:40:00.047+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '14', NULL, 'http://0.0.0.0:8055'),
	(17, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:40:00.052+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '15', NULL, 'http://0.0.0.0:8055'),
	(18, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:40:00.057+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_collections', 'content_contexts', NULL, 'http://0.0.0.0:8055'),
	(19, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:40:39.962+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '16', NULL, 'http://0.0.0.0:8055'),
	(20, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:41:12.701+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '17', NULL, 'http://0.0.0.0:8055'),
	(21, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:41:12.798+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '18', NULL, 'http://0.0.0.0:8055'),
	(22, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:41:12.807+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_collections', 'content_contexts_content_characters', NULL, 'http://0.0.0.0:8055'),
	(23, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:41:12.876+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '19', NULL, 'http://0.0.0.0:8055'),
	(24, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:41:12.923+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '20', NULL, 'http://0.0.0.0:8055'),
	(25, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:41:12.961+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '21', NULL, 'http://0.0.0.0:8055'),
	(26, 'update', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:41:21.879+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_fields', '17', NULL, 'http://0.0.0.0:8055'),
	(27, 'update', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:41:57.244+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_collections', 'content_contexts', NULL, 'http://0.0.0.0:8055'),
	(28, 'update', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:42:06.873+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'directus_collections', 'content_characters', NULL, 'http://0.0.0.0:8055'),
	(29, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:42:32.691+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'content_contexts', '1', NULL, 'http://0.0.0.0:8055'),
	(30, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:42:32.702+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'content_contexts_content_characters', '1', NULL, 'http://0.0.0.0:8055'),
	(31, 'create', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 14:42:32.713+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', 'content_characters', '1', NULL, 'http://0.0.0.0:8055');


--
-- Data for Name: directus_collections; Type: TABLE DATA; Schema: content; Owner: postgres
--

INSERT INTO "content"."directus_collections" ("collection", "icon", "note", "display_template", "hidden", "singleton", "translations", "archive_field", "archive_app_filter", "archive_value", "unarchive_value", "sort_field", "accountability", "color", "item_duplication_fields", "sort", "group", "collapse", "preview_url", "versioning") VALUES
	('content_contexts_content_characters', 'import_export', NULL, NULL, true, false, NULL, NULL, true, NULL, NULL, NULL, 'all', NULL, NULL, NULL, NULL, 'open', NULL, false),
	('content_contexts', NULL, NULL, '{{name}}', false, false, NULL, 'status', true, 'archived', 'draft', 'sort', 'all', NULL, NULL, NULL, NULL, 'open', NULL, false),
	('content_characters', NULL, NULL, '{{name}}', false, false, NULL, 'status', true, 'archived', 'draft', 'sort', 'all', NULL, NULL, NULL, NULL, 'open', NULL, false);


--
-- Data for Name: directus_dashboards; Type: TABLE DATA; Schema: content; Owner: postgres
--



--
-- Data for Name: directus_extensions; Type: TABLE DATA; Schema: content; Owner: postgres
--



--
-- Data for Name: directus_fields; Type: TABLE DATA; Schema: content; Owner: postgres
--

INSERT INTO "content"."directus_fields" ("id", "collection", "field", "special", "interface", "options", "display", "display_options", "readonly", "hidden", "sort", "width", "translations", "note", "conditions", "required", "group", "validation", "validation_message") VALUES
	(1, 'content_characters', 'id', NULL, 'input', NULL, NULL, NULL, true, true, 1, 'full', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(2, 'content_characters', 'status', NULL, 'select-dropdown', '{"choices":[{"text":"$t:published","value":"published","color":"var(--theme--primary)"},{"text":"$t:draft","value":"draft","color":"var(--theme--foreground)"},{"text":"$t:archived","value":"archived","color":"var(--theme--warning)"}]}', 'labels', '{"showAsDot":true,"choices":[{"text":"$t:published","value":"published","color":"var(--theme--primary)","foreground":"var(--theme--primary)","background":"var(--theme--primary-background)"},{"text":"$t:draft","value":"draft","color":"var(--theme--foreground)","foreground":"var(--theme--foreground)","background":"var(--theme--background-normal)"},{"text":"$t:archived","value":"archived","color":"var(--theme--warning)","foreground":"var(--theme--warning)","background":"var(--theme--warning-background)"}]}', false, false, 2, 'full', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(3, 'content_characters', 'sort', NULL, 'input', NULL, NULL, NULL, false, true, 3, 'full', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(4, 'content_characters', 'user_created', 'user-created', 'select-dropdown-m2o', '{"template":"{{avatar.$thumbnail}} {{first_name}} {{last_name}}"}', 'user', NULL, true, true, 4, 'half', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(5, 'content_characters', 'date_created', 'date-created', 'datetime', NULL, 'datetime', '{"relative":true}', true, true, 5, 'half', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(6, 'content_characters', 'user_updated', 'user-updated', 'select-dropdown-m2o', '{"template":"{{avatar.$thumbnail}} {{first_name}} {{last_name}}"}', 'user', NULL, true, true, 6, 'half', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(7, 'content_characters', 'date_updated', 'date-updated', 'datetime', NULL, 'datetime', '{"relative":true}', true, true, 7, 'half', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(8, 'content_characters', 'name', NULL, 'input', NULL, NULL, NULL, false, false, 8, 'full', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(9, 'content_contexts', 'id', NULL, 'input', NULL, NULL, NULL, true, true, 1, 'full', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(10, 'content_contexts', 'status', NULL, 'select-dropdown', '{"choices":[{"text":"$t:published","value":"published","color":"var(--theme--primary)"},{"text":"$t:draft","value":"draft","color":"var(--theme--foreground)"},{"text":"$t:archived","value":"archived","color":"var(--theme--warning)"}]}', 'labels', '{"showAsDot":true,"choices":[{"text":"$t:published","value":"published","color":"var(--theme--primary)","foreground":"var(--theme--primary)","background":"var(--theme--primary-background)"},{"text":"$t:draft","value":"draft","color":"var(--theme--foreground)","foreground":"var(--theme--foreground)","background":"var(--theme--background-normal)"},{"text":"$t:archived","value":"archived","color":"var(--theme--warning)","foreground":"var(--theme--warning)","background":"var(--theme--warning-background)"}]}', false, false, 2, 'full', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(11, 'content_contexts', 'sort', NULL, 'input', NULL, NULL, NULL, false, true, 3, 'full', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(12, 'content_contexts', 'user_created', 'user-created', 'select-dropdown-m2o', '{"template":"{{avatar.$thumbnail}} {{first_name}} {{last_name}}"}', 'user', NULL, true, true, 4, 'half', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(13, 'content_contexts', 'date_created', 'date-created', 'datetime', NULL, 'datetime', '{"relative":true}', true, true, 5, 'half', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(14, 'content_contexts', 'user_updated', 'user-updated', 'select-dropdown-m2o', '{"template":"{{avatar.$thumbnail}} {{first_name}} {{last_name}}"}', 'user', NULL, true, true, 6, 'half', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(15, 'content_contexts', 'date_updated', 'date-updated', 'datetime', NULL, 'datetime', '{"relative":true}', true, true, 7, 'half', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(16, 'content_contexts', 'name', NULL, 'input', NULL, NULL, NULL, false, false, 8, 'full', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(18, 'content_contexts_content_characters', 'id', NULL, NULL, NULL, NULL, NULL, false, true, 1, 'full', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(19, 'content_characters', 'usable_contexts', 'm2m', 'list-m2m', NULL, NULL, NULL, false, false, 9, 'full', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(20, 'content_contexts_content_characters', 'content_contexts_id', NULL, NULL, NULL, NULL, NULL, false, true, 2, 'full', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(21, 'content_contexts_content_characters', 'content_characters_id', NULL, NULL, NULL, NULL, NULL, false, true, 3, 'full', NULL, NULL, NULL, false, NULL, NULL, NULL),
	(17, 'content_contexts', 'used_by', 'm2m', 'list-m2m', NULL, NULL, NULL, false, false, 9, 'full', NULL, NULL, NULL, false, NULL, NULL, NULL);


--
-- Data for Name: directus_folders; Type: TABLE DATA; Schema: content; Owner: postgres
--



--
-- Data for Name: directus_files; Type: TABLE DATA; Schema: content; Owner: postgres
--



--
-- Data for Name: directus_flows; Type: TABLE DATA; Schema: content; Owner: postgres
--



--
-- Data for Name: directus_migrations; Type: TABLE DATA; Schema: content; Owner: postgres
--

INSERT INTO "content"."directus_migrations" ("version", "name", "timestamp") VALUES
	('20201028A', 'Remove Collection Foreign Keys', '2024-05-11 14:31:18.50812+00'),
	('20201029A', 'Remove System Relations', '2024-05-11 14:31:18.51073+00'),
	('20201029B', 'Remove System Collections', '2024-05-11 14:31:18.513663+00'),
	('20201029C', 'Remove System Fields', '2024-05-11 14:31:18.517504+00'),
	('20201105A', 'Add Cascade System Relations', '2024-05-11 14:31:18.533977+00'),
	('20201105B', 'Change Webhook URL Type', '2024-05-11 14:31:18.536529+00'),
	('20210225A', 'Add Relations Sort Field', '2024-05-11 14:31:18.538567+00'),
	('20210304A', 'Remove Locked Fields', '2024-05-11 14:31:18.539751+00'),
	('20210312A', 'Webhooks Collections Text', '2024-05-11 14:31:18.54205+00'),
	('20210331A', 'Add Refresh Interval', '2024-05-11 14:31:18.54302+00'),
	('20210415A', 'Make Filesize Nullable', '2024-05-11 14:31:18.546038+00'),
	('20210416A', 'Add Collections Accountability', '2024-05-11 14:31:18.547704+00'),
	('20210422A', 'Remove Files Interface', '2024-05-11 14:31:18.54864+00'),
	('20210506A', 'Rename Interfaces', '2024-05-11 14:31:18.55982+00'),
	('20210510A', 'Restructure Relations', '2024-05-11 14:31:18.567588+00'),
	('20210518A', 'Add Foreign Key Constraints', '2024-05-11 14:31:18.570706+00'),
	('20210519A', 'Add System Fk Triggers', '2024-05-11 14:31:18.580589+00'),
	('20210521A', 'Add Collections Icon Color', '2024-05-11 14:31:18.581584+00'),
	('20210525A', 'Add Insights', '2024-05-11 14:31:18.587757+00'),
	('20210608A', 'Add Deep Clone Config', '2024-05-11 14:31:18.58866+00'),
	('20210626A', 'Change Filesize Bigint', '2024-05-11 14:31:18.593604+00'),
	('20210716A', 'Add Conditions to Fields', '2024-05-11 14:31:18.59467+00'),
	('20210721A', 'Add Default Folder', '2024-05-11 14:31:18.596713+00'),
	('20210802A', 'Replace Groups', '2024-05-11 14:31:18.598509+00'),
	('20210803A', 'Add Required to Fields', '2024-05-11 14:31:18.599562+00'),
	('20210805A', 'Update Groups', '2024-05-11 14:31:18.601076+00'),
	('20210805B', 'Change Image Metadata Structure', '2024-05-11 14:31:18.602496+00'),
	('20210811A', 'Add Geometry Config', '2024-05-11 14:31:18.603478+00'),
	('20210831A', 'Remove Limit Column', '2024-05-11 14:31:18.604491+00'),
	('20210903A', 'Add Auth Provider', '2024-05-11 14:31:18.61028+00'),
	('20210907A', 'Webhooks Collections Not Null', '2024-05-11 14:31:18.613238+00'),
	('20210910A', 'Move Module Setup', '2024-05-11 14:31:18.615182+00'),
	('20210920A', 'Webhooks URL Not Null', '2024-05-11 14:31:18.618149+00'),
	('20210924A', 'Add Collection Organization', '2024-05-11 14:31:18.620174+00'),
	('20210927A', 'Replace Fields Group', '2024-05-11 14:31:18.623387+00'),
	('20210927B', 'Replace M2M Interface', '2024-05-11 14:31:18.624314+00'),
	('20210929A', 'Rename Login Action', '2024-05-11 14:31:18.625141+00'),
	('20211007A', 'Update Presets', '2024-05-11 14:31:18.627729+00'),
	('20211009A', 'Add Auth Data', '2024-05-11 14:31:18.62881+00'),
	('20211016A', 'Add Webhook Headers', '2024-05-11 14:31:18.62983+00'),
	('20211103A', 'Set Unique to User Token', '2024-05-11 14:31:18.631844+00'),
	('20211103B', 'Update Special Geometry', '2024-05-11 14:31:18.632813+00'),
	('20211104A', 'Remove Collections Listing', '2024-05-11 14:31:18.633828+00'),
	('20211118A', 'Add Notifications', '2024-05-11 14:31:18.638445+00'),
	('20211211A', 'Add Shares', '2024-05-11 14:31:18.644649+00'),
	('20211230A', 'Add Project Descriptor', '2024-05-11 14:31:18.645754+00'),
	('20220303A', 'Remove Default Project Color', '2024-05-11 14:31:18.648765+00'),
	('20220308A', 'Add Bookmark Icon and Color', '2024-05-11 14:31:18.649839+00'),
	('20220314A', 'Add Translation Strings', '2024-05-11 14:31:18.650857+00'),
	('20220322A', 'Rename Field Typecast Flags', '2024-05-11 14:31:18.652496+00'),
	('20220323A', 'Add Field Validation', '2024-05-11 14:31:18.65354+00'),
	('20220325A', 'Fix Typecast Flags', '2024-05-11 14:31:18.655082+00'),
	('20220325B', 'Add Default Language', '2024-05-11 14:31:18.658347+00'),
	('20220402A', 'Remove Default Value Panel Icon', '2024-05-11 14:31:18.661367+00'),
	('20220429A', 'Add Flows', '2024-05-11 14:31:18.673248+00'),
	('20220429B', 'Add Color to Insights Icon', '2024-05-11 14:31:18.674242+00'),
	('20220429C', 'Drop Non Null From IP of Activity', '2024-05-11 14:31:18.675157+00'),
	('20220429D', 'Drop Non Null From Sender of Notifications', '2024-05-11 14:31:18.676024+00'),
	('20220614A', 'Rename Hook Trigger to Event', '2024-05-11 14:31:18.676788+00'),
	('20220801A', 'Update Notifications Timestamp Column', '2024-05-11 14:31:18.679608+00'),
	('20220802A', 'Add Custom Aspect Ratios', '2024-05-11 14:31:18.680649+00'),
	('20220826A', 'Add Origin to Accountability', '2024-05-11 14:31:18.682022+00'),
	('20230401A', 'Update Material Icons', '2024-05-11 14:31:18.684925+00'),
	('20230525A', 'Add Preview Settings', '2024-05-11 14:31:18.68596+00'),
	('20230526A', 'Migrate Translation Strings', '2024-05-11 14:31:18.689942+00'),
	('20230721A', 'Require Shares Fields', '2024-05-11 14:31:18.691972+00'),
	('20230823A', 'Add Content Versioning', '2024-05-11 14:31:18.697846+00'),
	('20230927A', 'Themes', '2024-05-11 14:31:18.703678+00'),
	('20231009A', 'Update CSV Fields to Text', '2024-05-11 14:31:18.705185+00'),
	('20231009B', 'Update Panel Options', '2024-05-11 14:31:18.706044+00'),
	('20231010A', 'Add Extensions', '2024-05-11 14:31:18.707621+00'),
	('20231215A', 'Add Focalpoints', '2024-05-11 14:31:18.708557+00'),
	('20240122A', 'Add Report URL Fields', '2024-05-11 14:31:18.70955+00'),
	('20240204A', 'Marketplace', '2024-05-11 14:31:18.718708+00'),
	('20240305A', 'Change Useragent Type', '2024-05-11 14:31:18.722062+00'),
	('20240311A', 'Deprecate Webhooks', '2024-05-11 14:31:18.725815+00'),
	('20240422A', 'Public Registration', '2024-05-11 14:31:18.727616+00');


--
-- Data for Name: directus_notifications; Type: TABLE DATA; Schema: content; Owner: postgres
--



--
-- Data for Name: directus_operations; Type: TABLE DATA; Schema: content; Owner: postgres
--



--
-- Data for Name: directus_panels; Type: TABLE DATA; Schema: content; Owner: postgres
--



--
-- Data for Name: directus_permissions; Type: TABLE DATA; Schema: content; Owner: postgres
--



--
-- Data for Name: directus_presets; Type: TABLE DATA; Schema: content; Owner: postgres
--

INSERT INTO "content"."directus_presets" ("id", "bookmark", "user", "role", "collection", "search", "layout", "layout_query", "layout_options", "refresh_interval", "filter", "icon", "color") VALUES
	(1, NULL, '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', NULL, 'content_contexts', NULL, NULL, '{"tabular":{"fields":["name","status","used_by"]}}', '{"tabular":{"widths":{"name":442}}}', NULL, NULL, 'bookmark', NULL);


--
-- Data for Name: directus_relations; Type: TABLE DATA; Schema: content; Owner: postgres
--

INSERT INTO "content"."directus_relations" ("id", "many_collection", "many_field", "one_collection", "one_field", "one_collection_field", "one_allowed_collections", "junction_field", "sort_field", "one_deselect_action") VALUES
	(1, 'content_characters', 'user_created', 'directus_users', NULL, NULL, NULL, NULL, NULL, 'nullify'),
	(2, 'content_characters', 'user_updated', 'directus_users', NULL, NULL, NULL, NULL, NULL, 'nullify'),
	(3, 'content_contexts', 'user_created', 'directus_users', NULL, NULL, NULL, NULL, NULL, 'nullify'),
	(4, 'content_contexts', 'user_updated', 'directus_users', NULL, NULL, NULL, NULL, NULL, 'nullify'),
	(5, 'content_contexts_content_characters', 'content_characters_id', 'content_characters', 'usable_contexts', NULL, NULL, 'content_contexts_id', NULL, 'nullify'),
	(6, 'content_contexts_content_characters', 'content_contexts_id', 'content_contexts', 'used_by', NULL, NULL, 'content_characters_id', NULL, 'nullify');


--
-- Data for Name: directus_versions; Type: TABLE DATA; Schema: content; Owner: postgres
--



--
-- Data for Name: directus_revisions; Type: TABLE DATA; Schema: content; Owner: postgres
--

INSERT INTO "content"."directus_revisions" ("id", "activity", "collection", "item", "data", "delta", "parent", "version") VALUES
	(1, 2, 'directus_fields', '1', '{"sort":1,"hidden":true,"interface":"input","readonly":true,"field":"id","collection":"content_characters"}', '{"sort":1,"hidden":true,"interface":"input","readonly":true,"field":"id","collection":"content_characters"}', NULL, NULL),
	(2, 3, 'directus_fields', '2', '{"sort":2,"width":"full","options":{"choices":[{"text":"$t:published","value":"published","color":"var(--theme--primary)"},{"text":"$t:draft","value":"draft","color":"var(--theme--foreground)"},{"text":"$t:archived","value":"archived","color":"var(--theme--warning)"}]},"interface":"select-dropdown","display":"labels","display_options":{"showAsDot":true,"choices":[{"text":"$t:published","value":"published","color":"var(--theme--primary)","foreground":"var(--theme--primary)","background":"var(--theme--primary-background)"},{"text":"$t:draft","value":"draft","color":"var(--theme--foreground)","foreground":"var(--theme--foreground)","background":"var(--theme--background-normal)"},{"text":"$t:archived","value":"archived","color":"var(--theme--warning)","foreground":"var(--theme--warning)","background":"var(--theme--warning-background)"}]},"field":"status","collection":"content_characters"}', '{"sort":2,"width":"full","options":{"choices":[{"text":"$t:published","value":"published","color":"var(--theme--primary)"},{"text":"$t:draft","value":"draft","color":"var(--theme--foreground)"},{"text":"$t:archived","value":"archived","color":"var(--theme--warning)"}]},"interface":"select-dropdown","display":"labels","display_options":{"showAsDot":true,"choices":[{"text":"$t:published","value":"published","color":"var(--theme--primary)","foreground":"var(--theme--primary)","background":"var(--theme--primary-background)"},{"text":"$t:draft","value":"draft","color":"var(--theme--foreground)","foreground":"var(--theme--foreground)","background":"var(--theme--background-normal)"},{"text":"$t:archived","value":"archived","color":"var(--theme--warning)","foreground":"var(--theme--warning)","background":"var(--theme--warning-background)"}]},"field":"status","collection":"content_characters"}', NULL, NULL),
	(3, 4, 'directus_fields', '3', '{"sort":3,"interface":"input","hidden":true,"field":"sort","collection":"content_characters"}', '{"sort":3,"interface":"input","hidden":true,"field":"sort","collection":"content_characters"}', NULL, NULL),
	(4, 5, 'directus_fields', '4', '{"sort":4,"special":["user-created"],"interface":"select-dropdown-m2o","options":{"template":"{{avatar.$thumbnail}} {{first_name}} {{last_name}}"},"display":"user","readonly":true,"hidden":true,"width":"half","field":"user_created","collection":"content_characters"}', '{"sort":4,"special":["user-created"],"interface":"select-dropdown-m2o","options":{"template":"{{avatar.$thumbnail}} {{first_name}} {{last_name}}"},"display":"user","readonly":true,"hidden":true,"width":"half","field":"user_created","collection":"content_characters"}', NULL, NULL),
	(5, 6, 'directus_fields', '5', '{"sort":5,"special":["date-created"],"interface":"datetime","readonly":true,"hidden":true,"width":"half","display":"datetime","display_options":{"relative":true},"field":"date_created","collection":"content_characters"}', '{"sort":5,"special":["date-created"],"interface":"datetime","readonly":true,"hidden":true,"width":"half","display":"datetime","display_options":{"relative":true},"field":"date_created","collection":"content_characters"}', NULL, NULL),
	(6, 7, 'directus_fields', '6', '{"sort":6,"special":["user-updated"],"interface":"select-dropdown-m2o","options":{"template":"{{avatar.$thumbnail}} {{first_name}} {{last_name}}"},"display":"user","readonly":true,"hidden":true,"width":"half","field":"user_updated","collection":"content_characters"}', '{"sort":6,"special":["user-updated"],"interface":"select-dropdown-m2o","options":{"template":"{{avatar.$thumbnail}} {{first_name}} {{last_name}}"},"display":"user","readonly":true,"hidden":true,"width":"half","field":"user_updated","collection":"content_characters"}', NULL, NULL),
	(7, 8, 'directus_fields', '7', '{"sort":7,"special":["date-updated"],"interface":"datetime","readonly":true,"hidden":true,"width":"half","display":"datetime","display_options":{"relative":true},"field":"date_updated","collection":"content_characters"}', '{"sort":7,"special":["date-updated"],"interface":"datetime","readonly":true,"hidden":true,"width":"half","display":"datetime","display_options":{"relative":true},"field":"date_updated","collection":"content_characters"}', NULL, NULL),
	(8, 9, 'directus_collections', 'content_characters', '{"sort_field":"sort","archive_field":"status","archive_value":"archived","unarchive_value":"draft","singleton":false,"collection":"content_characters"}', '{"sort_field":"sort","archive_field":"status","archive_value":"archived","unarchive_value":"draft","singleton":false,"collection":"content_characters"}', NULL, NULL),
	(9, 10, 'directus_fields', '8', '{"sort":8,"interface":"input","special":null,"collection":"content_characters","field":"name"}', '{"sort":8,"interface":"input","special":null,"collection":"content_characters","field":"name"}', NULL, NULL),
	(10, 11, 'directus_fields', '9', '{"sort":1,"hidden":true,"interface":"input","readonly":true,"field":"id","collection":"content_contexts"}', '{"sort":1,"hidden":true,"interface":"input","readonly":true,"field":"id","collection":"content_contexts"}', NULL, NULL),
	(11, 12, 'directus_fields', '10', '{"sort":2,"width":"full","options":{"choices":[{"text":"$t:published","value":"published","color":"var(--theme--primary)"},{"text":"$t:draft","value":"draft","color":"var(--theme--foreground)"},{"text":"$t:archived","value":"archived","color":"var(--theme--warning)"}]},"interface":"select-dropdown","display":"labels","display_options":{"showAsDot":true,"choices":[{"text":"$t:published","value":"published","color":"var(--theme--primary)","foreground":"var(--theme--primary)","background":"var(--theme--primary-background)"},{"text":"$t:draft","value":"draft","color":"var(--theme--foreground)","foreground":"var(--theme--foreground)","background":"var(--theme--background-normal)"},{"text":"$t:archived","value":"archived","color":"var(--theme--warning)","foreground":"var(--theme--warning)","background":"var(--theme--warning-background)"}]},"field":"status","collection":"content_contexts"}', '{"sort":2,"width":"full","options":{"choices":[{"text":"$t:published","value":"published","color":"var(--theme--primary)"},{"text":"$t:draft","value":"draft","color":"var(--theme--foreground)"},{"text":"$t:archived","value":"archived","color":"var(--theme--warning)"}]},"interface":"select-dropdown","display":"labels","display_options":{"showAsDot":true,"choices":[{"text":"$t:published","value":"published","color":"var(--theme--primary)","foreground":"var(--theme--primary)","background":"var(--theme--primary-background)"},{"text":"$t:draft","value":"draft","color":"var(--theme--foreground)","foreground":"var(--theme--foreground)","background":"var(--theme--background-normal)"},{"text":"$t:archived","value":"archived","color":"var(--theme--warning)","foreground":"var(--theme--warning)","background":"var(--theme--warning-background)"}]},"field":"status","collection":"content_contexts"}', NULL, NULL),
	(12, 13, 'directus_fields', '11', '{"sort":3,"interface":"input","hidden":true,"field":"sort","collection":"content_contexts"}', '{"sort":3,"interface":"input","hidden":true,"field":"sort","collection":"content_contexts"}', NULL, NULL),
	(19, 20, 'directus_fields', '17', '{"sort":9,"special":["m2m"],"collection":"content_contexts","field":"used_by"}', '{"sort":9,"special":["m2m"],"collection":"content_contexts","field":"used_by"}', NULL, NULL),
	(23, 24, 'directus_fields', '20', '{"sort":2,"hidden":true,"collection":"content_contexts_content_characters","field":"content_contexts_id"}', '{"sort":2,"hidden":true,"collection":"content_contexts_content_characters","field":"content_contexts_id"}', NULL, NULL),
	(13, 14, 'directus_fields', '12', '{"sort":4,"special":["user-created"],"interface":"select-dropdown-m2o","options":{"template":"{{avatar.$thumbnail}} {{first_name}} {{last_name}}"},"display":"user","readonly":true,"hidden":true,"width":"half","field":"user_created","collection":"content_contexts"}', '{"sort":4,"special":["user-created"],"interface":"select-dropdown-m2o","options":{"template":"{{avatar.$thumbnail}} {{first_name}} {{last_name}}"},"display":"user","readonly":true,"hidden":true,"width":"half","field":"user_created","collection":"content_contexts"}', NULL, NULL),
	(14, 15, 'directus_fields', '13', '{"sort":5,"special":["date-created"],"interface":"datetime","readonly":true,"hidden":true,"width":"half","display":"datetime","display_options":{"relative":true},"field":"date_created","collection":"content_contexts"}', '{"sort":5,"special":["date-created"],"interface":"datetime","readonly":true,"hidden":true,"width":"half","display":"datetime","display_options":{"relative":true},"field":"date_created","collection":"content_contexts"}', NULL, NULL),
	(15, 16, 'directus_fields', '14', '{"sort":6,"special":["user-updated"],"interface":"select-dropdown-m2o","options":{"template":"{{avatar.$thumbnail}} {{first_name}} {{last_name}}"},"display":"user","readonly":true,"hidden":true,"width":"half","field":"user_updated","collection":"content_contexts"}', '{"sort":6,"special":["user-updated"],"interface":"select-dropdown-m2o","options":{"template":"{{avatar.$thumbnail}} {{first_name}} {{last_name}}"},"display":"user","readonly":true,"hidden":true,"width":"half","field":"user_updated","collection":"content_contexts"}', NULL, NULL),
	(16, 17, 'directus_fields', '15', '{"sort":7,"special":["date-updated"],"interface":"datetime","readonly":true,"hidden":true,"width":"half","display":"datetime","display_options":{"relative":true},"field":"date_updated","collection":"content_contexts"}', '{"sort":7,"special":["date-updated"],"interface":"datetime","readonly":true,"hidden":true,"width":"half","display":"datetime","display_options":{"relative":true},"field":"date_updated","collection":"content_contexts"}', NULL, NULL),
	(17, 18, 'directus_collections', 'content_contexts', '{"sort_field":"sort","archive_field":"status","archive_value":"archived","unarchive_value":"draft","singleton":false,"collection":"content_contexts"}', '{"sort_field":"sort","archive_field":"status","archive_value":"archived","unarchive_value":"draft","singleton":false,"collection":"content_contexts"}', NULL, NULL),
	(18, 19, 'directus_fields', '16', '{"sort":8,"interface":"input","special":null,"collection":"content_contexts","field":"name"}', '{"sort":8,"interface":"input","special":null,"collection":"content_contexts","field":"name"}', NULL, NULL),
	(20, 21, 'directus_fields', '18', '{"sort":1,"hidden":true,"field":"id","collection":"content_contexts_content_characters"}', '{"sort":1,"hidden":true,"field":"id","collection":"content_contexts_content_characters"}', NULL, NULL),
	(21, 22, 'directus_collections', 'content_contexts_content_characters', '{"hidden":true,"icon":"import_export","collection":"content_contexts_content_characters"}', '{"hidden":true,"icon":"import_export","collection":"content_contexts_content_characters"}', NULL, NULL),
	(22, 23, 'directus_fields', '19', '{"sort":9,"special":["m2m"],"interface":"list-m2m","collection":"content_characters","field":"usable_contexts"}', '{"sort":9,"special":["m2m"],"interface":"list-m2m","collection":"content_characters","field":"usable_contexts"}', NULL, NULL),
	(24, 25, 'directus_fields', '21', '{"sort":3,"hidden":true,"collection":"content_contexts_content_characters","field":"content_characters_id"}', '{"sort":3,"hidden":true,"collection":"content_contexts_content_characters","field":"content_characters_id"}', NULL, NULL),
	(25, 26, 'directus_fields', '17', '{"id":17,"collection":"content_contexts","field":"used_by","special":["m2m"],"interface":"list-m2m","options":null,"display":null,"display_options":null,"readonly":false,"hidden":false,"sort":9,"width":"full","translations":null,"note":null,"conditions":null,"required":false,"group":null,"validation":null,"validation_message":null}', '{"collection":"content_contexts","field":"used_by","interface":"list-m2m"}', NULL, NULL),
	(26, 27, 'directus_collections', 'content_contexts', '{"collection":"content_contexts","icon":null,"note":null,"display_template":"{{name}}","hidden":false,"singleton":false,"translations":null,"archive_field":"status","archive_app_filter":true,"archive_value":"archived","unarchive_value":"draft","sort_field":"sort","accountability":"all","color":null,"item_duplication_fields":null,"sort":null,"group":null,"collapse":"open","preview_url":null,"versioning":false}', '{"display_template":"{{name}}"}', NULL, NULL),
	(27, 28, 'directus_collections', 'content_characters', '{"collection":"content_characters","icon":null,"note":null,"display_template":"{{name}}","hidden":false,"singleton":false,"translations":null,"archive_field":"status","archive_app_filter":true,"archive_value":"archived","unarchive_value":"draft","sort_field":"sort","accountability":"all","color":null,"item_duplication_fields":null,"sort":null,"group":null,"collapse":"open","preview_url":null,"versioning":false}', '{"display_template":"{{name}}"}', NULL, NULL),
	(28, 29, 'content_contexts', '1', '{"status":"published","name":"Аико встретила тебя в лесу"}', '{"status":"published","name":"Аико встретила тебя в лесу"}', 29, NULL),
	(30, 31, 'content_characters', '1', '{"status":"published","name":"Аико","usable_contexts":{"create":[{"content_contexts_id":{"status":"published","name":"Аико встретила тебя в лесу"}}],"update":[],"delete":[]}}', '{"status":"published","name":"Аико","usable_contexts":{"create":[{"content_contexts_id":{"status":"published","name":"Аико встретила тебя в лесу"}}],"update":[],"delete":[]}}', NULL, NULL),
	(29, 30, 'content_contexts_content_characters', '1', '{"content_contexts_id":{"status":"published","name":"Аико встретила тебя в лесу"},"content_characters_id":1}', '{"content_contexts_id":{"status":"published","name":"Аико встретила тебя в лесу"},"content_characters_id":1}', 30, NULL);


--
-- Data for Name: directus_shares; Type: TABLE DATA; Schema: content; Owner: postgres
--



--
-- Data for Name: directus_sessions; Type: TABLE DATA; Schema: content; Owner: postgres
--

INSERT INTO "content"."directus_sessions" ("token", "user", "expires", "ip", "user_agent", "share", "origin") VALUES
	('nFEbK9csZ4_A8kdwRW8L36dittbK06eEbxV6uVIVMAIqj53XWb_RtVWB_C0yROTW', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-18 14:39:08.357+00', '127.0.0.1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0', NULL, 'http://0.0.0.0:8055');


--
-- Data for Name: directus_settings; Type: TABLE DATA; Schema: content; Owner: postgres
--



--
-- Data for Name: directus_translations; Type: TABLE DATA; Schema: content; Owner: postgres
--



--
-- Data for Name: directus_webhooks; Type: TABLE DATA; Schema: content; Owner: postgres
--



--
-- Data for Name: key; Type: TABLE DATA; Schema: pgsodium; Owner: supabase_admin
--



--
-- Data for Name: buckets; Type: TABLE DATA; Schema: storage; Owner: supabase_storage_admin
--



--
-- Data for Name: objects; Type: TABLE DATA; Schema: storage; Owner: supabase_storage_admin
--



--
-- Data for Name: s3_multipart_uploads; Type: TABLE DATA; Schema: storage; Owner: supabase_storage_admin
--



--
-- Data for Name: s3_multipart_uploads_parts; Type: TABLE DATA; Schema: storage; Owner: supabase_storage_admin
--



--
-- Data for Name: hooks; Type: TABLE DATA; Schema: supabase_functions; Owner: supabase_functions_admin
--



--
-- Data for Name: secrets; Type: TABLE DATA; Schema: vault; Owner: supabase_admin
--



--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE SET; Schema: auth; Owner: supabase_auth_admin
--

SELECT pg_catalog.setval('"auth"."refresh_tokens_id_seq"', 1, false);


--
-- Name: content_characters_id_seq; Type: SEQUENCE SET; Schema: content; Owner: postgres
--

SELECT pg_catalog.setval('"content"."content_characters_id_seq"', 1, true);


--
-- Name: content_contexts_content_characters_id_seq; Type: SEQUENCE SET; Schema: content; Owner: postgres
--

SELECT pg_catalog.setval('"content"."content_contexts_content_characters_id_seq"', 1, true);


--
-- Name: content_contexts_id_seq; Type: SEQUENCE SET; Schema: content; Owner: postgres
--

SELECT pg_catalog.setval('"content"."content_contexts_id_seq"', 1, true);


--
-- Name: directus_activity_id_seq; Type: SEQUENCE SET; Schema: content; Owner: postgres
--

SELECT pg_catalog.setval('"content"."directus_activity_id_seq"', 31, true);


--
-- Name: directus_fields_id_seq; Type: SEQUENCE SET; Schema: content; Owner: postgres
--

SELECT pg_catalog.setval('"content"."directus_fields_id_seq"', 21, true);


--
-- Name: directus_notifications_id_seq; Type: SEQUENCE SET; Schema: content; Owner: postgres
--

SELECT pg_catalog.setval('"content"."directus_notifications_id_seq"', 1, false);


--
-- Name: directus_permissions_id_seq; Type: SEQUENCE SET; Schema: content; Owner: postgres
--

SELECT pg_catalog.setval('"content"."directus_permissions_id_seq"', 1, false);


--
-- Name: directus_presets_id_seq; Type: SEQUENCE SET; Schema: content; Owner: postgres
--

SELECT pg_catalog.setval('"content"."directus_presets_id_seq"', 1, true);


--
-- Name: directus_relations_id_seq; Type: SEQUENCE SET; Schema: content; Owner: postgres
--

SELECT pg_catalog.setval('"content"."directus_relations_id_seq"', 6, true);


--
-- Name: directus_revisions_id_seq; Type: SEQUENCE SET; Schema: content; Owner: postgres
--

SELECT pg_catalog.setval('"content"."directus_revisions_id_seq"', 30, true);


--
-- Name: directus_settings_id_seq; Type: SEQUENCE SET; Schema: content; Owner: postgres
--

SELECT pg_catalog.setval('"content"."directus_settings_id_seq"', 1, false);


--
-- Name: directus_webhooks_id_seq; Type: SEQUENCE SET; Schema: content; Owner: postgres
--

SELECT pg_catalog.setval('"content"."directus_webhooks_id_seq"', 1, false);


--
-- Name: key_key_id_seq; Type: SEQUENCE SET; Schema: pgsodium; Owner: supabase_admin
--

SELECT pg_catalog.setval('"pgsodium"."key_key_id_seq"', 1, false);


--
-- Name: hooks_id_seq; Type: SEQUENCE SET; Schema: supabase_functions; Owner: supabase_functions_admin
--

SELECT pg_catalog.setval('"supabase_functions"."hooks_id_seq"', 1, false);


--
-- PostgreSQL database dump complete
--

RESET ALL;
