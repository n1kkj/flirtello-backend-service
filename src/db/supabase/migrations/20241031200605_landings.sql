create sequence "content"."landings_benefits_section_id_seq";

create sequence "content"."landings_benefits_subsection_id_seq";

create sequence "content"."landings_characters_section_content_characters_id_seq";

create sequence "content"."landings_characters_section_id_seq";

create sequence "content"."landings_conclusion_section_id_seq";

create sequence "content"."landings_faq_section_id_seq";

create sequence "content"."landings_faq_subsection_id_seq";

create sequence "content"."landings_id_seq";

create sequence "content"."landings_main_section_id_seq";

create sequence "content"."landings_main_subsection_id_seq";

create sequence "content"."landings_more_ai_section_id_seq";

create sequence "content"."landings_more_ai_subsection_id_seq";

create sequence "content"."landings_secondary_section_id_seq";

create table "content"."landings" (
    "id" integer not null default nextval('content.landings_id_seq'::regclass),
    "status" character varying(255) not null default 'draft'::character varying,
    "user_created" uuid,
    "date_created" timestamp with time zone,
    "user_updated" uuid,
    "date_updated" timestamp with time zone,
    "main_title" character varying(255) default 'NSWF AI Chat'::character varying,
    "main_subtitle" character varying(255) default 'Explore the World of Al Sexting: Your Guide to Flirtello.com'::character varying,
    "main_image" uuid
);


create table "content"."landings_benefits_section" (
    "id" integer not null default nextval('content.landings_benefits_section_id_seq'::regclass),
    "sort" integer,
    "user_created" uuid,
    "date_created" timestamp with time zone,
    "user_updated" uuid,
    "date_updated" timestamp with time zone,
    "title" character varying(255) default 'Benefits of Using the NSFW Al Chat Platform'::character varying,
    "subtitle" character varying(255) default 'Embracing the world of Al sexting unlocks numerous benefits:'::character varying,
    "button_text" character varying(255) default 'Try it for free!'::character varying,
    "button_link" character varying(255),
    "landing_id" integer
);


create table "content"."landings_benefits_subsection" (
    "id" integer not null default nextval('content.landings_benefits_subsection_id_seq'::regclass),
    "status" character varying(255) not null default 'draft'::character varying,
    "sort" integer,
    "user_created" uuid,
    "date_created" timestamp with time zone,
    "user_updated" uuid,
    "date_updated" timestamp with time zone,
    "title" character varying(255) default NULL::character varying,
    "text" character varying(255),
    "image" uuid,
    "benefits_section_id" integer
);


create table "content"."landings_characters_section" (
    "id" integer not null default nextval('content.landings_characters_section_id_seq'::regclass),
    "sort" integer,
    "user_created" uuid,
    "date_created" timestamp with time zone,
    "user_updated" uuid,
    "date_updated" timestamp with time zone,
    "title" character varying(255) default 'Characters'::character varying,
    "landing_id" integer
);


create table "content"."landings_characters_section_content_characters" (
    "id" integer not null default nextval('content.landings_characters_section_content_characters_id_seq'::regclass),
    "landings_characters_section_id" integer,
    "content_characters_id" integer,
    "sort" integer
);


create table "content"."landings_conclusion_section" (
    "id" integer not null default nextval('content.landings_conclusion_section_id_seq'::regclass),
    "sort" integer,
    "user_created" uuid,
    "date_created" timestamp with time zone,
    "user_updated" uuid,
    "date_updated" timestamp with time zone,
    "title" character varying(255),
    "text" character varying(255),
    "button_text" character varying(255) default 'Try it for free!'::character varying,
    "button_link" character varying(255),
    "landing_id" integer
);


create table "content"."landings_faq_section" (
    "id" integer not null default nextval('content.landings_faq_section_id_seq'::regclass),
    "sort" integer,
    "user_created" uuid,
    "date_created" timestamp with time zone,
    "user_updated" uuid,
    "date_updated" timestamp with time zone,
    "title" character varying(255) default 'Q&A Block'::character varying,
    "subtitle" character varying(255) default 'Your NSFW Character Al Chat Questions Answered'::character varying,
    "landing_id" integer
);


create table "content"."landings_faq_subsection" (
    "id" integer not null default nextval('content.landings_faq_subsection_id_seq'::regclass),
    "sort" integer,
    "user_created" uuid,
    "date_created" timestamp with time zone,
    "user_updated" uuid,
    "date_updated" timestamp with time zone,
    "question" character varying(255),
    "answer" character varying(255),
    "faq_section_id" integer
);


