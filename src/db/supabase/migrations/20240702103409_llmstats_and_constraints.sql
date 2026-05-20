alter table "content"."content_character_filters_content_characters" drop constraint "content_character_filters_content_character__c7acaf0_foreign";

alter table "content"."content_characters_files" drop constraint "content_characters_files_content_characters_id_foreign";

alter table "content"."content_contexts_content_characters" drop constraint "content_contexts_content_characters_conten__4d6f7745_foreign";

alter table "content"."content_images" drop constraint "content_images_character_foreign";

alter table "content"."content_locations_content_characters" drop constraint "content_locations_content_characters_conte__5c611469_foreign";

alter table "content"."content_traits_content_characters" drop constraint "content_traits_content_characters_content___57fde464_foreign";

alter table "content"."llm_stats" add column "chat_history" jsonb;

alter table "content"."llm_stats" add column "prompt" text;

alter table "content"."llm_stats" add column "response" text;

alter table "content"."llm_stats" add column "system_prompt" text;

alter table "content"."content_character_filters_content_characters" add constraint "content_character_filters_content_character__c7acaf0_foreign" FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON UPDATE CASCADE not valid;

alter table "content"."content_character_filters_content_characters" validate constraint "content_character_filters_content_character__c7acaf0_foreign";

alter table "content"."content_characters_files" add constraint "content_characters_files_content_characters_id_foreign" FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON UPDATE CASCADE not valid;

alter table "content"."content_characters_files" validate constraint "content_characters_files_content_characters_id_foreign";

alter table "content"."content_contexts_content_characters" add constraint "content_contexts_content_characters_conten__4d6f7745_foreign" FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON UPDATE CASCADE not valid;

alter table "content"."content_contexts_content_characters" validate constraint "content_contexts_content_characters_conten__4d6f7745_foreign";

alter table "content"."content_images" add constraint "content_images_character_foreign" FOREIGN KEY ("character") REFERENCES content.content_characters(id) ON UPDATE CASCADE not valid;

alter table "content"."content_images" validate constraint "content_images_character_foreign";

alter table "content"."content_locations_content_characters" add constraint "content_locations_content_characters_conte__5c611469_foreign" FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON UPDATE CASCADE not valid;

alter table "content"."content_locations_content_characters" validate constraint "content_locations_content_characters_conte__5c611469_foreign";

alter table "content"."content_traits_content_characters" add constraint "content_traits_content_characters_content___57fde464_foreign" FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON UPDATE CASCADE not valid;

alter table "content"."content_traits_content_characters" validate constraint "content_traits_content_characters_content___57fde464_foreign";


alter table "public"."channels" drop constraint "channels_char_id_fkey";

alter table "public"."messages" drop constraint "messages_char_id_fkey";

alter table "public"."channels" add constraint "channels_char_id_fkey" FOREIGN KEY (char_id) REFERENCES content.content_characters(id) ON UPDATE CASCADE not valid;

alter table "public"."channels" validate constraint "channels_char_id_fkey";

alter table "public"."messages" add constraint "messages_char_id_fkey" FOREIGN KEY (char_id) REFERENCES content.content_characters(id) ON UPDATE CASCADE not valid;

alter table "public"."messages" validate constraint "messages_char_id_fkey";

