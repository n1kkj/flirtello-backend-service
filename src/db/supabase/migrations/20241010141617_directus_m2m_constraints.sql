alter table "content"."content_character_filters_content_characters" drop constraint "content_character_filters_content_characte__19a18a9f_foreign";

alter table "content"."content_character_filters_content_characters" drop constraint "content_character_filters_content_character__c7acaf0_foreign";

alter table "content"."content_locations_content_characters" drop constraint "content_locations_content_characters_conte__5c611469_foreign";

alter table "content"."content_locations_content_characters" drop constraint "content_locations_content_characters_conten__3184201_foreign";

alter table "content"."content_traits_content_characters" drop constraint "content_traits_content_characters_content___57fde464_foreign";

alter table "content"."content_traits_content_characters" drop constraint "content_traits_content_characters_content_traits_id_foreign";


alter table "content"."content_character_filters_content_characters" add constraint "content_character_filters_content_characte__19a18a9f_foreign" FOREIGN KEY (content_character_filters_id) REFERENCES content.content_character_filters(id) ON DELETE CASCADE not valid;

alter table "content"."content_character_filters_content_characters" validate constraint "content_character_filters_content_characte__19a18a9f_foreign";

alter table "content"."content_character_filters_content_characters" add constraint "content_character_filters_content_character__c7acaf0_foreign" FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON DELETE CASCADE not valid;

alter table "content"."content_character_filters_content_characters" validate constraint "content_character_filters_content_character__c7acaf0_foreign";

alter table "content"."content_locations_content_characters" add constraint "content_locations_content_characters_conte__5c611469_foreign" FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON DELETE CASCADE not valid;

alter table "content"."content_locations_content_characters" validate constraint "content_locations_content_characters_conte__5c611469_foreign";

alter table "content"."content_locations_content_characters" add constraint "content_locations_content_characters_conten__3184201_foreign" FOREIGN KEY (content_locations_id) REFERENCES content.content_locations(id) ON DELETE CASCADE not valid;

alter table "content"."content_locations_content_characters" validate constraint "content_locations_content_characters_conten__3184201_foreign";

alter table "content"."content_traits_content_characters" add constraint "content_traits_content_characters_content___57fde464_foreign" FOREIGN KEY (content_characters_id) REFERENCES content.content_characters(id) ON DELETE CASCADE not valid;

alter table "content"."content_traits_content_characters" validate constraint "content_traits_content_characters_content___57fde464_foreign";

alter table "content"."content_traits_content_characters" add constraint "content_traits_content_characters_content_traits_id_foreign" FOREIGN KEY (content_traits_id) REFERENCES content.content_traits(id) ON DELETE CASCADE not valid;

alter table "content"."content_traits_content_characters" validate constraint "content_traits_content_characters_content_traits_id_foreign";


