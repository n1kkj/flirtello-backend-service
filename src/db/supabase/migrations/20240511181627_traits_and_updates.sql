create sequence "content"."content_traits_content_characters_id_seq";

create sequence "content"."content_traits_id_seq";

create table "content"."content_traits" (
    "id" integer not null default nextval('content.content_traits_id_seq'::regclass),
    "status" character varying(255) not null default 'draft'::character varying,
    "sort" integer,
    "user_created" uuid,
    "date_created" timestamp with time zone,
    "user_updated" uuid,
    "date_updated" timestamp with time zone,
    "name" character varying(255)
);


create table "content"."content_traits_content_characters" (
    "id" integer not null default nextval('content.content_traits_content_characters_id_seq'::regclass),
    "content_traits_id" integer,
    "content_characters_id" integer
);


alter table "content"."content_characters" add column "personality" text;

alter table "content"."content_contexts" add column "first_message" text;

alter table "content"."content_contexts" add column "scenario" text;

alter sequence "content"."content_traits_content_characters_id_seq" owned by "content"."content_traits_content_characters"."id";

alter sequence "content"."content_traits_id_seq" owned by "content"."content_traits"."id";

CREATE UNIQUE INDEX content_traits_content_characters_pkey ON content.content_traits_content_characters USING btree (id);

CREATE UNIQUE INDEX content_traits_pkey ON content.content_traits USING btree (id);

alter table "content"."content_traits" add constraint "content_traits_pkey" PRIMARY KEY using index "content_traits_pkey";

alter table "content"."content_traits_content_characters" add constraint "content_traits_content_characters_pkey" PRIMARY KEY using index "content_traits_content_characters_pkey";

alter table "content"."content_traits" add constraint "content_traits_user_created_foreign" FOREIGN KEY (user_created) REFERENCES content.directus_users(id) not valid;

alter table "content"."content_traits" validate constraint "content_traits_user_created_foreign";

alter table "content"."content_traits" add constraint "content_traits_user_updated_foreign" FOREIGN KEY (user_updated) REFERENCES content.directus_users(id) not valid;

alter table "content"."content_traits" validate constraint "content_traits_user_updated_foreign";

alter table "content"."content_traits_content_characters" add constraint "content_traits_content_characters_content___57fde464_foreign" FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON DELETE SET NULL not valid;

alter table "content"."content_traits_content_characters" validate constraint "content_traits_content_characters_content___57fde464_foreign";

alter table "content"."content_traits_content_characters" add constraint "content_traits_content_characters_content_traits_id_foreign" FOREIGN KEY (content_traits_id) REFERENCES content.content_traits(id) ON DELETE SET NULL not valid;

alter table "content"."content_traits_content_characters" validate constraint "content_traits_content_characters_content_traits_id_foreign";


--
-- PostgreSQL database dump
--

-- Dumped from database version 15.1 (Ubuntu 15.1-1.pgdg20.04+1)
-- Dumped by pg_dump version 16.2

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
-- Data for Name: content_traits; Type: TABLE DATA; Schema: content; Owner: postgres
--

INSERT INTO content.content_traits (id, status, sort, user_created, date_created, user_updated, date_updated, name) VALUES (2, 'published', NULL, '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 17:57:50.333+00', NULL, NULL, 'Tender');
INSERT INTO content.content_traits (id, status, sort, user_created, date_created, user_updated, date_updated, name) VALUES (1, 'published', NULL, '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 17:57:50.304+00', '7abd9c74-08e4-44dc-aaad-69f83f8f9e0b', '2024-05-11 18:05:46.854+00', 'Horny');


--
-- Data for Name: content_traits_content_characters; Type: TABLE DATA; Schema: content; Owner: postgres
--

INSERT INTO content.content_traits_content_characters (id, content_traits_id, content_characters_id) VALUES (1, 1, 1);
INSERT INTO content.content_traits_content_characters (id, content_traits_id, content_characters_id) VALUES (3, 2, 1);
INSERT INTO content.content_traits_content_characters (id, content_traits_id, content_characters_id) VALUES (2, NULL, NULL);


--
-- Name: content_traits_content_characters_id_seq; Type: SEQUENCE SET; Schema: content; Owner: postgres
--

SELECT pg_catalog.setval('content.content_traits_content_characters_id_seq', 3, true);


--
-- Name: content_traits_id_seq; Type: SEQUENCE SET; Schema: content; Owner: postgres
--

SELECT pg_catalog.setval('content.content_traits_id_seq', 2, true);


--
-- PostgreSQL database dump complete
--

