-- Enable row-level security on the table
ALTER TABLE "public"."users" ENABLE ROW LEVEL SECURITY;

-- Drop the existing policy if it exists
DROP POLICY IF EXISTS "Enable insert to public.users for authenticated users only" ON "public"."users";

-- Create the policy for allowing insert operations
CREATE POLICY "Enable insert to public.users for authenticated users only" 
ON "public"."users" 
FOR INSERT 
TO service_role, supabase_auth_admin, postgres 
WITH CHECK (true);