create table "content"."landings_main_section" (
    "id" integer not null default nextval('content.landings_main_section_id_seq'::regclass),
    "sort" integer,
    "user_created" uuid,
    "date_created" timestamp with time zone,
    "user_updated" uuid,
    "date_updated" timestamp with time zone,
    "landing_id" integer
);


create table "content"."landings_main_subsection" (
    "id" integer not null default nextval('content.landings_main_subsection_id_seq'::regclass),
    "sort" integer,
    "user_created" uuid,
    "date_created" timestamp with time zone,
    "user_updated" uuid,
    "date_updated" timestamp with time zone,
    "title" character varying(255),
    "text" character varying(255),
    "button_text" character varying(255) default 'Try it for free!'::character varying,
    "button_link" character varying(255),
    "landings_main_section_id" integer
);


create table "content"."landings_more_ai_section" (
    "id" integer not null default nextval('content.landings_more_ai_section_id_seq'::regclass),
    "sort" integer,
    "user_created" uuid,
    "date_created" timestamp with time zone,
    "user_updated" uuid,
    "date_updated" timestamp with time zone,
    "title" character varying(255) default 'More NSFW Al Chat with Flirtello.com'::character varying,
    "landing_id" integer
);


create table "content"."landings_more_ai_subsection" (
    "id" integer not null default nextval('content.landings_more_ai_subsection_id_seq'::regclass),
    "sort" integer,
    "user_created" uuid,
    "date_created" timestamp with time zone,
    "user_updated" uuid,
    "date_updated" timestamp with time zone,
    "button_text" character varying(255),
    "more_ai_section_id" integer
);


create table "content"."landings_secondary_section" (
    "id" integer not null default nextval('content.landings_secondary_section_id_seq'::regclass),
    "sort" integer,
    "user_created" uuid,
    "date_created" timestamp with time zone,
    "user_updated" uuid,
    "date_updated" timestamp with time zone,
    "title" character varying(255),
    "text" character varying(255),
    "button_text" character varying(255) default 'Try it for free!'::character varying,
    "button_link" character varying(255),
    "landing_id" integer
);


alter table "content"."content_banners" alter column "is_active" drop not null;

alter table "content"."paid_actions" alter column "is_archived" drop not null;

alter table "content"."paid_actions" alter column "is_public" drop not null;

alter table "content"."tariff_plans" alter column "is_archived" drop not null;

alter table "content"."tariff_plans" alter column "is_trial" drop not null;

alter table "content"."token_packs" alter column "is_archived" drop not null;

alter sequence "content"."landings_benefits_section_id_seq" owned by "content"."landings_benefits_section"."id";

alter sequence "content"."landings_benefits_subsection_id_seq" owned by "content"."landings_benefits_subsection"."id";

alter sequence "content"."landings_characters_section_content_characters_id_seq" owned by "content"."landings_characters_section_content_characters"."id";

alter sequence "content"."landings_characters_section_id_seq" owned by "content"."landings_characters_section"."id";

alter sequence "content"."landings_conclusion_section_id_seq" owned by "content"."landings_conclusion_section"."id";

alter sequence "content"."landings_faq_section_id_seq" owned by "content"."landings_faq_section"."id";

alter sequence "content"."landings_faq_subsection_id_seq" owned by "content"."landings_faq_subsection"."id";

alter sequence "content"."landings_id_seq" owned by "content"."landings"."id";

alter sequence "content"."landings_main_section_id_seq" owned by "content"."landings_main_section"."id";

alter sequence "content"."landings_main_subsection_id_seq" owned by "content"."landings_main_subsection"."id";

alter sequence "content"."landings_more_ai_section_id_seq" owned by "content"."landings_more_ai_section"."id";

alter sequence "content"."landings_more_ai_subsection_id_seq" owned by "content"."landings_more_ai_subsection"."id";

alter sequence "content"."landings_secondary_section_id_seq" owned by "content"."landings_secondary_section"."id";

CREATE UNIQUE INDEX landings_benefits_section_pkey ON content.landings_benefits_section USING btree (id);

CREATE UNIQUE INDEX landings_benefits_subsection_pkey ON content.landings_benefits_subsection USING btree (id);

CREATE UNIQUE INDEX landings_characters_section_content_characters_pkey ON content.landings_characters_section_content_characters USING btree (id);

