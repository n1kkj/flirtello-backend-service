alter table "content"."content_contexts" add column "context_type" character varying(255);


update "content"."content_contexts" set "context_type" = 'first_interaction' where id = 1;