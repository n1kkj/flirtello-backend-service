alter table "content"."landings" add column "meta_description" character varying(255);

alter table "content"."landings" add column "meta_title" character varying(255);

alter table "content"."landings_more_ai_subsection" add column "button_link" character varying(255);