CREATE UNIQUE INDEX landings_characters_section_pkey ON content.landings_characters_section USING btree (id);

CREATE UNIQUE INDEX landings_conclusion_section_pkey ON content.landings_conclusion_section USING btree (id);

CREATE UNIQUE INDEX landings_faq_section_pkey ON content.landings_faq_section USING btree (id);

CREATE UNIQUE INDEX landings_faq_subsection_pkey ON content.landings_faq_subsection USING btree (id);

CREATE UNIQUE INDEX landings_main_section_pkey ON content.landings_main_section USING btree (id);

CREATE UNIQUE INDEX landings_main_subsection_pkey ON content.landings_main_subsection USING btree (id);

CREATE UNIQUE INDEX landings_more_ai_section_pkey ON content.landings_more_ai_section USING btree (id);

CREATE UNIQUE INDEX landings_more_ai_subsection_pkey ON content.landings_more_ai_subsection USING btree (id);

CREATE UNIQUE INDEX landings_pkey ON content.landings USING btree (id);

CREATE UNIQUE INDEX landings_secondary_section_pkey ON content.landings_secondary_section USING btree (id);

alter table "content"."landings" add constraint "landings_pkey" PRIMARY KEY using index "landings_pkey";

alter table "content"."landings_benefits_section" add constraint "landings_benefits_section_pkey" PRIMARY KEY using index "landings_benefits_section_pkey";

alter table "content"."landings_benefits_subsection" add constraint "landings_benefits_subsection_pkey" PRIMARY KEY using index "landings_benefits_subsection_pkey";

alter table "content"."landings_characters_section" add constraint "landings_characters_section_pkey" PRIMARY KEY using index "landings_characters_section_pkey";

alter table "content"."landings_characters_section_content_characters" add constraint "landings_characters_section_content_characters_pkey" PRIMARY KEY using index "landings_characters_section_content_characters_pkey";

alter table "content"."landings_conclusion_section" add constraint "landings_conclusion_section_pkey" PRIMARY KEY using index "landings_conclusion_section_pkey";

alter table "content"."landings_faq_section" add constraint "landings_faq_section_pkey" PRIMARY KEY using index "landings_faq_section_pkey";

alter table "content"."landings_faq_subsection" add constraint "landings_faq_subsection_pkey" PRIMARY KEY using index "landings_faq_subsection_pkey";

alter table "content"."landings_main_section" add constraint "landings_main_section_pkey" PRIMARY KEY using index "landings_main_section_pkey";

alter table "content"."landings_main_subsection" add constraint "landings_main_subsection_pkey" PRIMARY KEY using index "landings_main_subsection_pkey";

alter table "content"."landings_more_ai_section" add constraint "landings_more_ai_section_pkey" PRIMARY KEY using index "landings_more_ai_section_pkey";

alter table "content"."landings_more_ai_subsection" add constraint "landings_more_ai_subsection_pkey" PRIMARY KEY using index "landings_more_ai_subsection_pkey";

alter table "content"."landings_secondary_section" add constraint "landings_secondary_section_pkey" PRIMARY KEY using index "landings_secondary_section_pkey";

alter table "content"."landings" add constraint "landings_main_image_foreign" FOREIGN KEY (main_image) REFERENCES content.directus_files(id) ON DELETE SET NULL not valid;

alter table "content"."landings" validate constraint "landings_main_image_foreign";

alter table "content"."landings" add constraint "landings_user_created_foreign" FOREIGN KEY (user_created) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings" validate constraint "landings_user_created_foreign";

alter table "content"."landings" add constraint "landings_user_updated_foreign" FOREIGN KEY (user_updated) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings" validate constraint "landings_user_updated_foreign";

alter table "content"."landings_benefits_section" add constraint "landings_benefits_section_landing_id_foreign" FOREIGN KEY (landing_id) REFERENCES content.landings(id) ON DELETE SET NULL not valid;

alter table "content"."landings_benefits_section" validate constraint "landings_benefits_section_landing_id_foreign";

alter table "content"."landings_benefits_section" add constraint "landings_benefits_section_user_created_foreign" FOREIGN KEY (user_created) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_benefits_section" validate constraint "landings_benefits_section_user_created_foreign";

alter table "content"."landings_benefits_section" add constraint "landings_benefits_section_user_updated_foreign" FOREIGN KEY (user_updated) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_benefits_section" validate constraint "landings_benefits_section_user_updated_foreign";

