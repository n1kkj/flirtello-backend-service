--
-- Idempotent schema DDL (application schemas: app_auth, content,
-- context_images, mktdata, public, translator).
-- Safe to apply ON TOP of an existing database; re-runnable.
-- Generated from pg_dump --schema-only, post-processed for idempotency.
--

--
-- PostgreSQL database dump
--

-- Dumped from database version 15.6
-- Dumped by pg_dump version 17.5

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
-- SET transaction_timeout = 0;  -- removed: PG17-only GUC, not valid on PG15

SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: app_auth; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS app_auth;


--
-- Name: content; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS content;


--
-- Name: context_images; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS context_images;


--
-- Name: mktdata; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS mktdata;


--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS public;


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: translator; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA IF NOT EXISTS translator;


--
-- Name: message_review_status; Type: TYPE; Schema: public; Owner: -
--

DO $mig$
BEGIN
CREATE TYPE public.message_review_status AS ENUM (
    'LIKE',
    'DISLIKE',
    'NEUTRAL'
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: review_types; Type: TYPE; Schema: public; Owner: -
--

DO $mig$
BEGIN
CREATE TYPE public.review_types AS ENUM (
    'TEXT',
    'IMAGE'
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: user_status; Type: TYPE; Schema: public; Owner: -
--

DO $mig$
BEGIN
CREATE TYPE public.user_status AS ENUM (
    'ONLINE',
    'OFFLINE'
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: handle_new_user(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE OR REPLACE FUNCTION public.handle_new_user() RETURNS trigger
    LANGUAGE plpgsql
    AS $$DECLARE
    -- Declare variables
    company_trial_tokens_balance_id INTEGER := 572450034;
    trial_tokens INTEGER :=0;
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
    VALUES (NEW.id, (SELECT id FROM content.tariff_plans WHERE is_trial = true and is_archived = false));

    -- 1. Insert balance for "TOKEN" with balance_amount = trial_tokens
    INSERT INTO content.balances (user_id, balance_amount, currency_type_id)
    VALUES (NEW.id, trial_tokens, (SELECT id FROM content.currency_types WHERE name = 'TOKEN'))
    RETURNING id INTO user_token_balance_id;

    -- 2. Insert balance for "SERVICE" with balance_amount = 0
    INSERT INTO content.balances (user_id, balance_amount, currency_type_id)
    VALUES (NEW.id, 0, (SELECT id FROM content.currency_types WHERE name = 'SERVICE'));

    -- 3. Insert balance for "USD" with balance_amount = 0
    INSERT INTO content.balances (user_id, balance_amount, currency_type_id)
    VALUES (NEW.id, 0, (SELECT id FROM content.currency_types WHERE name = 'EUR'));

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
END;$$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE OR REPLACE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: trigger_log; Type: TABLE; Schema: app_auth; Owner: -
--

CREATE TABLE IF NOT EXISTS app_auth.trigger_log (
    log_time timestamp with time zone DEFAULT now(),
    action text
);


--
-- Name: balances; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.balances (
    id bigint NOT NULL,
    user_id uuid,
    currency_type_id bigint,
    balance_amount numeric DEFAULT '0'::numeric,
    is_official boolean DEFAULT false NOT NULL
);


--
-- Name: balances_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE content.balances ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME content.balances_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: character_configs; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.character_configs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    public_name text NOT NULL,
    description text,
    character_id bigint NOT NULL,
    config text NOT NULL,
    path text NOT NULL,
    status character varying(255) DEFAULT 'draft'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL,
    background_file_id uuid,
    style_name character varying,
    short_name text DEFAULT ''::text NOT NULL
);


--
-- Name: clearings; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.clearings (
    id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);


--
-- Name: clearings_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE content.clearings ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME content.clearings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_banners; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_banners (
    id bigint NOT NULL,
    title text NOT NULL,
    description text,
    button_text text NOT NULL,
    button_url text NOT NULL,
    number smallint,
    subscript text,
    number_text text,
    is_active boolean DEFAULT true,
    desktop_background uuid,
    is_prioritized boolean,
    mobile_background uuid
);


--
-- Name: content_banners_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE content.content_banners ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME content.content_banners_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_blogs; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_blogs (
    id bigint NOT NULL,
    date_created timestamp with time zone DEFAULT now() NOT NULL,
    title character varying(255),
    description text,
    announcement text,
    meta_description character varying(255),
    meta_title character varying(255),
    slug character varying(255)
);


--
-- Name: content_blogs_files; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_blogs_files (
    id integer NOT NULL,
    content_blogs_id bigint,
    directus_files_id uuid
);


--
-- Name: content_blogs_files_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_blogs_files_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_blogs_files_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_blogs_files_id_seq OWNED BY content.content_blogs_files.id;


--
-- Name: content_blogs_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_blogs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_blogs_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_blogs_id_seq OWNED BY content.content_blogs.id;


--
-- Name: content_character_filters; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_character_filters (
    id integer NOT NULL,
    name character varying(255)
);


--
-- Name: content_character_filters_content_characters; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_character_filters_content_characters (
    id integer NOT NULL,
    content_character_filters_id integer,
    content_characters_id integer
);


--
-- Name: content_character_filters_content_characters_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_character_filters_content_characters_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_character_filters_content_characters_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_character_filters_content_characters_id_seq OWNED BY content.content_character_filters_content_characters.id;


--
-- Name: content_character_filters_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_character_filters_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_character_filters_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_character_filters_id_seq OWNED BY content.content_character_filters.id;


--
-- Name: content_character_images; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_character_images (
    id bigint NOT NULL,
    character_id integer,
    image_id uuid
);


--
-- Name: content_character_images_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE content.content_character_images ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME content.content_character_images_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_characters; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_characters (
    id integer NOT NULL,
    status character varying(255) DEFAULT 'draft'::character varying NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    name character varying(255),
    personality text,
    main_photo uuid,
    public_description text,
    system_prompt_override text,
    use_system_prompt_override boolean,
    message_addendum_override text,
    use_message_addendum_override boolean,
    caption character varying(255),
    video_preview uuid,
    onboarding_message character varying(255),
    background_image_id uuid,
    telegram_description text
);


--
-- Name: content_characters_content_tags; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_characters_content_tags (
    id integer NOT NULL,
    content_characters_id integer,
    content_tags_id integer
);


--
-- Name: content_characters_content_tags_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_characters_content_tags_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_characters_content_tags_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_characters_content_tags_id_seq OWNED BY content.content_characters_content_tags.id;


--
-- Name: content_characters_files; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_characters_files (
    id integer NOT NULL,
    content_characters_id integer,
    directus_files_id uuid
);


--
-- Name: content_characters_files_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_characters_files_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_characters_files_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_characters_files_id_seq OWNED BY content.content_characters_files.id;


--
-- Name: content_characters_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_characters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_characters_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_characters_id_seq OWNED BY content.content_characters.id;


--
-- Name: content_contexts; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_contexts (
    id integer NOT NULL,
    status character varying(255) DEFAULT 'draft'::character varying NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    name character varying(255),
    first_message text,
    scenario text,
    context_type character varying(255),
    first_image uuid
);


--
-- Name: content_contexts_content_characters; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_contexts_content_characters (
    id integer NOT NULL,
    content_contexts_id integer,
    content_characters_id integer
);


--
-- Name: content_contexts_content_characters_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_contexts_content_characters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_contexts_content_characters_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_contexts_content_characters_id_seq OWNED BY content.content_contexts_content_characters.id;


--
-- Name: content_contexts_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_contexts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_contexts_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_contexts_id_seq OWNED BY content.content_contexts.id;


--
-- Name: content_faq; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_faq (
    id bigint NOT NULL,
    date_created timestamp with time zone,
    question character varying(255),
    answer text,
    "order" numeric
);


--
-- Name: content_faq_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_faq_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_faq_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_faq_id_seq OWNED BY content.content_faq.id;


--
-- Name: content_images; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_images (
    id uuid NOT NULL,
    hash character varying(255) DEFAULT NULL::character varying NOT NULL,
    "character" integer NOT NULL,
    image uuid,
    location character varying(255) DEFAULT NULL::character varying NOT NULL,
    cloths character varying(255) DEFAULT NULL::character varying NOT NULL,
    rating character varying(255) DEFAULT NULL::character varying NOT NULL,
    behavior character varying(255) NOT NULL,
    prompt text NOT NULL,
    name character varying(255) NOT NULL,
    char_name character varying(255),
    image_blurred uuid,
    attr1 character varying(255),
    attr2 character varying(255),
    attr3 character varying(255),
    is_free boolean DEFAULT false NOT NULL,
    config_id uuid
);


--
-- Name: content_images_path; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_images_path (
    id integer NOT NULL,
    content_images_id uuid,
    item character varying(255),
    collection character varying(255)
);


--
-- Name: content_images_path_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_images_path_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_images_path_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_images_path_id_seq OWNED BY content.content_images_path.id;


--
-- Name: content_locations; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_locations (
    id integer NOT NULL,
    status character varying(255) DEFAULT 'draft'::character varying NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    name character varying(255),
    header_image uuid,
    description text
);


--
-- Name: content_locations_content_characters; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_locations_content_characters (
    id integer NOT NULL,
    content_locations_id integer,
    content_characters_id integer
);


--
-- Name: content_locations_content_characters_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_locations_content_characters_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_locations_content_characters_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_locations_content_characters_id_seq OWNED BY content.content_locations_content_characters.id;


--
-- Name: content_locations_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_locations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_locations_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_locations_id_seq OWNED BY content.content_locations.id;


--
-- Name: content_review_categories; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_review_categories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    review_type public.review_types NOT NULL,
    category_name text NOT NULL
);


--
-- Name: content_settings; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_settings (
    id integer NOT NULL,
    status character varying(255) DEFAULT 'draft'::character varying NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    txt_option text,
    bool_option boolean,
    name character varying(255)
);


--
-- Name: content_settings_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_settings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_settings_id_seq OWNED BY content.content_settings.id;


--
-- Name: content_tags; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_tags (
    id integer NOT NULL,
    status character varying(255) DEFAULT 'draft'::character varying NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    icon character varying(255),
    plate_color character varying(255),
    name character varying(255)
);


--
-- Name: content_tags_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_tags_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_tags_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_tags_id_seq OWNED BY content.content_tags.id;


--
-- Name: content_texts; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_texts (
    id integer NOT NULL,
    slug text,
    text text,
    header character varying(255)
);


--
-- Name: content_texts_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_texts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_texts_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_texts_id_seq OWNED BY content.content_texts.id;


--
-- Name: content_traits; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_traits (
    id integer NOT NULL,
    status character varying(255) DEFAULT 'draft'::character varying NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    name character varying(255)
);


--
-- Name: content_traits_content_characters; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_traits_content_characters (
    id integer NOT NULL,
    content_traits_id integer,
    content_characters_id integer
);


--
-- Name: content_traits_content_characters_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_traits_content_characters_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_traits_content_characters_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_traits_content_characters_id_seq OWNED BY content.content_traits_content_characters.id;


--
-- Name: content_traits_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.content_traits_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_traits_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.content_traits_id_seq OWNED BY content.content_traits.id;


--
-- Name: content_webhook_data; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.content_webhook_data (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    data jsonb NOT NULL,
    payment_system_name text,
    created_at timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL,
    is_handled boolean NOT NULL,
    status text
);


--
-- Name: currency_types; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.currency_types (
    id bigint NOT NULL,
    name text NOT NULL
);


--
-- Name: currency_types_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE content.currency_types ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME content.currency_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_activity; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_activity (
    id integer NOT NULL,
    action character varying(45) NOT NULL,
    "user" uuid,
    "timestamp" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ip character varying(50),
    user_agent text,
    collection character varying(64) NOT NULL,
    item character varying(255) NOT NULL,
    comment text,
    origin character varying(255)
);


--
-- Name: directus_activity_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.directus_activity_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: directus_activity_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.directus_activity_id_seq OWNED BY content.directus_activity.id;


--
-- Name: directus_collections; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_collections (
    collection character varying(64) NOT NULL,
    icon character varying(30),
    note text,
    display_template character varying(255),
    hidden boolean DEFAULT false NOT NULL,
    singleton boolean DEFAULT false NOT NULL,
    translations json,
    archive_field character varying(64),
    archive_app_filter boolean DEFAULT true NOT NULL,
    archive_value character varying(255),
    unarchive_value character varying(255),
    sort_field character varying(64),
    accountability character varying(255) DEFAULT 'all'::character varying,
    color character varying(255),
    item_duplication_fields json,
    sort integer,
    "group" character varying(64),
    collapse character varying(255) DEFAULT 'open'::character varying NOT NULL,
    preview_url character varying(255),
    versioning boolean DEFAULT false NOT NULL
);


--
-- Name: directus_dashboards; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_dashboards (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    icon character varying(30) DEFAULT 'dashboard'::character varying NOT NULL,
    note text,
    date_created timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    user_created uuid,
    color character varying(255)
);


--
-- Name: directus_extensions; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_extensions (
    enabled boolean DEFAULT true NOT NULL,
    id uuid NOT NULL,
    folder character varying(255) NOT NULL,
    source character varying(255) NOT NULL,
    bundle uuid
);


--
-- Name: directus_fields; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_fields (
    id integer NOT NULL,
    collection character varying(64) NOT NULL,
    field character varying(64) NOT NULL,
    special character varying(64),
    interface character varying(64),
    options json,
    display character varying(64),
    display_options json,
    readonly boolean DEFAULT false NOT NULL,
    hidden boolean DEFAULT false NOT NULL,
    sort integer,
    width character varying(30) DEFAULT 'full'::character varying,
    translations json,
    note text,
    conditions json,
    required boolean DEFAULT false,
    "group" character varying(64),
    validation json,
    validation_message text
);


--
-- Name: directus_fields_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.directus_fields_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: directus_fields_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.directus_fields_id_seq OWNED BY content.directus_fields.id;


--
-- Name: directus_files; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_files (
    id uuid NOT NULL,
    storage character varying(255) NOT NULL,
    filename_disk character varying(255),
    filename_download character varying(255) NOT NULL,
    title character varying(255),
    type character varying(255),
    folder uuid,
    uploaded_by uuid,
    uploaded_on timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    modified_by uuid,
    modified_on timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    charset character varying(50),
    filesize bigint,
    width integer,
    height integer,
    duration integer,
    embed character varying(200),
    description text,
    location text,
    tags text,
    metadata json,
    focal_point_x integer,
    focal_point_y integer
);


--
-- Name: directus_flows; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_flows (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    icon character varying(30),
    color character varying(255),
    description text,
    status character varying(255) DEFAULT 'active'::character varying NOT NULL,
    trigger character varying(255),
    accountability character varying(255) DEFAULT 'all'::character varying,
    options json,
    operation uuid,
    date_created timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    user_created uuid
);


--
-- Name: directus_folders; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_folders (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    parent uuid
);


--
-- Name: directus_migrations; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_migrations (
    version character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    "timestamp" timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: directus_notifications; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_notifications (
    id integer NOT NULL,
    "timestamp" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    status character varying(255) DEFAULT 'inbox'::character varying,
    recipient uuid NOT NULL,
    sender uuid,
    subject character varying(255) NOT NULL,
    message text,
    collection character varying(64),
    item character varying(255)
);


--
-- Name: directus_notifications_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.directus_notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: directus_notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.directus_notifications_id_seq OWNED BY content.directus_notifications.id;


--
-- Name: directus_operations; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_operations (
    id uuid NOT NULL,
    name character varying(255),
    key character varying(255) NOT NULL,
    type character varying(255) NOT NULL,
    position_x integer NOT NULL,
    position_y integer NOT NULL,
    options json,
    resolve uuid,
    reject uuid,
    flow uuid NOT NULL,
    date_created timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    user_created uuid
);


--
-- Name: directus_panels; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_panels (
    id uuid NOT NULL,
    dashboard uuid NOT NULL,
    name character varying(255),
    icon character varying(30) DEFAULT NULL::character varying,
    color character varying(10),
    show_header boolean DEFAULT false NOT NULL,
    note text,
    type character varying(255) NOT NULL,
    position_x integer NOT NULL,
    position_y integer NOT NULL,
    width integer NOT NULL,
    height integer NOT NULL,
    options json,
    date_created timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    user_created uuid
);


--
-- Name: directus_permissions; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_permissions (
    id integer NOT NULL,
    role uuid,
    collection character varying(64) NOT NULL,
    action character varying(10) NOT NULL,
    permissions json,
    validation json,
    presets json,
    fields text
);


--
-- Name: directus_permissions_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.directus_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: directus_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.directus_permissions_id_seq OWNED BY content.directus_permissions.id;


--
-- Name: directus_presets; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_presets (
    id integer NOT NULL,
    bookmark character varying(255),
    "user" uuid,
    role uuid,
    collection character varying(64),
    search character varying(100),
    layout character varying(100) DEFAULT 'tabular'::character varying,
    layout_query json,
    layout_options json,
    refresh_interval integer,
    filter json,
    icon character varying(30) DEFAULT 'bookmark'::character varying,
    color character varying(255)
);


--
-- Name: directus_presets_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.directus_presets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: directus_presets_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.directus_presets_id_seq OWNED BY content.directus_presets.id;


--
-- Name: directus_relations; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_relations (
    id integer NOT NULL,
    many_collection character varying(64) NOT NULL,
    many_field character varying(64) NOT NULL,
    one_collection character varying(64),
    one_field character varying(64),
    one_collection_field character varying(64),
    one_allowed_collections text,
    junction_field character varying(64),
    sort_field character varying(64),
    one_deselect_action character varying(255) DEFAULT 'nullify'::character varying NOT NULL
);


--
-- Name: directus_relations_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.directus_relations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: directus_relations_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.directus_relations_id_seq OWNED BY content.directus_relations.id;


--
-- Name: directus_revisions; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_revisions (
    id integer NOT NULL,
    activity integer NOT NULL,
    collection character varying(64) NOT NULL,
    item character varying(255) NOT NULL,
    data json,
    delta json,
    parent integer,
    version uuid
);


--
-- Name: directus_revisions_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.directus_revisions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: directus_revisions_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.directus_revisions_id_seq OWNED BY content.directus_revisions.id;


--
-- Name: directus_roles; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_roles (
    id uuid NOT NULL,
    name character varying(100) NOT NULL,
    icon character varying(30) DEFAULT 'supervised_user_circle'::character varying NOT NULL,
    description text,
    ip_access text,
    enforce_tfa boolean DEFAULT false NOT NULL,
    admin_access boolean DEFAULT false NOT NULL,
    app_access boolean DEFAULT true NOT NULL
);


--
-- Name: directus_sessions; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_sessions (
    token character varying(64) NOT NULL,
    "user" uuid,
    expires timestamp with time zone NOT NULL,
    ip character varying(255),
    user_agent text,
    share uuid,
    origin character varying(255)
);


--
-- Name: directus_settings; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_settings (
    id integer NOT NULL,
    project_name character varying(100) DEFAULT 'Directus'::character varying NOT NULL,
    project_url character varying(255),
    project_color character varying(255) DEFAULT '#6644FF'::character varying NOT NULL,
    project_logo uuid,
    public_foreground uuid,
    public_background uuid,
    public_note text,
    auth_login_attempts integer DEFAULT 25,
    auth_password_policy character varying(100),
    storage_asset_transform character varying(7) DEFAULT 'all'::character varying,
    storage_asset_presets json,
    custom_css text,
    storage_default_folder uuid,
    basemaps json,
    mapbox_key character varying(255),
    module_bar json,
    project_descriptor character varying(100),
    default_language character varying(255) DEFAULT 'en-US'::character varying NOT NULL,
    custom_aspect_ratios json,
    public_favicon uuid,
    default_appearance character varying(255) DEFAULT 'auto'::character varying NOT NULL,
    default_theme_light character varying(255),
    theme_light_overrides json,
    default_theme_dark character varying(255),
    theme_dark_overrides json,
    report_error_url character varying(255),
    report_bug_url character varying(255),
    report_feature_url character varying(255),
    public_registration boolean DEFAULT false NOT NULL,
    public_registration_verify_email boolean DEFAULT true NOT NULL,
    public_registration_role uuid,
    public_registration_email_filter json
);


--
-- Name: directus_settings_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.directus_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: directus_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.directus_settings_id_seq OWNED BY content.directus_settings.id;


--
-- Name: directus_shares; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_shares (
    id uuid NOT NULL,
    name character varying(255),
    collection character varying(64) NOT NULL,
    item character varying(255) NOT NULL,
    role uuid,
    password character varying(255),
    user_created uuid,
    date_created timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    date_start timestamp with time zone,
    date_end timestamp with time zone,
    times_used integer DEFAULT 0,
    max_uses integer
);


--
-- Name: directus_translations; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_translations (
    id uuid NOT NULL,
    language character varying(255) NOT NULL,
    key character varying(255) NOT NULL,
    value text NOT NULL
);


--
-- Name: directus_users; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_users (
    id uuid NOT NULL,
    first_name character varying(50),
    last_name character varying(50),
    email character varying(128),
    password character varying(255),
    location character varying(255),
    title character varying(50),
    description text,
    tags json,
    avatar uuid,
    language character varying(255) DEFAULT NULL::character varying,
    tfa_secret character varying(255),
    status character varying(16) DEFAULT 'active'::character varying NOT NULL,
    role uuid,
    token character varying(255),
    last_access timestamp with time zone,
    last_page character varying(255),
    provider character varying(128) DEFAULT 'default'::character varying NOT NULL,
    external_identifier character varying(255),
    auth_data json,
    email_notifications boolean DEFAULT true,
    appearance character varying(255),
    theme_dark character varying(255),
    theme_light character varying(255),
    theme_light_overrides json,
    theme_dark_overrides json
);


--
-- Name: directus_versions; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_versions (
    id uuid NOT NULL,
    key character varying(64) NOT NULL,
    name character varying(255),
    collection character varying(64) NOT NULL,
    item character varying(255) NOT NULL,
    hash character varying(255),
    date_created timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    date_updated timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    user_created uuid,
    user_updated uuid
);


--
-- Name: directus_webhooks; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.directus_webhooks (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    method character varying(10) DEFAULT 'POST'::character varying NOT NULL,
    url character varying(255) NOT NULL,
    status character varying(10) DEFAULT 'active'::character varying NOT NULL,
    data boolean DEFAULT true NOT NULL,
    actions character varying(100) NOT NULL,
    collections character varying(255) NOT NULL,
    headers json,
    was_active_before_deprecation boolean DEFAULT false NOT NULL,
    migrated_flow uuid
);


--
-- Name: directus_webhooks_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.directus_webhooks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: directus_webhooks_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.directus_webhooks_id_seq OWNED BY content.directus_webhooks.id;


--
-- Name: gift_codes; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.gift_codes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    code text NOT NULL,
    token_amount integer,
    code_type text,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL,
    tokens_lifetime_hours integer DEFAULT 48 NOT NULL
);


--
-- Name: gift_codes_users; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.gift_codes_users (
    id bigint NOT NULL,
    gift_code_id uuid DEFAULT gen_random_uuid(),
    user_id uuid DEFAULT gen_random_uuid(),
    activated_at timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);


--
-- Name: gift_codes_users_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE content.gift_codes_users ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME content.gift_codes_users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: images_user_settings; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.images_user_settings (
    id uuid NOT NULL,
    settings extensions.hstore
);


--
-- Name: images_views; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.images_views (
    id uuid NOT NULL,
    image_id uuid NOT NULL,
    user_id uuid NOT NULL
);


--
-- Name: invoices; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.invoices (
    id bigint NOT NULL,
    customer_id uuid,
    service_id uuid,
    total numeric NOT NULL,
    currency_type_id bigint,
    status text NOT NULL,
    service_type text NOT NULL,
    callback_url text NOT NULL,
    payment_system_transaction_id text,
    payment_system_name text
);


--
-- Name: invoices_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE content.invoices ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME content.invoices_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.landings (
    id integer NOT NULL,
    status character varying(255) DEFAULT 'draft'::character varying NOT NULL,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    main_title character varying(255) DEFAULT 'NSWF AI Chat'::character varying,
    main_subtitle character varying(255) DEFAULT 'Explore the World of Al Sexting: Your Guide to Flirtello.com'::character varying,
    main_image uuid,
    main_button_link character varying(255),
    main_button_text character varying(255),
    slug character varying(255),
    meta_description character varying(255) DEFAULT NULL::character varying,
    meta_title character varying(255) DEFAULT NULL::character varying
);


--
-- Name: landings_benefits_section; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.landings_benefits_section (
    id integer NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    title character varying(255) DEFAULT 'Benefits of Using the NSFW Al Chat Platform'::character varying,
    subtitle character varying(255) DEFAULT 'Embracing the world of Al sexting unlocks numerous benefits:'::character varying,
    button_text character varying(255) DEFAULT 'Try it for free!'::character varying,
    button_link character varying(255) DEFAULT NULL::character varying,
    landing_id integer
);


--
-- Name: landings_benefits_section_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.landings_benefits_section_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: landings_benefits_section_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.landings_benefits_section_id_seq OWNED BY content.landings_benefits_section.id;


--
-- Name: landings_benefits_subsection; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.landings_benefits_subsection (
    id integer NOT NULL,
    status character varying(255) DEFAULT 'draft'::character varying NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    title character varying(255) DEFAULT NULL::character varying,
    text text,
    image uuid,
    benefits_section_id integer
);


--
-- Name: landings_benefits_subsection_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.landings_benefits_subsection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: landings_benefits_subsection_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.landings_benefits_subsection_id_seq OWNED BY content.landings_benefits_subsection.id;


--
-- Name: landings_characters_section; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.landings_characters_section (
    id integer NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    title character varying(255) DEFAULT 'Characters'::character varying,
    landing_id integer
);


--
-- Name: landings_characters_section_content_characters; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.landings_characters_section_content_characters (
    id integer NOT NULL,
    landings_characters_section_id integer,
    content_characters_id integer,
    sort integer
);


--
-- Name: landings_characters_section_content_characters_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.landings_characters_section_content_characters_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: landings_characters_section_content_characters_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.landings_characters_section_content_characters_id_seq OWNED BY content.landings_characters_section_content_characters.id;


--
-- Name: landings_characters_section_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.landings_characters_section_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: landings_characters_section_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.landings_characters_section_id_seq OWNED BY content.landings_characters_section.id;


--
-- Name: landings_conclusion_section; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.landings_conclusion_section (
    id integer NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    title character varying(255) DEFAULT NULL::character varying,
    text text,
    button_text character varying(255) DEFAULT 'Try it for free!'::character varying,
    button_link character varying(255) DEFAULT NULL::character varying,
    landing_id integer
);


--
-- Name: landings_conclusion_section_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.landings_conclusion_section_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: landings_conclusion_section_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.landings_conclusion_section_id_seq OWNED BY content.landings_conclusion_section.id;


--
-- Name: landings_faq_section; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.landings_faq_section (
    id integer NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    title character varying(255) DEFAULT 'Q&A Block'::character varying,
    subtitle character varying(255) DEFAULT 'Your NSFW Character Al Chat Questions Answered'::character varying,
    landing_id integer
);


--
-- Name: landings_faq_section_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.landings_faq_section_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: landings_faq_section_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.landings_faq_section_id_seq OWNED BY content.landings_faq_section.id;


--
-- Name: landings_faq_subsection; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.landings_faq_subsection (
    id integer NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    question text,
    answer text,
    faq_section_id integer
);


--
-- Name: landings_faq_subsection_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.landings_faq_subsection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: landings_faq_subsection_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.landings_faq_subsection_id_seq OWNED BY content.landings_faq_subsection.id;


--
-- Name: landings_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.landings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: landings_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.landings_id_seq OWNED BY content.landings.id;


--
-- Name: landings_main_section; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.landings_main_section (
    id integer NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    landing_id integer
);


--
-- Name: landings_main_section_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.landings_main_section_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: landings_main_section_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.landings_main_section_id_seq OWNED BY content.landings_main_section.id;


--
-- Name: landings_main_subsection; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.landings_main_subsection (
    id integer NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    title character varying(255) DEFAULT NULL::character varying,
    text text,
    button_text character varying(255) DEFAULT 'Try it for free!'::character varying,
    button_link character varying(255) DEFAULT NULL::character varying,
    landings_main_section_id integer,
    image uuid
);


--
-- Name: landings_main_subsection_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.landings_main_subsection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: landings_main_subsection_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.landings_main_subsection_id_seq OWNED BY content.landings_main_subsection.id;


--
-- Name: landings_more_ai_section; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.landings_more_ai_section (
    id integer NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    title character varying(255) DEFAULT 'More NSFW Al Chat with Flirtello.com'::character varying,
    landing_id integer
);


--
-- Name: landings_more_ai_section_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.landings_more_ai_section_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: landings_more_ai_section_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.landings_more_ai_section_id_seq OWNED BY content.landings_more_ai_section.id;


--
-- Name: landings_more_ai_subsection; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.landings_more_ai_subsection (
    id integer NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    button_text character varying(255) DEFAULT NULL::character varying,
    more_ai_section_id integer,
    button_link character varying(255) DEFAULT NULL::character varying
);


--
-- Name: landings_more_ai_subsection_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.landings_more_ai_subsection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: landings_more_ai_subsection_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.landings_more_ai_subsection_id_seq OWNED BY content.landings_more_ai_subsection.id;


--
-- Name: landings_secondary_section; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.landings_secondary_section (
    id integer NOT NULL,
    sort integer,
    user_created uuid,
    date_created timestamp with time zone,
    user_updated uuid,
    date_updated timestamp with time zone,
    title character varying(255) DEFAULT NULL::character varying,
    text text,
    button_text character varying(255) DEFAULT 'Try it for free!'::character varying,
    button_link character varying(255) DEFAULT NULL::character varying,
    landing_id integer
);


--
-- Name: landings_secondary_section_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS content.landings_secondary_section_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: landings_secondary_section_id_seq; Type: SEQUENCE OWNED BY; Schema: content; Owner: -
--

ALTER SEQUENCE content.landings_secondary_section_id_seq OWNED BY content.landings_secondary_section.id;


--
-- Name: llm_stats; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.llm_stats (
    id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    model_id character varying NOT NULL,
    model_latency integer NOT NULL,
    input_tokens integer NOT NULL,
    output_tokens integer NOT NULL,
    ref_id integer NOT NULL,
    ref_type text NOT NULL,
    user_id uuid NOT NULL,
    system_prompt text,
    chat_history json,
    prompt text,
    response text,
    llm_provider text
);


--
-- Name: llm_stats_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE content.llm_stats ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME content.llm_stats_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: message_archive; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.message_archive (
    id bigint NOT NULL,
    inserted_at timestamp with time zone DEFAULT now() NOT NULL,
    text text,
    attachments jsonb,
    user_id uuid,
    char_id integer,
    channel_id bigint,
    archive_id uuid NOT NULL,
    archive_time timestamp with time zone
);


--
-- Name: message_archive_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE content.message_archive ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME content.message_archive_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: transactions; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.transactions (
    user_id uuid,
    balance_id_from bigint NOT NULL,
    balance_id_to bigint NOT NULL,
    transaction_type text NOT NULL,
    service_id uuid,
    amount numeric,
    source_name text,
    additional_data json,
    created_at timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL,
    correlation_id uuid,
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    clearing_id bigint
);


--
-- Name: message_image_stats; Type: VIEW; Schema: content; Owner: -
--

CREATE OR REPLACE VIEW content.message_image_stats AS
 SELECT date(t.created_at) AS interaction_date,
    count(DISTINCT
        CASE
            WHEN ((t.additional_data)::jsonb ? 'message_id'::text) THEN t.user_id
            ELSE NULL::uuid
        END) AS unique_chat_users,
    count(DISTINCT
        CASE
            WHEN ((t.additional_data)::jsonb ? 'image_id'::text) THEN t.user_id
            ELSE NULL::uuid
        END) AS unique_image_users
   FROM content.transactions t
  GROUP BY (date(t.created_at))
  ORDER BY (date(t.created_at));


--
-- Name: paid_actions; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.paid_actions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    price numeric NOT NULL,
    is_archived boolean DEFAULT false,
    description text,
    is_public boolean DEFAULT false
);


--
-- Name: summaries; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.summaries (
    id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    channel_id bigint NOT NULL,
    summary text NOT NULL,
    message_date_from timestamp with time zone NOT NULL,
    message_date_to timestamp with time zone NOT NULL
);


--
-- Name: summaries_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE content.summaries ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME content.summaries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: tariff_plans; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.tariff_plans (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    tokens_per_month numeric,
    duration_in_month smallint,
    currency_type_id bigint,
    is_trial boolean DEFAULT false,
    is_archived boolean DEFAULT false,
    tariff_info text,
    price numeric,
    internal_name text,
    is_highlighted boolean,
    "order" smallint,
    created_at timestamp with time zone DEFAULT (now() AT TIME ZONE 'utc'::text),
    payment_system_plan_id text
);


--
-- Name: token_batches; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.token_batches (
    id bigint NOT NULL,
    token_amount numeric NOT NULL,
    expiration_date timestamp with time zone,
    user_plans_id uuid
);


--
-- Name: token_batches_id_seq; Type: SEQUENCE; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE content.token_batches ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME content.token_batches_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: token_packs; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.token_packs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    amount numeric NOT NULL,
    currency_type_id bigint,
    price numeric NOT NULL,
    is_archived boolean DEFAULT false,
    name text NOT NULL,
    is_highlighted boolean DEFAULT false,
    "order" smallint,
    lifetime_days integer DEFAULT 9999 NOT NULL
);


