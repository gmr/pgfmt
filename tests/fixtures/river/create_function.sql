CREATE FUNCTION app.update_modified_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF (TG_OP = 'UPDATE') THEN NEW.modified_at = CURRENT_TIMESTAMP; END IF; RETURN NEW; END; $$
