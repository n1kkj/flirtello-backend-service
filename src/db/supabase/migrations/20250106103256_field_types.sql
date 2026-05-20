alter table "content"."landings" alter column "main_subtitle" set default 'Explore the World of Al Sexting: Your Guide to Flirtello.com'::text;

alter table "content"."landings" alter column "main_subtitle" set data type text using "main_subtitle"::text;

alter table "content"."landings" alter column "main_title" set default 'NSWF AI Chat'::text;

alter table "content"."landings" alter column "main_title" set data type text using "main_title"::text;

alter table "content"."landings" alter column "meta_description" set data type text using "meta_description"::text;

alter table "content"."landings" alter column "meta_title" set data type text using "meta_title"::text;

alter table "content"."landings_benefits_section" alter column "button_link" set data type text using "button_link"::text;

alter table "content"."landings_benefits_section" alter column "button_text" set default 'Try it for free!'::text;

alter table "content"."landings_benefits_section" alter column "button_text" set data type text using "button_text"::text;

alter table "content"."landings_benefits_section" alter column "subtitle" set default 'Embracing the world of Al sexting unlocks numerous benefits:'::text;

alter table "content"."landings_benefits_section" alter column "subtitle" set data type text using "subtitle"::text;

alter table "content"."landings_benefits_section" alter column "title" set default 'Benefits of Using the NSFW Al Chat Platform'::text;

alter table "content"."landings_benefits_section" alter column "title" set data type text using "title"::text;

alter table "content"."landings_characters_section" alter column "title" set default 'Characters'::text;

alter table "content"."landings_characters_section" alter column "title" set data type text using "title"::text;

alter table "content"."landings_conclusion_section" alter column "button_link" set data type text using "button_link"::text;

alter table "content"."landings_conclusion_section" alter column "button_text" drop default;

alter table "content"."landings_conclusion_section" alter column "button_text" set data type text using "button_text"::text;

alter table "content"."landings_conclusion_section" alter column "text" set data type text using "text"::text;

alter table "content"."landings_conclusion_section" alter column "title" set data type text using "title"::text;

alter table "content"."landings_faq_section" alter column "subtitle" set default 'Your NSFW Character Al Chat Questions Answered'::text;

alter table "content"."landings_faq_section" alter column "subtitle" set data type text using "subtitle"::text;

alter table "content"."landings_faq_section" alter column "title" set default 'Q&A Block'::text;

alter table "content"."landings_faq_section" alter column "title" set data type text using "title"::text;

alter table "content"."landings_faq_subsection" alter column "answer" set data type text using "answer"::text;

alter table "content"."landings_faq_subsection" alter column "question" set data type text using "question"::text;

alter table "content"."landings_main_subsection" alter column "button_link" set data type text using "button_link"::text;

alter table "content"."landings_main_subsection" alter column "button_text" set default 'Try it for free!'::text;

alter table "content"."landings_main_subsection" alter column "button_text" set data type text using "button_text"::text;

alter table "content"."landings_main_subsection" alter column "text" set data type text using "text"::text;

alter table "content"."landings_main_subsection" alter column "title" set data type text using "title"::text;

alter table "content"."landings_more_ai_section" alter column "title" set default 'More NSFW Al Chat with Flirtello.com'::text;

alter table "content"."landings_more_ai_section" alter column "title" set data type text using "title"::text;

alter table "content"."landings_more_ai_subsection" alter column "button_link" set data type text using "button_link"::text;

alter table "content"."landings_more_ai_subsection" alter column "button_text" set data type text using "button_text"::text;

alter table "content"."landings_secondary_section" alter column "button_link" set data type text using "button_link"::text;

alter table "content"."landings_secondary_section" alter column "button_text" drop default;

alter table "content"."landings_secondary_section" alter column "button_text" set data type text using "button_text"::text;

alter table "content"."landings_secondary_section" alter column "text" set data type text using "text"::text;

alter table "content"."landings_secondary_section" alter column "title" set data type text using "title"::text;


