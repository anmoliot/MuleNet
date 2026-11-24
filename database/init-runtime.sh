#!/usr/bin/env bash
set -euo pipefail
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set=app_password="$MULENET_DB_PASSWORD" --set=db_name="$POSTGRES_DB" <<'SQL'
CREATE ROLE mulenet_runtime LOGIN PASSWORD :'app_password';
GRANT CONNECT ON DATABASE :"db_name" TO mulenet_runtime;
GRANT USAGE ON SCHEMA public TO mulenet_runtime;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT,INSERT,UPDATE,DELETE ON TABLES TO mulenet_runtime;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE,SELECT ON SEQUENCES TO mulenet_runtime;
SQL