alter table "content"."landings_benefits_subsection" add constraint "landings_benefits_subsection_benefits_section_id_foreign" FOREIGN KEY (benefits_section_id) REFERENCES content.landings_benefits_section(id) ON DELETE SET NULL not valid;

alter table "content"."landings_benefits_subsection" validate constraint "landings_benefits_subsection_benefits_section_id_foreign";

alter table "content"."landings_benefits_subsection" add constraint "landings_benefits_subsection_image_foreign" FOREIGN KEY (image) REFERENCES content.directus_files(id) ON DELETE SET NULL not valid;

alter table "content"."landings_benefits_subsection" validate constraint "landings_benefits_subsection_image_foreign";

alter table "content"."landings_benefits_subsection" add constraint "landings_benefits_subsection_user_created_foreign" FOREIGN KEY (user_created) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_benefits_subsection" validate constraint "landings_benefits_subsection_user_created_foreign";

alter table "content"."landings_benefits_subsection" add constraint "landings_benefits_subsection_user_updated_foreign" FOREIGN KEY (user_updated) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_benefits_subsection" validate constraint "landings_benefits_subsection_user_updated_foreign";

alter table "content"."landings_characters_section" add constraint "landings_characters_section_landing_id_foreign" FOREIGN KEY (landing_id) REFERENCES content.landings(id) ON DELETE SET NULL not valid;

alter table "content"."landings_characters_section" validate constraint "landings_characters_section_landing_id_foreign";

alter table "content"."landings_characters_section" add constraint "landings_characters_section_user_created_foreign" FOREIGN KEY (user_created) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_characters_section" validate constraint "landings_characters_section_user_created_foreign";

alter table "content"."landings_characters_section" add constraint "landings_characters_section_user_updated_foreign" FOREIGN KEY (user_updated) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_characters_section" validate constraint "landings_characters_section_user_updated_foreign";

alter table "content"."landings_characters_section_content_characters" add constraint "landings_characters_section_content_charac__51b63aa1_foreign" FOREIGN KEY (landings_characters_section_id) REFERENCES content.landings_characters_section(id) ON DELETE SET NULL not valid;

alter table "content"."landings_characters_section_content_characters" validate constraint "landings_characters_section_content_charac__51b63aa1_foreign";

alter table "content"."landings_characters_section_content_characters" add constraint "landings_characters_section_content_charac__71362a1c_foreign" FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON DELETE SET NULL not valid;

alter table "content"."landings_characters_section_content_characters" validate constraint "landings_characters_section_content_charac__71362a1c_foreign";

alter table "content"."landings_conclusion_section" add constraint "landings_conclusion_section_landing_id_foreign" FOREIGN KEY (landing_id) REFERENCES content.landings(id) ON DELETE SET NULL not valid;

alter table "content"."landings_conclusion_section" validate constraint "landings_conclusion_section_landing_id_foreign";

alter table "content"."landings_conclusion_section" add constraint "landings_conclusion_section_user_created_foreign" FOREIGN KEY (user_created) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_conclusion_section" validate constraint "landings_conclusion_section_user_created_foreign";

alter table "content"."landings_conclusion_section" add constraint "landings_conclusion_section_user_updated_foreign" FOREIGN KEY (user_updated) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_conclusion_section" validate constraint "landings_conclusion_section_user_updated_foreign";

alter table "content"."landings_faq_section" add constraint "landings_faq_section_landing_id_foreign" FOREIGN KEY (landing_id) REFERENCES content.landings(id) ON DELETE SET NULL not valid;

alter table "content"."landings_faq_section" validate constraint "landings_faq_section_landing_id_foreign";

alter table "content"."landings_faq_section" add constraint "landings_faq_section_user_created_foreign" FOREIGN KEY (user_created) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_faq_section" validate constraint "landings_faq_section_user_created_foreign";

alter table "content"."landings_faq_section" add constraint "landings_faq_section_user_updated_foreign" FOREIGN KEY (user_updated) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_faq_section" validate constraint "landings_faq_section_user_updated_foreign";

alter table "content"."landings_faq_subsection" add constraint "landings_faq_subsection_faq_section_id_foreign" FOREIGN KEY (faq_section_id) REFERENCES content.landings_faq_section(id) ON DELETE SET NULL not valid;

alter table "content"."landings_faq_subsection" validate constraint "landings_faq_subsection_faq_section_id_foreign";