--
-- Name: user_plans; Type: TABLE; Schema: content; Owner: -
--

CREATE TABLE IF NOT EXISTS content.user_plans (
    user_id uuid NOT NULL,
    tariff_plan_id uuid,
    expired_at timestamp with time zone,
    next_top_up timestamp with time zone,
    is_paid boolean,
    truevo_subscription_id text,
    truevo_token_id text
);


--
-- Name: disposable_email_domains; Type: TABLE; Schema: context_images; Owner: -
--

CREATE TABLE IF NOT EXISTS context_images.disposable_email_domains (
    id bigint NOT NULL,
    domain text
);


--
-- Name: disposable_email_domains_id_seq; Type: SEQUENCE; Schema: context_images; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE context_images.disposable_email_domains ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME context_images.disposable_email_domains_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: image_metadata; Type: TABLE; Schema: context_images; Owner: -
--

CREATE TABLE IF NOT EXISTS context_images.image_metadata (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tag_string text,
    tag_string_embedding extensions.vector(1024),
    rating text,
    "character" integer,
    config_id uuid,
    image_description text,
    image_description_embedding extensions.vector,
    cohere_tag_embedding extensions.vector(1024),
    cohere_desc_embedding extensions.vector(1024)
);


--
-- Name: tag_embeddings; Type: TABLE; Schema: context_images; Owner: -
--

