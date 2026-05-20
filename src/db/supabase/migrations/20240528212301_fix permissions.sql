grant insert on table public.users to supabase_auth_admin;
CREATE OR REPLACE FUNCTION public.handle_new_user()
    RETURNS trigger
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE NOT LEAKPROOF
AS $BODY$
BEGIN
    -- -- Log the start of the function
    -- INSERT INTO auth.trigger_log(action) VALUES ('Trigger fired with new id: ' || NEW.id);

    -- Perform the insert
    INSERT INTO public.users (id, tg_id)
    VALUES (NEW.id, 123);

    -- -- Log successful insert
    -- INSERT INTO auth.trigger_log(action) VALUES ('Successfully inserted new id: ' || NEW.id);

    RETURN NEW;
EXCEPTION
    WHEN OTHERS THEN
        -- Log the error
		RAISE EXCEPTION 'Error in handle_new_user: % | Role: % | User: %', SQLERRM, current_role, session_user;
END;
$BODY$;
