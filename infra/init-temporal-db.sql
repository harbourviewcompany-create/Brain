-- Temporal auto-setup needs dedicated databases on the shared Postgres instance.
-- Runs only on first volume initialization (docker-entrypoint-initdb.d).
CREATE DATABASE temporal;
CREATE DATABASE temporal_visibility;