CREATE TABLE IF NOT EXISTS context_images.tag_embeddings (
    tag text NOT NULL,
    embedding extensions.vector(1024) NOT NULL,
    num_usages bigint,
    cohere_embedding extensions.vector(1024)
);


--
-- Name: mktdata_raw; Type: TABLE; Schema: mktdata; Owner: -
--

CREATE TABLE IF NOT EXISTS mktdata.mktdata_raw (
    id integer NOT NULL,
    user_id uuid NOT NULL,
    params json NOT NULL,
    created_at timestamp without time zone NOT NULL,
    action text NOT NULL
);


--
-- Name: mktdata_raw_id_seq; Type: SEQUENCE; Schema: mktdata; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS mktdata.mktdata_raw_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: mktdata_raw_id_seq; Type: SEQUENCE OWNED BY; Schema: mktdata; Owner: -
--

ALTER SEQUENCE mktdata.mktdata_raw_id_seq OWNED BY mktdata.mktdata_raw.id;


--
-- Name: _blog; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS public._blog (
    id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    title character varying,
    description text,
    images jsonb,
    announcement text
);


--
-- Name: TABLE _blog; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public._blog IS 'site blog articles';


--
-- Name: _faq; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS public._faq (
    id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    question character varying,
    answer text,
    "order" numeric
);


