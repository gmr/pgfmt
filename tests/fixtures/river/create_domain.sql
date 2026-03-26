CREATE DOMAIN public.status_type AS text CONSTRAINT valid_values CHECK ((VALUE = ANY (ARRAY['active'::text, 'inactive'::text, 'pending'::text])))
