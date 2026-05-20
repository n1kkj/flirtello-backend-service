alter table "content"."landings" add column "slug" character varying(255);

CREATE UNIQUE INDEX landings_slug_unique ON content.landings USING btree (slug);

alter table "content"."landings" add constraint "landings_slug_unique" UNIQUE using index "landings_slug_unique";