--
-- Name: TABLE _faq; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public._faq IS 'faq for users';


--
-- Name: blog_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE public._blog ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.blog_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: blogs; Type: VIEW; Schema: public; Owner: -
--

CREATE OR REPLACE VIEW public.blogs AS
 SELECT content_blogs.id,
    content_blogs.date_created AS created_at,
    content_blogs.title,
    content_blogs.description,
    content_blogs.announcement,
    content_blogs.slug,
    content_blogs.meta_title,
    content_blogs.meta_description
   FROM content.content_blogs;


--
-- Name: channels; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS public.channels (
    id bigint NOT NULL,
    inserted_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    user_id uuid,
    char_id integer,
    current_char_context integer,
    config_id uuid,
    stage_name text
);

ALTER TABLE ONLY public.channels REPLICA IDENTITY FULL;


--
-- Name: TABLE channels; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.channels IS 'Message channels';


--
-- Name: channels_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE public.channels ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.channels_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: characters; Type: VIEW; Schema: public; Owner: -
--

CREATE OR REPLACE VIEW public.characters AS
 WITH trait_agg AS (
         SELECT ctc.content_characters_id,
            array_remove(array_agg(DISTINCT ct.name), NULL::character varying) AS traits
           FROM (content.content_traits_content_characters ctc
             JOIN content.content_traits ct ON ((ctc.content_traits_id = ct.id)))
          GROUP BY ctc.content_characters_id
        ), filter_agg AS (
         SELECT cfc.content_characters_id,
            array_remove(array_agg(DISTINCT cf.name), NULL::character varying) AS filters
           FROM (content.content_character_filters_content_characters cfc
             JOIN content.content_character_filters cf ON ((cfc.content_character_filters_id = cf.id)))
          GROUP BY cfc.content_characters_id
        ), location_agg AS (
         SELECT clc.content_characters_id,
            array_remove(array_agg(DISTINCT cl.name), NULL::character varying) AS locations
           FROM (content.content_locations_content_characters clc
             JOIN content.content_locations cl ON ((clc.content_locations_id = cl.id)))
          GROUP BY clc.content_characters_id
        ), additional_files_agg AS (
         SELECT ccf.content_characters_id,
            array_remove(array_agg(DISTINCT df2.filename_disk), NULL::character varying) AS additional_files
           FROM (content.content_characters_files ccf
             JOIN content.directus_files df2 ON ((ccf.directus_files_id = df2.id)))
          GROUP BY ccf.content_characters_id
        ), profile_images_agg AS (
         SELECT cci.character_id,
            array_agg(cci.image_id) AS profile_images_ids
           FROM content.content_character_images cci
          GROUP BY cci.character_id
        ), tags_agg AS (
         SELECT cct.content_characters_id,
            jsonb_agg(jsonb_build_object('name', ct.name, 'plate_color', ct.plate_color, 'icon', ct.icon)) AS tags
           FROM (content.content_characters_content_tags cct
             JOIN content.content_tags ct ON ((cct.content_tags_id = ct.id)))
          GROUP BY cct.content_characters_id
        )
 SELECT cc.id,
    cc.status,
    cc.sort,
    cc.name,
    cc.public_description,
    COALESCE(t.traits, '{}'::character varying[]) AS traits,
    COALESCE(f.filters, '{}'::character varying[]) AS filters,
    COALESCE(l.locations, '{}'::character varying[]) AS locations,
    df.filename_disk AS main_photo,
    COALESCE(a.additional_files, '{}'::character varying[]) AS profile_images,
    COALESCE(p.profile_images_ids, '{}'::uuid[]) AS profile_images_ids,
    COALESCE(tag.tags, '[]'::jsonb) AS tags,
    cc.caption,
    df_video.filename_disk AS video_preview,
    cc.onboarding_message,
    df_background.filename_disk AS background_image,
    cc.telegram_description
   FROM (((((((((content.content_characters cc
     LEFT JOIN trait_agg t ON ((cc.id = t.content_characters_id)))
     LEFT JOIN filter_agg f ON ((cc.id = f.content_characters_id)))
     LEFT JOIN location_agg l ON ((cc.id = l.content_characters_id)))
     LEFT JOIN content.directus_files df ON ((cc.main_photo = df.id)))
     LEFT JOIN additional_files_agg a ON ((cc.id = a.content_characters_id)))
     LEFT JOIN profile_images_agg p ON ((cc.id = p.character_id)))
     LEFT JOIN tags_agg tag ON ((cc.id = tag.content_characters_id)))
     LEFT JOIN content.directus_files df_video ON ((cc.video_preview = df_video.id)))
     LEFT JOIN content.directus_files df_background ON ((cc.background_image_id = df_background.id)));


--
-- Name: content_review_categories; Type: VIEW; Schema: public; Owner: -
--

CREATE OR REPLACE VIEW public.content_review_categories AS
 SELECT content_review_categories.id,
    content_review_categories.review_type,
    content_review_categories.category_name
   FROM content.content_review_categories;


--
-- Name: faq; Type: VIEW; Schema: public; Owner: -
--

CREATE OR REPLACE VIEW public.faq AS
 SELECT content_faq.id,
    content_faq.date_created AS created_at,
    content_faq.question,
    content_faq.answer,
    content_faq."order"
   FROM content.content_faq;


--
-- Name: faq_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE public._faq ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.faq_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS public.messages (
    id bigint NOT NULL,
    inserted_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    text text,
    attachments jsonb,
    user_id uuid,
    char_id integer,
    channel_id bigint NOT NULL,
    review_categories text[],
    review_status public.message_review_status DEFAULT 'NEUTRAL'::public.message_review_status NOT NULL,
    review_text text,
    message_type text,
    stage_name text
);

ALTER TABLE ONLY public.messages REPLICA IDENTITY FULL;


--
-- Name: TABLE messages; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.messages IS 'Individual messages.';


--
-- Name: messages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE public.messages ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.messages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: notification; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS public.notification (
    id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    title character varying DEFAULT ''::character varying,
    is_readed boolean DEFAULT false,
    user_id uuid,
    channel_id bigint
);


--
-- Name: TABLE notification; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.notification IS 'Notify users about new messages';


--
-- Name: notification_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE public.notification ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.notification_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: paid_actions; Type: VIEW; Schema: public; Owner: -
--

CREATE OR REPLACE VIEW public.paid_actions AS
 SELECT paid_actions.id,
    paid_actions.price,
    paid_actions.description
   FROM content.paid_actions
  WHERE ((paid_actions.is_archived = false) AND (paid_actions.is_public = true));


--
-- Name: tariff_plans; Type: VIEW; Schema: public; Owner: -
--

CREATE OR REPLACE VIEW public.tariff_plans AS
 SELECT tp.id,
    tp.name,
    tp.tokens_per_month,
    tp.duration_in_month,
    tp.currency_type_id,
    tp.price,
    tp.is_trial,
    tp.is_archived,
    tp.tariff_info,
    tp.is_highlighted,
    tp."order",
    latest_archived.price AS previous_price
   FROM (content.tariff_plans tp
     LEFT JOIN LATERAL ( SELECT archived_tp.price
           FROM content.tariff_plans archived_tp
          WHERE ((archived_tp.name = tp.name) AND (archived_tp.duration_in_month = tp.duration_in_month) AND (archived_tp.is_archived = true) AND (archived_tp.is_trial = false) AND (archived_tp.price > tp.price))
          ORDER BY archived_tp.created_at
         LIMIT 1) latest_archived ON (true))
  WHERE ((tp.is_trial = false) AND (tp.is_archived = false));


--
-- Name: texts; Type: VIEW; Schema: public; Owner: -
--

CREATE OR REPLACE VIEW public.texts AS
 SELECT content_texts.id,
    content_texts.slug,
    content_texts.header,
    content_texts.text
   FROM content.content_texts;


--
-- Name: token_packs; Type: VIEW; Schema: public; Owner: -
--

CREATE OR REPLACE VIEW public.token_packs AS
 SELECT token_packs.id,
    token_packs.amount,
    token_packs.currency_type_id,
    token_packs.price,
    token_packs.is_archived,
    token_packs.name,
    token_packs."order",
    token_packs.is_highlighted,
    token_packs.lifetime_days
   FROM content.token_packs
  WHERE (token_packs.is_archived = false);


--
-- Name: user_balances; Type: VIEW; Schema: public; Owner: -
--

CREATE OR REPLACE VIEW public.user_balances WITH (security_invoker='true') AS
 SELECT ub.id,
    ub.user_id,
    ub.balance_amount,
    ub.currency_type_id
   FROM (content.balances ub
     JOIN content.currency_types ct ON ((ub.currency_type_id = ct.id)))
  WHERE (ct.name = 'TOKEN'::text);


--
-- Name: user_plans; Type: VIEW; Schema: public; Owner: -
--

CREATE OR REPLACE VIEW public.user_plans WITH (security_invoker='true') AS
 SELECT up.user_id,
    up.tariff_plan_id,
    up.expired_at,
    tp.name,
    tp.duration_in_month,
    tp.tariff_info,
    tp.is_trial,
    up.truevo_subscription_id
   FROM (content.user_plans up
     JOIN content.tariff_plans tp ON ((up.tariff_plan_id = tp.id)));


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS public.users (
    id uuid NOT NULL,
    display_name text,
    status public.user_status DEFAULT 'OFFLINE'::public.user_status,
    tg_id text,
    settings extensions.hstore DEFAULT ''::extensions.hstore NOT NULL
);

