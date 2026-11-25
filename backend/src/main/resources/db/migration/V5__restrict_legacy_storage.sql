DO $$
DECLARE legacy RECORD;
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='mulenet_runtime') THEN
        FOR legacy IN SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename NOT LIKE 'platform_%'
        LOOP
            EXECUTE format('REVOKE ALL PRIVILEGES ON TABLE public.%I FROM mulenet_runtime', legacy.tablename);
        END LOOP;
        REVOKE UPDATE,DELETE ON platform_ledger FROM mulenet_runtime;
        REVOKE UPDATE ON platform_vault FROM mulenet_runtime;
    END IF;
END $$;
