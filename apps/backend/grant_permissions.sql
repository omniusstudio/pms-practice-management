-- Database Administrator Script
-- CRITICAL: Run this as a PostgreSQL superuser (postgres) to grant proper permissions
-- The omniusstudio user STILL does not have CREATE permissions!

-- Step 1: Connect to the pmsdb database as postgres superuser:
-- psql -h localhost -p 5432 -U postgres -d pmsdb

-- Step 2: Run these commands exactly as shown:

-- First, ensure the user exists (may already exist)
-- CREATE USER omniusstudio WITH PASSWORD '8Z3Rx04LMNw3';

-- Grant schema permissions (CRITICAL - these are missing!)
GRANT CREATE ON SCHEMA public TO omniusstudio;
GRANT USAGE ON SCHEMA public TO omniusstudio;
GRANT ALL ON SCHEMA public TO omniusstudio;

-- Grant table permissions (for existing and future tables)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO omniusstudio;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO omniusstudio;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO omniusstudio;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO omniusstudio;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO omniusstudio;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO omniusstudio;

-- Grant database-level permissions
GRANT CONNECT ON DATABASE pmsdb TO omniusstudio;
GRANT CREATE ON DATABASE pmsdb TO omniusstudio;

-- Alternative: Make user a superuser (if above doesn't work)
-- ALTER USER omniusstudio WITH SUPERUSER;

-- Verify permissions (optional check)
SELECT
    current_user as current_user,
    has_schema_privilege('omniusstudio', 'public', 'CREATE') as can_create_tables,
    has_schema_privilege('omniusstudio', 'public', 'USAGE') as can_use_schema;

-- Expected output should show:
-- current_user: postgres (or your admin user)
-- can_create_tables: t (true)
-- can_use_schema: t (true)