ALTER TABLE ONLY public.users REPLICA IDENTITY FULL;


--
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.users IS 'Profile data for each user.';


--
-- Name: translations; Type: TABLE; Schema: translator; Owner: -
--

CREATE TABLE IF NOT EXISTS translator.translations (
    id integer NOT NULL,
    key character varying NOT NULL,
    language character varying NOT NULL,
    source_text text NOT NULL,
    translated_text text NOT NULL,
    is_verified_by_human boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    translated_text_hash character varying
);


--
-- Name: translations_id_seq; Type: SEQUENCE; Schema: translator; Owner: -
--

CREATE SEQUENCE IF NOT EXISTS translator.translations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: translations_id_seq; Type: SEQUENCE OWNED BY; Schema: translator; Owner: -
--

ALTER SEQUENCE translator.translations_id_seq OWNED BY translator.translations.id;


--
-- Name: content_blogs id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_blogs ALTER COLUMN id SET DEFAULT nextval('content.content_blogs_id_seq'::regclass);


--
-- Name: content_blogs_files id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_blogs_files ALTER COLUMN id SET DEFAULT nextval('content.content_blogs_files_id_seq'::regclass);


--
-- Name: content_character_filters id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_character_filters ALTER COLUMN id SET DEFAULT nextval('content.content_character_filters_id_seq'::regclass);


--
-- Name: content_character_filters_content_characters id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_character_filters_content_characters ALTER COLUMN id SET DEFAULT nextval('content.content_character_filters_content_characters_id_seq'::regclass);


--
-- Name: content_characters id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_characters ALTER COLUMN id SET DEFAULT nextval('content.content_characters_id_seq'::regclass);


--
-- Name: content_characters_content_tags id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_characters_content_tags ALTER COLUMN id SET DEFAULT nextval('content.content_characters_content_tags_id_seq'::regclass);


--
-- Name: content_characters_files id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_characters_files ALTER COLUMN id SET DEFAULT nextval('content.content_characters_files_id_seq'::regclass);


--
-- Name: content_contexts id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_contexts ALTER COLUMN id SET DEFAULT nextval('content.content_contexts_id_seq'::regclass);


--
-- Name: content_contexts_content_characters id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_contexts_content_characters ALTER COLUMN id SET DEFAULT nextval('content.content_contexts_content_characters_id_seq'::regclass);


--
-- Name: content_faq id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_faq ALTER COLUMN id SET DEFAULT nextval('content.content_faq_id_seq'::regclass);


--
-- Name: content_images_path id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_images_path ALTER COLUMN id SET DEFAULT nextval('content.content_images_path_id_seq'::regclass);


--
-- Name: content_locations id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_locations ALTER COLUMN id SET DEFAULT nextval('content.content_locations_id_seq'::regclass);


--
-- Name: content_locations_content_characters id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_locations_content_characters ALTER COLUMN id SET DEFAULT nextval('content.content_locations_content_characters_id_seq'::regclass);


--
-- Name: content_settings id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_settings ALTER COLUMN id SET DEFAULT nextval('content.content_settings_id_seq'::regclass);


--
-- Name: content_tags id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_tags ALTER COLUMN id SET DEFAULT nextval('content.content_tags_id_seq'::regclass);


--
-- Name: content_texts id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_texts ALTER COLUMN id SET DEFAULT nextval('content.content_texts_id_seq'::regclass);


--
-- Name: content_traits id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_traits ALTER COLUMN id SET DEFAULT nextval('content.content_traits_id_seq'::regclass);


--
-- Name: content_traits_content_characters id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.content_traits_content_characters ALTER COLUMN id SET DEFAULT nextval('content.content_traits_content_characters_id_seq'::regclass);


--
-- Name: directus_activity id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.directus_activity ALTER COLUMN id SET DEFAULT nextval('content.directus_activity_id_seq'::regclass);


--
-- Name: directus_fields id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.directus_fields ALTER COLUMN id SET DEFAULT nextval('content.directus_fields_id_seq'::regclass);


--
-- Name: directus_notifications id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.directus_notifications ALTER COLUMN id SET DEFAULT nextval('content.directus_notifications_id_seq'::regclass);


--
-- Name: directus_permissions id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.directus_permissions ALTER COLUMN id SET DEFAULT nextval('content.directus_permissions_id_seq'::regclass);


--
-- Name: directus_presets id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.directus_presets ALTER COLUMN id SET DEFAULT nextval('content.directus_presets_id_seq'::regclass);


--
-- Name: directus_relations id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.directus_relations ALTER COLUMN id SET DEFAULT nextval('content.directus_relations_id_seq'::regclass);


--
-- Name: directus_revisions id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.directus_revisions ALTER COLUMN id SET DEFAULT nextval('content.directus_revisions_id_seq'::regclass);


--
-- Name: directus_settings id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.directus_settings ALTER COLUMN id SET DEFAULT nextval('content.directus_settings_id_seq'::regclass);


--
-- Name: directus_webhooks id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.directus_webhooks ALTER COLUMN id SET DEFAULT nextval('content.directus_webhooks_id_seq'::regclass);


--
-- Name: landings id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.landings ALTER COLUMN id SET DEFAULT nextval('content.landings_id_seq'::regclass);


--
-- Name: landings_benefits_section id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.landings_benefits_section ALTER COLUMN id SET DEFAULT nextval('content.landings_benefits_section_id_seq'::regclass);


--
-- Name: landings_benefits_subsection id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.landings_benefits_subsection ALTER COLUMN id SET DEFAULT nextval('content.landings_benefits_subsection_id_seq'::regclass);


--
-- Name: landings_characters_section id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.landings_characters_section ALTER COLUMN id SET DEFAULT nextval('content.landings_characters_section_id_seq'::regclass);


--
-- Name: landings_characters_section_content_characters id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.landings_characters_section_content_characters ALTER COLUMN id SET DEFAULT nextval('content.landings_characters_section_content_characters_id_seq'::regclass);


--
-- Name: landings_conclusion_section id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.landings_conclusion_section ALTER COLUMN id SET DEFAULT nextval('content.landings_conclusion_section_id_seq'::regclass);


--
-- Name: landings_faq_section id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.landings_faq_section ALTER COLUMN id SET DEFAULT nextval('content.landings_faq_section_id_seq'::regclass);


--
-- Name: landings_faq_subsection id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.landings_faq_subsection ALTER COLUMN id SET DEFAULT nextval('content.landings_faq_subsection_id_seq'::regclass);


--
-- Name: landings_main_section id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.landings_main_section ALTER COLUMN id SET DEFAULT nextval('content.landings_main_section_id_seq'::regclass);


--
-- Name: landings_main_subsection id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.landings_main_subsection ALTER COLUMN id SET DEFAULT nextval('content.landings_main_subsection_id_seq'::regclass);


--
-- Name: landings_more_ai_section id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.landings_more_ai_section ALTER COLUMN id SET DEFAULT nextval('content.landings_more_ai_section_id_seq'::regclass);


--
-- Name: landings_more_ai_subsection id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.landings_more_ai_subsection ALTER COLUMN id SET DEFAULT nextval('content.landings_more_ai_subsection_id_seq'::regclass);


--
-- Name: landings_secondary_section id; Type: DEFAULT; Schema: content; Owner: -
--

ALTER TABLE ONLY content.landings_secondary_section ALTER COLUMN id SET DEFAULT nextval('content.landings_secondary_section_id_seq'::regclass);


--
-- Name: mktdata_raw id; Type: DEFAULT; Schema: mktdata; Owner: -
--

ALTER TABLE ONLY mktdata.mktdata_raw ALTER COLUMN id SET DEFAULT nextval('mktdata.mktdata_raw_id_seq'::regclass);


--
-- Name: translations id; Type: DEFAULT; Schema: translator; Owner: -
--

ALTER TABLE ONLY translator.translations ALTER COLUMN id SET DEFAULT nextval('translator.translations_id_seq'::regclass);


