create sequence "content"."content_character_filters_content_characters_id_seq";

create sequence "content"."content_character_filters_id_seq";

create sequence "content"."content_locations_content_characters_id_seq";

create sequence "content"."content_locations_id_seq";

create table "content"."content_character_filters" (
    "id" integer not null default nextval('content.content_character_filters_id_seq'::regclass),
    "name" character varying(255)
);


create table "content"."content_character_filters_content_characters" (
    "id" integer not null default nextval('content.content_character_filters_content_characters_id_seq'::regclass),
    "content_character_filters_id" integer,
    "content_characters_id" integer
);


create table "content"."content_locations" (
    "id" integer not null default nextval('content.content_locations_id_seq'::regclass),
    "status" character varying(255) not null default 'draft'::character varying,
    "sort" integer,
    "user_created" uuid,
    "date_created" timestamp with time zone,
    "user_updated" uuid,
    "date_updated" timestamp with time zone,
    "name" character varying(255),
    "header_image" uuid,
    "description" text
);


create table "content"."content_locations_content_characters" (
    "id" integer not null default nextval('content.content_locations_content_characters_id_seq'::regclass),
    "content_locations_id" integer,
    "content_characters_id" integer
);


alter table "content"."content_texts" add column "header" character varying(255);

alter sequence "content"."content_character_filters_content_characters_id_seq" owned by "content"."content_character_filters_content_characters"."id";

alter sequence "content"."content_character_filters_id_seq" owned by "content"."content_character_filters"."id";

alter sequence "content"."content_locations_content_characters_id_seq" owned by "content"."content_locations_content_characters"."id";

alter sequence "content"."content_locations_id_seq" owned by "content"."content_locations"."id";

CREATE UNIQUE INDEX content_character_filters_content_characters_pkey ON content.content_character_filters_content_characters USING btree (id);

CREATE UNIQUE INDEX content_character_filters_pkey ON content.content_character_filters USING btree (id);

CREATE UNIQUE INDEX content_locations_content_characters_pkey ON content.content_locations_content_characters USING btree (id);

CREATE UNIQUE INDEX content_locations_pkey ON content.content_locations USING btree (id);

alter table "content"."content_character_filters" add constraint "content_character_filters_pkey" PRIMARY KEY using index "content_character_filters_pkey";

alter table "content"."content_character_filters_content_characters" add constraint "content_character_filters_content_characters_pkey" PRIMARY KEY using index "content_character_filters_content_characters_pkey";

alter table "content"."content_locations" add constraint "content_locations_pkey" PRIMARY KEY using index "content_locations_pkey";

alter table "content"."content_locations_content_characters" add constraint "content_locations_content_characters_pkey" PRIMARY KEY using index "content_locations_content_characters_pkey";

alter table "content"."content_character_filters_content_characters" add constraint "content_character_filters_content_characte__19a18a9f_foreign" FOREIGN KEY (content_character_filters_id) REFERENCES content.content_character_filters(id) ON DELETE SET NULL not valid;

alter table "content"."content_character_filters_content_characters" validate constraint "content_character_filters_content_characte__19a18a9f_foreign";

alter table "content"."content_character_filters_content_characters" add constraint "content_character_filters_content_character__c7acaf0_foreign" FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON DELETE SET NULL not valid;

alter table "content"."content_character_filters_content_characters" validate constraint "content_character_filters_content_character__c7acaf0_foreign";

alter table "content"."content_locations" add constraint "content_locations_header_image_foreign" FOREIGN KEY (header_image) REFERENCES content.directus_files(id) ON DELETE SET NULL not valid;

alter table "content"."content_locations" validate constraint "content_locations_header_image_foreign";

alter table "content"."content_locations" add constraint "content_locations_user_created_foreign" FOREIGN KEY (user_created) REFERENCES content.directus_users(id) not valid;

alter table "content"."content_locations" validate constraint "content_locations_user_created_foreign";

alter table "content"."content_locations" add constraint "content_locations_user_updated_foreign" FOREIGN KEY (user_updated) REFERENCES content.directus_users(id) not valid;

alter table "content"."content_locations" validate constraint "content_locations_user_updated_foreign";

alter table "content"."content_locations_content_characters" add constraint "content_locations_content_characters_conte__5c611469_foreign" FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON DELETE SET NULL not valid;

alter table "content"."content_locations_content_characters" validate constraint "content_locations_content_characters_conte__5c611469_foreign";

alter table "content"."content_locations_content_characters" add constraint "content_locations_content_characters_conten__3184201_foreign" FOREIGN KEY (content_locations_id) REFERENCES content.content_locations(id) ON DELETE SET NULL not valid;

alter table "content"."content_locations_content_characters" validate constraint "content_locations_content_characters_conten__3184201_foreign";


drop view if exists "public"."characters";

create or replace view "public"."characters" as  SELECT cc.id,
    cc.status,
    cc.sort,
    cc.user_created,
    cc.date_created,
    cc.user_updated,
    cc.date_updated,
    cc.name,
    cc.personality,
    COALESCE(array_remove(array_agg(DISTINCT ct.name), NULL::character varying), '{}'::character varying[]) AS traits,
    COALESCE(array_remove(array_agg(DISTINCT cf.name), NULL::character varying), '{}'::character varying[]) AS filters,
    COALESCE(array_remove(array_agg(DISTINCT cl.name), NULL::character varying), '{}'::character varying[]) AS localtions
   FROM ((((((content.content_characters cc
     LEFT JOIN content.content_traits_content_characters ctc ON ((cc.id = ctc.content_characters_id)))
     LEFT JOIN content.content_traits ct ON ((ctc.content_traits_id = ct.id)))
     LEFT JOIN content.content_locations_content_characters clc ON ((cc.id = clc.content_characters_id)))
     LEFT JOIN content.content_locations cl ON ((clc.content_locations_id = cl.id)))
     LEFT JOIN content.content_character_filters_content_characters cfc ON ((cc.id = cfc.content_characters_id)))
     LEFT JOIN content.content_character_filters cf ON ((cfc.content_character_filters_id = cf.id)))
  GROUP BY cc.id;