alter table "content"."landings_faq_subsection" add constraint "landings_faq_subsection_user_created_foreign" FOREIGN KEY (user_created) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_faq_subsection" validate constraint "landings_faq_subsection_user_created_foreign";

alter table "content"."landings_faq_subsection" add constraint "landings_faq_subsection_user_updated_foreign" FOREIGN KEY (user_updated) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_faq_subsection" validate constraint "landings_faq_subsection_user_updated_foreign";

alter table "content"."landings_main_section" add constraint "landings_main_section_landing_id_foreign" FOREIGN KEY (landing_id) REFERENCES content.landings(id) ON DELETE SET NULL not valid;

alter table "content"."landings_main_section" validate constraint "landings_main_section_landing_id_foreign";

alter table "content"."landings_main_section" add constraint "landings_main_section_user_created_foreign" FOREIGN KEY (user_created) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_main_section" validate constraint "landings_main_section_user_created_foreign";

alter table "content"."landings_main_section" add constraint "landings_main_section_user_updated_foreign" FOREIGN KEY (user_updated) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_main_section" validate constraint "landings_main_section_user_updated_foreign";

alter table "content"."landings_main_subsection" add constraint "landings_main_subsection_landings_main_section_id_foreign" FOREIGN KEY (landings_main_section_id) REFERENCES content.landings_main_section(id) ON DELETE SET NULL not valid;

alter table "content"."landings_main_subsection" validate constraint "landings_main_subsection_landings_main_section_id_foreign";

alter table "content"."landings_main_subsection" add constraint "landings_main_subsection_user_created_foreign" FOREIGN KEY (user_created) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_main_subsection" validate constraint "landings_main_subsection_user_created_foreign";

alter table "content"."landings_main_subsection" add constraint "landings_main_subsection_user_updated_foreign" FOREIGN KEY (user_updated) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_main_subsection" validate constraint "landings_main_subsection_user_updated_foreign";

alter table "content"."landings_more_ai_section" add constraint "landings_more_ai_section_landing_id_foreign" FOREIGN KEY (landing_id) REFERENCES content.landings(id) ON DELETE SET NULL not valid;

alter table "content"."landings_more_ai_section" validate constraint "landings_more_ai_section_landing_id_foreign";

alter table "content"."landings_more_ai_section" add constraint "landings_more_ai_section_user_created_foreign" FOREIGN KEY (user_created) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_more_ai_section" validate constraint "landings_more_ai_section_user_created_foreign";

alter table "content"."landings_more_ai_section" add constraint "landings_more_ai_section_user_updated_foreign" FOREIGN KEY (user_updated) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_more_ai_section" validate constraint "landings_more_ai_section_user_updated_foreign";

alter table "content"."landings_more_ai_subsection" add constraint "landings_more_ai_subsection_more_ai_section_id_foreign" FOREIGN KEY (more_ai_section_id) REFERENCES content.landings_more_ai_section(id) ON DELETE SET NULL not valid;

alter table "content"."landings_more_ai_subsection" validate constraint "landings_more_ai_subsection_more_ai_section_id_foreign";

alter table "content"."landings_more_ai_subsection" add constraint "landings_more_ai_subsection_user_created_foreign" FOREIGN KEY (user_created) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_more_ai_subsection" validate constraint "landings_more_ai_subsection_user_created_foreign";

alter table "content"."landings_more_ai_subsection" add constraint "landings_more_ai_subsection_user_updated_foreign" FOREIGN KEY (user_updated) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_more_ai_subsection" validate constraint "landings_more_ai_subsection_user_updated_foreign";

alter table "content"."landings_secondary_section" add constraint "landings_secondary_section_landing_id_foreign" FOREIGN KEY (landing_id) REFERENCES content.landings(id) ON DELETE SET NULL not valid;

alter table "content"."landings_secondary_section" validate constraint "landings_secondary_section_landing_id_foreign";

alter table "content"."landings_secondary_section" add constraint "landings_secondary_section_user_created_foreign" FOREIGN KEY (user_created) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_secondary_section" validate constraint "landings_secondary_section_user_created_foreign";

alter table "content"."landings_secondary_section" add constraint "landings_secondary_section_user_updated_foreign" FOREIGN KEY (user_updated) REFERENCES content.directus_users(id) not valid;

alter table "content"."landings_secondary_section" validate constraint "landings_secondary_section_user_updated_foreign";