--
-- Name: balances balances_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.balances
    ADD CONSTRAINT balances_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: character_configs character_configs_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.character_configs
    ADD CONSTRAINT character_configs_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: clearings clearings_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.clearings
    ADD CONSTRAINT clearings_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_banners content_banners_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_banners
    ADD CONSTRAINT content_banners_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_blogs_files content_blogs_files_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_blogs_files
    ADD CONSTRAINT content_blogs_files_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_blogs content_blogs_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_blogs
    ADD CONSTRAINT content_blogs_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_character_filters_content_characters content_character_filters_content_characters_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_character_filters_content_characters
    ADD CONSTRAINT content_character_filters_content_characters_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_character_filters content_character_filters_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_character_filters
    ADD CONSTRAINT content_character_filters_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_character_images content_character_images_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_character_images
    ADD CONSTRAINT content_character_images_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_characters_content_tags content_characters_content_tags_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_characters_content_tags
    ADD CONSTRAINT content_characters_content_tags_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_characters_files content_characters_files_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_characters_files
    ADD CONSTRAINT content_characters_files_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_characters content_characters_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_characters
    ADD CONSTRAINT content_characters_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_contexts_content_characters content_contexts_content_characters_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_contexts_content_characters
    ADD CONSTRAINT content_contexts_content_characters_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_contexts content_contexts_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_contexts
    ADD CONSTRAINT content_contexts_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_faq content_faq_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_faq
    ADD CONSTRAINT content_faq_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_images content_images_name_unique; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_images
    ADD CONSTRAINT content_images_name_unique UNIQUE (name);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_images_path content_images_path_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_images_path
    ADD CONSTRAINT content_images_path_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_images content_images_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_images
    ADD CONSTRAINT content_images_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_locations_content_characters content_locations_content_characters_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_locations_content_characters
    ADD CONSTRAINT content_locations_content_characters_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_locations content_locations_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_locations
    ADD CONSTRAINT content_locations_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_review_categories content_review_categories_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_review_categories
    ADD CONSTRAINT content_review_categories_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_settings content_settings_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_settings
    ADD CONSTRAINT content_settings_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_tags content_tags_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_tags
    ADD CONSTRAINT content_tags_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_texts content_texts_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_texts
    ADD CONSTRAINT content_texts_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_texts content_texts_slug_unique; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_texts
    ADD CONSTRAINT content_texts_slug_unique UNIQUE (slug);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_traits_content_characters content_traits_content_characters_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_traits_content_characters
    ADD CONSTRAINT content_traits_content_characters_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_traits content_traits_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_traits
    ADD CONSTRAINT content_traits_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_webhook_data content_webhook_data_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_webhook_data
    ADD CONSTRAINT content_webhook_data_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: currency_types currency_types_name_key; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.currency_types
    ADD CONSTRAINT currency_types_name_key UNIQUE (name);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: currency_types currency_types_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.currency_types
    ADD CONSTRAINT currency_types_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_activity directus_activity_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_activity
    ADD CONSTRAINT directus_activity_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_collections directus_collections_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_collections
    ADD CONSTRAINT directus_collections_pkey PRIMARY KEY (collection);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_dashboards directus_dashboards_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_dashboards
    ADD CONSTRAINT directus_dashboards_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_extensions directus_extensions_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_extensions
    ADD CONSTRAINT directus_extensions_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_fields directus_fields_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_fields
    ADD CONSTRAINT directus_fields_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_files directus_files_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_files
    ADD CONSTRAINT directus_files_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_flows directus_flows_operation_unique; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_flows
    ADD CONSTRAINT directus_flows_operation_unique UNIQUE (operation);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_flows directus_flows_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_flows
    ADD CONSTRAINT directus_flows_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_folders directus_folders_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_folders
    ADD CONSTRAINT directus_folders_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_migrations directus_migrations_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_migrations
    ADD CONSTRAINT directus_migrations_pkey PRIMARY KEY (version);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_notifications directus_notifications_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_notifications
    ADD CONSTRAINT directus_notifications_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_operations directus_operations_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_operations
    ADD CONSTRAINT directus_operations_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_operations directus_operations_reject_unique; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_operations
    ADD CONSTRAINT directus_operations_reject_unique UNIQUE (reject);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_operations directus_operations_resolve_unique; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_operations
    ADD CONSTRAINT directus_operations_resolve_unique UNIQUE (resolve);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_panels directus_panels_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_panels
    ADD CONSTRAINT directus_panels_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_permissions directus_permissions_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_permissions
    ADD CONSTRAINT directus_permissions_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_presets directus_presets_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_presets
    ADD CONSTRAINT directus_presets_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_relations directus_relations_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_relations
    ADD CONSTRAINT directus_relations_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_revisions directus_revisions_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_revisions
    ADD CONSTRAINT directus_revisions_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_roles directus_roles_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_roles
    ADD CONSTRAINT directus_roles_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_sessions directus_sessions_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_sessions
    ADD CONSTRAINT directus_sessions_pkey PRIMARY KEY (token);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_settings directus_settings_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_settings
    ADD CONSTRAINT directus_settings_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_shares directus_shares_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_shares
    ADD CONSTRAINT directus_shares_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_translations directus_translations_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_translations
    ADD CONSTRAINT directus_translations_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_users directus_users_email_unique; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_users
    ADD CONSTRAINT directus_users_email_unique UNIQUE (email);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_users directus_users_external_identifier_unique; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_users
    ADD CONSTRAINT directus_users_external_identifier_unique UNIQUE (external_identifier);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_users directus_users_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_users
    ADD CONSTRAINT directus_users_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_users directus_users_token_unique; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_users
    ADD CONSTRAINT directus_users_token_unique UNIQUE (token);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_versions directus_versions_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_versions
    ADD CONSTRAINT directus_versions_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_webhooks directus_webhooks_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_webhooks
    ADD CONSTRAINT directus_webhooks_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: gift_codes gift_codes_code_key; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.gift_codes
    ADD CONSTRAINT gift_codes_code_key UNIQUE (code);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: gift_codes gift_codes_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.gift_codes
    ADD CONSTRAINT gift_codes_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: gift_codes_users gift_codes_users_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.gift_codes_users
    ADD CONSTRAINT gift_codes_users_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: images_user_settings images_user_settings_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.images_user_settings
    ADD CONSTRAINT images_user_settings_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: images_views images_views_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.images_views
    ADD CONSTRAINT images_views_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: invoices invoices_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.invoices
    ADD CONSTRAINT invoices_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_benefits_section landings_benefits_section_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_benefits_section
    ADD CONSTRAINT landings_benefits_section_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_benefits_subsection landings_benefits_subsection_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_benefits_subsection
    ADD CONSTRAINT landings_benefits_subsection_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_characters_section_content_characters landings_characters_section_content_characters_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_characters_section_content_characters
    ADD CONSTRAINT landings_characters_section_content_characters_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_characters_section landings_characters_section_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_characters_section
    ADD CONSTRAINT landings_characters_section_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_conclusion_section landings_conclusion_section_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_conclusion_section
    ADD CONSTRAINT landings_conclusion_section_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_faq_section landings_faq_section_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_faq_section
    ADD CONSTRAINT landings_faq_section_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_faq_subsection landings_faq_subsection_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_faq_subsection
    ADD CONSTRAINT landings_faq_subsection_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_main_section landings_main_section_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_main_section
    ADD CONSTRAINT landings_main_section_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_main_subsection landings_main_subsection_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_main_subsection
    ADD CONSTRAINT landings_main_subsection_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_more_ai_section landings_more_ai_section_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_more_ai_section
    ADD CONSTRAINT landings_more_ai_section_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_more_ai_subsection landings_more_ai_subsection_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_more_ai_subsection
    ADD CONSTRAINT landings_more_ai_subsection_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings landings_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings
    ADD CONSTRAINT landings_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_secondary_section landings_secondary_section_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_secondary_section
    ADD CONSTRAINT landings_secondary_section_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings landings_slug_unique; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings
    ADD CONSTRAINT landings_slug_unique UNIQUE (slug);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: llm_stats llm_stats_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.llm_stats
    ADD CONSTRAINT llm_stats_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: message_archive message_archive_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.message_archive
    ADD CONSTRAINT message_archive_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: paid_actions paid_actions_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.paid_actions
    ADD CONSTRAINT paid_actions_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: summaries summaries_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.summaries
    ADD CONSTRAINT summaries_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: tariff_plans tariff_plans_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.tariff_plans
    ADD CONSTRAINT tariff_plans_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: token_batches token_batches_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.token_batches
    ADD CONSTRAINT token_batches_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: token_packs token_packs_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.token_packs
    ADD CONSTRAINT token_packs_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: transactions transactions_id_unique; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.transactions
    ADD CONSTRAINT transactions_id_unique UNIQUE (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: user_plans user_plans_pkey; Type: CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.user_plans
    ADD CONSTRAINT user_plans_pkey PRIMARY KEY (user_id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: disposable_email_domains disposable_email_domains_pkey; Type: CONSTRAINT; Schema: context_images; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY context_images.disposable_email_domains
    ADD CONSTRAINT disposable_email_domains_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: image_metadata image_metadata_pkey; Type: CONSTRAINT; Schema: context_images; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY context_images.image_metadata
    ADD CONSTRAINT image_metadata_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: tag_embeddings tag_embeddings_pkey; Type: CONSTRAINT; Schema: context_images; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY context_images.tag_embeddings
    ADD CONSTRAINT tag_embeddings_pkey PRIMARY KEY (tag);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: mktdata_raw mktdata_raw_pkey; Type: CONSTRAINT; Schema: mktdata; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY mktdata.mktdata_raw
    ADD CONSTRAINT mktdata_raw_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: _blog blog_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public._blog
    ADD CONSTRAINT blog_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: channels channels_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public.channels
    ADD CONSTRAINT channels_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: _faq faq_order_key; Type: CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public._faq
    ADD CONSTRAINT faq_order_key UNIQUE ("order");
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: _faq faq_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public._faq
    ADD CONSTRAINT faq_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: notification notification_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public.notification
    ADD CONSTRAINT notification_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: translations translations_pkey; Type: CONSTRAINT; Schema: translator; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY translator.translations
    ADD CONSTRAINT translations_pkey PRIMARY KEY (id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: idx_additional_data_image_id; Type: INDEX; Schema: content; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_additional_data_image_id ON content.transactions USING btree (((additional_data ->> 'image_id'::text)));


--
-- Name: idx_user_id; Type: INDEX; Schema: content; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_user_id ON content.transactions USING btree (user_id);


--
-- Name: ix_mktdata_mktdata_raw_action; Type: INDEX; Schema: mktdata; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_mktdata_mktdata_raw_action ON mktdata.mktdata_raw USING btree (action);


--
-- Name: ix_mktdata_mktdata_raw_user_id; Type: INDEX; Schema: mktdata; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_mktdata_mktdata_raw_user_id ON mktdata.mktdata_raw USING btree (user_id);


--
-- Name: idx_messages_channel_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_messages_channel_id ON public.messages USING btree (channel_id);


--
-- Name: idx_messages_inserted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_messages_inserted_at ON public.messages USING btree (inserted_at);


--
-- Name: idx_messages_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_messages_user_id ON public.messages USING btree (user_id);


--
-- Name: idx_translations_is_verified_by_human; Type: INDEX; Schema: translator; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_translations_is_verified_by_human ON translator.translations USING btree (is_verified_by_human);


--
-- Name: idx_translations_key; Type: INDEX; Schema: translator; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_translations_key ON translator.translations USING btree (key);


--
-- Name: idx_translations_language; Type: INDEX; Schema: translator; Owner: -
--

CREATE INDEX IF NOT EXISTS idx_translations_language ON translator.translations USING btree (language);


--
-- Name: ix_translator_translations_translated_text_hash; Type: INDEX; Schema: translator; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_translator_translations_translated_text_hash ON translator.translations USING btree (translated_text_hash);


--
-- Name: translations update_translations_updated_at; Type: TRIGGER; Schema: translator; Owner: -
--

CREATE OR REPLACE TRIGGER update_translations_updated_at BEFORE UPDATE ON translator.translations FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: balances balances_currency_type_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.balances
    ADD CONSTRAINT balances_currency_type_id_fkey FOREIGN KEY (currency_type_id) REFERENCES content.currency_types(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: character_configs character_configs_background_file_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.character_configs
    ADD CONSTRAINT character_configs_background_file_id_fkey FOREIGN KEY (background_file_id) REFERENCES content.directus_files(id) ON UPDATE CASCADE ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: character_configs character_configs_character_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.character_configs
    ADD CONSTRAINT character_configs_character_id_fkey FOREIGN KEY (character_id) REFERENCES content.content_characters(id) ON UPDATE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_banners content_banners_desktop_background_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_banners
    ADD CONSTRAINT content_banners_desktop_background_foreign FOREIGN KEY (desktop_background) REFERENCES content.directus_files(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_banners content_banners_mobile_background_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_banners
    ADD CONSTRAINT content_banners_mobile_background_foreign FOREIGN KEY (mobile_background) REFERENCES content.directus_files(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_blogs_files content_blogs_files_content_blogs_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_blogs_files
    ADD CONSTRAINT content_blogs_files_content_blogs_id_foreign FOREIGN KEY (content_blogs_id) REFERENCES content.content_blogs(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_blogs_files content_blogs_files_directus_files_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_blogs_files
    ADD CONSTRAINT content_blogs_files_directus_files_id_foreign FOREIGN KEY (directus_files_id) REFERENCES content.directus_files(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_character_filters_content_characters content_character_filters_content_characte__19a18a9f_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_character_filters_content_characters
    ADD CONSTRAINT content_character_filters_content_characte__19a18a9f_foreign FOREIGN KEY (content_character_filters_id) REFERENCES content.content_character_filters(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_character_filters_content_characters content_character_filters_content_character__c7acaf0_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_character_filters_content_characters
    ADD CONSTRAINT content_character_filters_content_character__c7acaf0_foreign FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_character_images content_character_images_character_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_character_images
    ADD CONSTRAINT content_character_images_character_id_fkey FOREIGN KEY (character_id) REFERENCES content.content_characters(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_character_images content_character_images_image_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_character_images
    ADD CONSTRAINT content_character_images_image_id_fkey FOREIGN KEY (image_id) REFERENCES content.content_images(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_characters content_characters_background_image_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_characters
    ADD CONSTRAINT content_characters_background_image_id_fkey FOREIGN KEY (background_image_id) REFERENCES content.directus_files(id) ON UPDATE CASCADE ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_characters_content_tags content_characters_content_tags_content_ch__34948cee_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_characters_content_tags
    ADD CONSTRAINT content_characters_content_tags_content_ch__34948cee_foreign FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_characters_content_tags content_characters_content_tags_content_tags_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_characters_content_tags
    ADD CONSTRAINT content_characters_content_tags_content_tags_id_foreign FOREIGN KEY (content_tags_id) REFERENCES content.content_tags(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_characters_files content_characters_files_content_characters_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_characters_files
    ADD CONSTRAINT content_characters_files_content_characters_id_foreign FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON UPDATE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_characters_files content_characters_files_directus_files_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_characters_files
    ADD CONSTRAINT content_characters_files_directus_files_id_foreign FOREIGN KEY (directus_files_id) REFERENCES content.directus_files(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_characters content_characters_main_photo_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_characters
    ADD CONSTRAINT content_characters_main_photo_foreign FOREIGN KEY (main_photo) REFERENCES content.directus_files(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_characters content_characters_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_characters
    ADD CONSTRAINT content_characters_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_characters content_characters_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_characters
    ADD CONSTRAINT content_characters_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_characters content_characters_video_preview_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_characters
    ADD CONSTRAINT content_characters_video_preview_foreign FOREIGN KEY (video_preview) REFERENCES content.directus_files(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_contexts_content_characters content_contexts_content_characters_conten__36eb00cb_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_contexts_content_characters
    ADD CONSTRAINT content_contexts_content_characters_conten__36eb00cb_foreign FOREIGN KEY (content_contexts_id) REFERENCES content.content_contexts(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_contexts_content_characters content_contexts_content_characters_conten__4d6f7745_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_contexts_content_characters
    ADD CONSTRAINT content_contexts_content_characters_conten__4d6f7745_foreign FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON UPDATE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_contexts content_contexts_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_contexts
    ADD CONSTRAINT content_contexts_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_contexts content_contexts_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_contexts
    ADD CONSTRAINT content_contexts_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_images content_images_character_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_images
    ADD CONSTRAINT content_images_character_foreign FOREIGN KEY ("character") REFERENCES content.content_characters(id) ON UPDATE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_images content_images_config_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_images
    ADD CONSTRAINT content_images_config_id_fkey FOREIGN KEY (config_id) REFERENCES content.character_configs(id) ON UPDATE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_images content_images_image_blurred_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_images
    ADD CONSTRAINT content_images_image_blurred_foreign FOREIGN KEY (image_blurred) REFERENCES content.directus_files(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_images content_images_image_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_images
    ADD CONSTRAINT content_images_image_foreign FOREIGN KEY (image) REFERENCES content.directus_files(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_locations_content_characters content_locations_content_characters_conte__5c611469_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_locations_content_characters
    ADD CONSTRAINT content_locations_content_characters_conte__5c611469_foreign FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_locations_content_characters content_locations_content_characters_conten__3184201_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_locations_content_characters
    ADD CONSTRAINT content_locations_content_characters_conten__3184201_foreign FOREIGN KEY (content_locations_id) REFERENCES content.content_locations(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_locations content_locations_header_image_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_locations
    ADD CONSTRAINT content_locations_header_image_foreign FOREIGN KEY (header_image) REFERENCES content.directus_files(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_locations content_locations_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_locations
    ADD CONSTRAINT content_locations_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_locations content_locations_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_locations
    ADD CONSTRAINT content_locations_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_settings content_settings_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_settings
    ADD CONSTRAINT content_settings_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_settings content_settings_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_settings
    ADD CONSTRAINT content_settings_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: summaries content_summaries_channel_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.summaries
    ADD CONSTRAINT content_summaries_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.channels(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_tags content_tags_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_tags
    ADD CONSTRAINT content_tags_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_tags content_tags_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_tags
    ADD CONSTRAINT content_tags_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_traits_content_characters content_traits_content_characters_content___57fde464_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_traits_content_characters
    ADD CONSTRAINT content_traits_content_characters_content___57fde464_foreign FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_traits_content_characters content_traits_content_characters_content_traits_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_traits_content_characters
    ADD CONSTRAINT content_traits_content_characters_content_traits_id_foreign FOREIGN KEY (content_traits_id) REFERENCES content.content_traits(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_traits content_traits_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_traits
    ADD CONSTRAINT content_traits_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_traits content_traits_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_traits
    ADD CONSTRAINT content_traits_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_collections directus_collections_group_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_collections
    ADD CONSTRAINT directus_collections_group_foreign FOREIGN KEY ("group") REFERENCES content.directus_collections(collection);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_dashboards directus_dashboards_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_dashboards
    ADD CONSTRAINT directus_dashboards_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_files directus_files_folder_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_files
    ADD CONSTRAINT directus_files_folder_foreign FOREIGN KEY (folder) REFERENCES content.directus_folders(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_files directus_files_modified_by_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_files
    ADD CONSTRAINT directus_files_modified_by_foreign FOREIGN KEY (modified_by) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_files directus_files_uploaded_by_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_files
    ADD CONSTRAINT directus_files_uploaded_by_foreign FOREIGN KEY (uploaded_by) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_flows directus_flows_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_flows
    ADD CONSTRAINT directus_flows_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_folders directus_folders_parent_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_folders
    ADD CONSTRAINT directus_folders_parent_foreign FOREIGN KEY (parent) REFERENCES content.directus_folders(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_notifications directus_notifications_recipient_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_notifications
    ADD CONSTRAINT directus_notifications_recipient_foreign FOREIGN KEY (recipient) REFERENCES content.directus_users(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_notifications directus_notifications_sender_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_notifications
    ADD CONSTRAINT directus_notifications_sender_foreign FOREIGN KEY (sender) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_operations directus_operations_flow_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_operations
    ADD CONSTRAINT directus_operations_flow_foreign FOREIGN KEY (flow) REFERENCES content.directus_flows(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_operations directus_operations_reject_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_operations
    ADD CONSTRAINT directus_operations_reject_foreign FOREIGN KEY (reject) REFERENCES content.directus_operations(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_operations directus_operations_resolve_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_operations
    ADD CONSTRAINT directus_operations_resolve_foreign FOREIGN KEY (resolve) REFERENCES content.directus_operations(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_operations directus_operations_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_operations
    ADD CONSTRAINT directus_operations_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_panels directus_panels_dashboard_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_panels
    ADD CONSTRAINT directus_panels_dashboard_foreign FOREIGN KEY (dashboard) REFERENCES content.directus_dashboards(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_panels directus_panels_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_panels
    ADD CONSTRAINT directus_panels_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_permissions directus_permissions_role_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_permissions
    ADD CONSTRAINT directus_permissions_role_foreign FOREIGN KEY (role) REFERENCES content.directus_roles(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_presets directus_presets_role_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_presets
    ADD CONSTRAINT directus_presets_role_foreign FOREIGN KEY (role) REFERENCES content.directus_roles(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_presets directus_presets_user_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_presets
    ADD CONSTRAINT directus_presets_user_foreign FOREIGN KEY ("user") REFERENCES content.directus_users(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_revisions directus_revisions_activity_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_revisions
    ADD CONSTRAINT directus_revisions_activity_foreign FOREIGN KEY (activity) REFERENCES content.directus_activity(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_revisions directus_revisions_parent_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_revisions
    ADD CONSTRAINT directus_revisions_parent_foreign FOREIGN KEY (parent) REFERENCES content.directus_revisions(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_revisions directus_revisions_version_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_revisions
    ADD CONSTRAINT directus_revisions_version_foreign FOREIGN KEY (version) REFERENCES content.directus_versions(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_sessions directus_sessions_share_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_sessions
    ADD CONSTRAINT directus_sessions_share_foreign FOREIGN KEY (share) REFERENCES content.directus_shares(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_sessions directus_sessions_user_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_sessions
    ADD CONSTRAINT directus_sessions_user_foreign FOREIGN KEY ("user") REFERENCES content.directus_users(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_settings directus_settings_project_logo_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_settings
    ADD CONSTRAINT directus_settings_project_logo_foreign FOREIGN KEY (project_logo) REFERENCES content.directus_files(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_settings directus_settings_public_background_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_settings
    ADD CONSTRAINT directus_settings_public_background_foreign FOREIGN KEY (public_background) REFERENCES content.directus_files(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_settings directus_settings_public_favicon_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_settings
    ADD CONSTRAINT directus_settings_public_favicon_foreign FOREIGN KEY (public_favicon) REFERENCES content.directus_files(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_settings directus_settings_public_foreground_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_settings
    ADD CONSTRAINT directus_settings_public_foreground_foreign FOREIGN KEY (public_foreground) REFERENCES content.directus_files(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_settings directus_settings_storage_default_folder_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_settings
    ADD CONSTRAINT directus_settings_storage_default_folder_foreign FOREIGN KEY (storage_default_folder) REFERENCES content.directus_folders(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_shares directus_shares_collection_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_shares
    ADD CONSTRAINT directus_shares_collection_foreign FOREIGN KEY (collection) REFERENCES content.directus_collections(collection) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_shares directus_shares_role_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_shares
    ADD CONSTRAINT directus_shares_role_foreign FOREIGN KEY (role) REFERENCES content.directus_roles(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_shares directus_shares_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_shares
    ADD CONSTRAINT directus_shares_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_users directus_users_role_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_users
    ADD CONSTRAINT directus_users_role_foreign FOREIGN KEY (role) REFERENCES content.directus_roles(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_versions directus_versions_collection_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_versions
    ADD CONSTRAINT directus_versions_collection_foreign FOREIGN KEY (collection) REFERENCES content.directus_collections(collection) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_versions directus_versions_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_versions
    ADD CONSTRAINT directus_versions_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: directus_versions directus_versions_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.directus_versions
    ADD CONSTRAINT directus_versions_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: transactions fk_clearing; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.transactions
    ADD CONSTRAINT fk_clearing FOREIGN KEY (clearing_id) REFERENCES content.clearings(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: content_contexts fk_first_image; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.content_contexts
    ADD CONSTRAINT fk_first_image FOREIGN KEY (first_image) REFERENCES content.content_images(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: gift_codes_users gift_codes_users_gift_code_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.gift_codes_users
    ADD CONSTRAINT gift_codes_users_gift_code_id_fkey FOREIGN KEY (gift_code_id) REFERENCES content.gift_codes(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: gift_codes_users gift_codes_users_user_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.gift_codes_users
    ADD CONSTRAINT gift_codes_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: invoices invoices_currency_type_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.invoices
    ADD CONSTRAINT invoices_currency_type_id_fkey FOREIGN KEY (currency_type_id) REFERENCES content.currency_types(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: invoices invoices_customer_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.invoices
    ADD CONSTRAINT invoices_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.users(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_benefits_section landings_benefits_section_landing_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_benefits_section
    ADD CONSTRAINT landings_benefits_section_landing_id_foreign FOREIGN KEY (landing_id) REFERENCES content.landings(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_benefits_section landings_benefits_section_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_benefits_section
    ADD CONSTRAINT landings_benefits_section_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_benefits_section landings_benefits_section_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_benefits_section
    ADD CONSTRAINT landings_benefits_section_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_benefits_subsection landings_benefits_subsection_benefits_section_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_benefits_subsection
    ADD CONSTRAINT landings_benefits_subsection_benefits_section_id_foreign FOREIGN KEY (benefits_section_id) REFERENCES content.landings_benefits_section(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_benefits_subsection landings_benefits_subsection_image_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_benefits_subsection
    ADD CONSTRAINT landings_benefits_subsection_image_foreign FOREIGN KEY (image) REFERENCES content.directus_files(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_benefits_subsection landings_benefits_subsection_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_benefits_subsection
    ADD CONSTRAINT landings_benefits_subsection_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_benefits_subsection landings_benefits_subsection_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_benefits_subsection
    ADD CONSTRAINT landings_benefits_subsection_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_characters_section_content_characters landings_characters_section_content_charac__51b63aa1_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_characters_section_content_characters
    ADD CONSTRAINT landings_characters_section_content_charac__51b63aa1_foreign FOREIGN KEY (landings_characters_section_id) REFERENCES content.landings_characters_section(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_characters_section_content_characters landings_characters_section_content_charac__71362a1c_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_characters_section_content_characters
    ADD CONSTRAINT landings_characters_section_content_charac__71362a1c_foreign FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_characters_section landings_characters_section_landing_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_characters_section
    ADD CONSTRAINT landings_characters_section_landing_id_foreign FOREIGN KEY (landing_id) REFERENCES content.landings(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_characters_section landings_characters_section_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_characters_section
    ADD CONSTRAINT landings_characters_section_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_characters_section landings_characters_section_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_characters_section
    ADD CONSTRAINT landings_characters_section_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_conclusion_section landings_conclusion_section_landing_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_conclusion_section
    ADD CONSTRAINT landings_conclusion_section_landing_id_foreign FOREIGN KEY (landing_id) REFERENCES content.landings(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_conclusion_section landings_conclusion_section_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_conclusion_section
    ADD CONSTRAINT landings_conclusion_section_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_conclusion_section landings_conclusion_section_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_conclusion_section
    ADD CONSTRAINT landings_conclusion_section_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_faq_section landings_faq_section_landing_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_faq_section
    ADD CONSTRAINT landings_faq_section_landing_id_foreign FOREIGN KEY (landing_id) REFERENCES content.landings(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_faq_section landings_faq_section_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_faq_section
    ADD CONSTRAINT landings_faq_section_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_faq_section landings_faq_section_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_faq_section
    ADD CONSTRAINT landings_faq_section_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_faq_subsection landings_faq_subsection_faq_section_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_faq_subsection
    ADD CONSTRAINT landings_faq_subsection_faq_section_id_foreign FOREIGN KEY (faq_section_id) REFERENCES content.landings_faq_section(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_faq_subsection landings_faq_subsection_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_faq_subsection
    ADD CONSTRAINT landings_faq_subsection_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_faq_subsection landings_faq_subsection_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_faq_subsection
    ADD CONSTRAINT landings_faq_subsection_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings landings_main_image_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings
    ADD CONSTRAINT landings_main_image_foreign FOREIGN KEY (main_image) REFERENCES content.directus_files(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_main_section landings_main_section_landing_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_main_section
    ADD CONSTRAINT landings_main_section_landing_id_foreign FOREIGN KEY (landing_id) REFERENCES content.landings(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_main_section landings_main_section_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_main_section
    ADD CONSTRAINT landings_main_section_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_main_section landings_main_section_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_main_section
    ADD CONSTRAINT landings_main_section_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_main_subsection landings_main_subsection_image_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_main_subsection
    ADD CONSTRAINT landings_main_subsection_image_foreign FOREIGN KEY (image) REFERENCES content.directus_files(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_main_subsection landings_main_subsection_landings_main_section_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_main_subsection
    ADD CONSTRAINT landings_main_subsection_landings_main_section_id_foreign FOREIGN KEY (landings_main_section_id) REFERENCES content.landings_main_section(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_main_subsection landings_main_subsection_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_main_subsection
    ADD CONSTRAINT landings_main_subsection_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_main_subsection landings_main_subsection_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_main_subsection
    ADD CONSTRAINT landings_main_subsection_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_more_ai_section landings_more_ai_section_landing_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_more_ai_section
    ADD CONSTRAINT landings_more_ai_section_landing_id_foreign FOREIGN KEY (landing_id) REFERENCES content.landings(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_more_ai_section landings_more_ai_section_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_more_ai_section
    ADD CONSTRAINT landings_more_ai_section_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_more_ai_section landings_more_ai_section_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_more_ai_section
    ADD CONSTRAINT landings_more_ai_section_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_more_ai_subsection landings_more_ai_subsection_more_ai_section_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_more_ai_subsection
    ADD CONSTRAINT landings_more_ai_subsection_more_ai_section_id_foreign FOREIGN KEY (more_ai_section_id) REFERENCES content.landings_more_ai_section(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_more_ai_subsection landings_more_ai_subsection_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_more_ai_subsection
    ADD CONSTRAINT landings_more_ai_subsection_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_more_ai_subsection landings_more_ai_subsection_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_more_ai_subsection
    ADD CONSTRAINT landings_more_ai_subsection_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_secondary_section landings_secondary_section_landing_id_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_secondary_section
    ADD CONSTRAINT landings_secondary_section_landing_id_foreign FOREIGN KEY (landing_id) REFERENCES content.landings(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_secondary_section landings_secondary_section_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_secondary_section
    ADD CONSTRAINT landings_secondary_section_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings_secondary_section landings_secondary_section_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings_secondary_section
    ADD CONSTRAINT landings_secondary_section_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings landings_user_created_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings
    ADD CONSTRAINT landings_user_created_foreign FOREIGN KEY (user_created) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: landings landings_user_updated_foreign; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.landings
    ADD CONSTRAINT landings_user_updated_foreign FOREIGN KEY (user_updated) REFERENCES content.directus_users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: tariff_plans tariff_plans_currency_type_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.tariff_plans
    ADD CONSTRAINT tariff_plans_currency_type_id_fkey FOREIGN KEY (currency_type_id) REFERENCES content.currency_types(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: token_batches token_batches_user_plans_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.token_batches
    ADD CONSTRAINT token_batches_user_plans_id_fkey FOREIGN KEY (user_plans_id) REFERENCES content.user_plans(user_id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: token_packs token_packs_currency_type_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.token_packs
    ADD CONSTRAINT token_packs_currency_type_id_fkey FOREIGN KEY (currency_type_id) REFERENCES content.currency_types(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: user_plans user_plans_tariff_plan_id_fkey; Type: FK CONSTRAINT; Schema: content; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY content.user_plans
    ADD CONSTRAINT user_plans_tariff_plan_id_fkey FOREIGN KEY (tariff_plan_id) REFERENCES content.tariff_plans(id) ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: channels channels_char_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public.channels
    ADD CONSTRAINT channels_char_id_fkey FOREIGN KEY (char_id) REFERENCES content.content_characters(id) ON UPDATE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: channels channels_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public.channels
    ADD CONSTRAINT channels_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: messages messages_channel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.channels(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: messages messages_char_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_char_id_fkey FOREIGN KEY (char_id) REFERENCES content.content_characters(id) ON UPDATE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: messages messages_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: notification notification_channel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public.notification
    ADD CONSTRAINT notification_channel_id_fkey FOREIGN KEY (channel_id) REFERENCES public.channels(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: notification notification_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public.notification
    ADD CONSTRAINT notification_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: channels public_channels_current_char_context_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public.channels
    ADD CONSTRAINT public_channels_current_char_context_fkey FOREIGN KEY (current_char_context) REFERENCES content.content_contexts(id) ON UPDATE CASCADE ON DELETE SET NULL;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: users users_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

DO $mig$
BEGIN
ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN duplicate_table THEN NULL;
    WHEN invalid_table_definition THEN NULL;
END $mig$;



--
-- Name: balances Allow insert to authenticated; Type: POLICY; Schema: content; Owner: -
--

DO $mig$
BEGIN
CREATE POLICY "Allow insert to authenticated" ON content.balances FOR INSERT TO service_role, postgres, supabase_auth_admin WITH CHECK (true);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: user_plans Allow insert to authenticated; Type: POLICY; Schema: content; Owner: -
--

DO $mig$
BEGIN
CREATE POLICY "Allow insert to authenticated" ON content.user_plans FOR INSERT TO service_role, postgres, supabase_auth_admin WITH CHECK (true);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: balances Allow read user balances; Type: POLICY; Schema: content; Owner: -
--

DO $mig$
BEGIN
CREATE POLICY "Allow read user balances" ON content.balances FOR SELECT USING ((( SELECT auth.uid() AS uid) = user_id));
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: balances Allow select for auth; Type: POLICY; Schema: content; Owner: -
--

DO $mig$
BEGIN
CREATE POLICY "Allow select for auth" ON content.balances FOR SELECT TO supabase_auth_admin USING (true);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: balances Allow update to authenticated; Type: POLICY; Schema: content; Owner: -
--

DO $mig$
BEGIN
CREATE POLICY "Allow update to authenticated" ON content.balances FOR UPDATE TO service_role, postgres, supabase_auth_admin USING (true);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: user_plans Read access to user plan; Type: POLICY; Schema: content; Owner: -
--

DO $mig$
BEGIN
CREATE POLICY "Read access to user plan" ON content.user_plans FOR SELECT USING ((( SELECT auth.uid() AS uid) = user_id));
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: balances; Type: ROW SECURITY; Schema: content; Owner: -
--

ALTER TABLE content.balances ENABLE ROW LEVEL SECURITY;

--
-- Name: user_plans; Type: ROW SECURITY; Schema: content; Owner: -
--

ALTER TABLE content.user_plans ENABLE ROW LEVEL SECURITY;

--
-- Name: disposable_email_domains; Type: ROW SECURITY; Schema: context_images; Owner: -
--

ALTER TABLE context_images.disposable_email_domains ENABLE ROW LEVEL SECURITY;

--
-- Name: channels Allow read access to channels ; Type: POLICY; Schema: public; Owner: -
--

DO $mig$
BEGIN
CREATE POLICY "Allow read access to channels " ON public.channels FOR SELECT USING ((auth.uid() = user_id));
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: messages Allow read access to messages; Type: POLICY; Schema: public; Owner: -
--

DO $mig$
BEGIN
CREATE POLICY "Allow read access to messages" ON public.messages FOR SELECT USING ((EXISTS ( SELECT 1
   FROM public.channels c
  WHERE ((c.id = messages.channel_id) AND (c.user_id = auth.uid())))));
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: notification Enable delete for users based on user_id; Type: POLICY; Schema: public; Owner: -
--

DO $mig$
BEGIN
CREATE POLICY "Enable delete for users based on user_id" ON public.notification FOR DELETE USING ((( SELECT auth.uid() AS uid) = user_id));
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: users Enable insert for authenticated users only; Type: POLICY; Schema: public; Owner: -
--

DO $mig$
BEGIN
CREATE POLICY "Enable insert for authenticated users only" ON public.users FOR INSERT TO service_role, postgres, supabase_auth_admin WITH CHECK ((auth.uid() IS NOT NULL));
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: notification Enable insert for users based on user_id; Type: POLICY; Schema: public; Owner: -
--

DO $mig$
BEGIN
CREATE POLICY "Enable insert for users based on user_id" ON public.notification FOR INSERT WITH CHECK ((( SELECT auth.uid() AS uid) = user_id));
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: users Enable insert to public.users for authenticated users only; Type: POLICY; Schema: public; Owner: -
--

DO $mig$
BEGIN
CREATE POLICY "Enable insert to public.users for authenticated users only" ON public.users FOR INSERT TO service_role, postgres, supabase_auth_admin WITH CHECK (true);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: notification Enable read access for owners; Type: POLICY; Schema: public; Owner: -
--

DO $mig$
BEGIN
CREATE POLICY "Enable read access for owners" ON public.notification FOR SELECT USING ((( SELECT auth.uid() AS uid) = user_id));
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $mig$;



--
-- Name: channels; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.channels ENABLE ROW LEVEL SECURITY;

--
-- Name: messages; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

--
-- Name: notification; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.notification ENABLE ROW LEVEL SECURITY;

--
-- Name: users; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

--
-- PostgreSQL database dump complete
--

