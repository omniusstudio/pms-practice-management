-- PMS Database Schema - Post Schema Cleanup & Index Audit
-- Version: 2.0
-- Date: January 6, 2025
-- Status: Production Ready

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create ENUMs
CREATE TYPE tokentype AS ENUM (
    'ACCESS',
    'REFRESH', 
    'RESET_PASSWORD',
    'EMAIL_VERIFICATION',
    'API_KEY'
);

CREATE TYPE tokenstatus AS ENUM (
    'active',
    'expired',
    'revoked',
    'used'
);

CREATE TYPE keystatus AS ENUM (
    'active',
    'expired',
    'revoked',
    'rotated'
);

CREATE TYPE keytype AS ENUM (
    'AES-256-GCM',
    'AES-256-CBC',
    'RSA-2048',
    'RSA-4096'
);

CREATE TYPE fhirresourcetype AS ENUM (
    'PATIENT',
    'PRACTITIONER',
    'ENCOUNTER',
    'OBSERVATION',
    'APPOINTMENT',
    'ORGANIZATION',
    'LOCATION',
    'MEDICATION',
    'MEDICATIONREQUEST',
    'DIAGNOSTICREPORT',
    'CONDITION',
    'PROCEDURE',
    'CAREPLAN',
    'DOCUMENTREFERENCE',
    'COVERAGE',
    'CLAIM',
    'EXPLANATIONOFBENEFIT'
);

CREATE TYPE fhirmappingstatus AS ENUM (
    'active',
    'inactive',
    'pending',
    'error',
    'deprecated'
);

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Key Rotation Policies Table (referenced by encryption_keys)
CREATE TABLE key_rotation_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    rotation_interval_days INTEGER NOT NULL,
    max_key_age_days INTEGER,
    auto_rotate BOOLEAN DEFAULT true,
    notification_days_before INTEGER DEFAULT 7,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Auth Tokens Table
CREATE TABLE auth_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    user_id UUID NOT NULL,
    token_type tokentype NOT NULL,
    status tokenstatus NOT NULL DEFAULT 'active',
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE,
    rotation_count INTEGER DEFAULT 0,
    parent_token_id UUID,
    tenant_id UUID,
    correlation_id UUID,
    
    -- Foreign Keys
    CONSTRAINT fk_auth_tokens_parent 
        FOREIGN KEY (parent_token_id) 
        REFERENCES auth_tokens(id) 
        ON DELETE SET NULL,
    
    -- Check Constraints
    CONSTRAINT ck_auth_tokens_rotation_count_valid 
        CHECK (rotation_count >= 0)
);

-- Encryption Keys Table
CREATE TABLE encryption_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_name VARCHAR(255) NOT NULL,
    kms_key_id VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL,
    status keystatus NOT NULL DEFAULT 'active',
    key_type keytype NOT NULL DEFAULT 'AES-256-GCM',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    rotated_at TIMESTAMP WITH TIME ZONE,
    parent_key_id UUID,
    created_by_token_id UUID,
    rotated_by_token_id UUID,
    rotation_policy_id UUID,
    tenant_id UUID,
    correlation_id UUID,
    
    -- Foreign Keys
    CONSTRAINT fk_encryption_keys_parent 
        FOREIGN KEY (parent_key_id) 
        REFERENCES encryption_keys(id) 
        ON DELETE SET NULL,
    CONSTRAINT fk_encryption_keys_created_by 
        FOREIGN KEY (created_by_token_id) 
        REFERENCES auth_tokens(id) 
        ON DELETE SET NULL,
    CONSTRAINT fk_encryption_keys_rotated_by 
        FOREIGN KEY (rotated_by_token_id) 
        REFERENCES auth_tokens(id) 
        ON DELETE SET NULL,
    CONSTRAINT fk_encryption_keys_rotation_policy 
        FOREIGN KEY (rotation_policy_id) 
        REFERENCES key_rotation_policies(id) 
        ON DELETE SET NULL,
    
    -- Check Constraints
    CONSTRAINT ck_encryption_keys_version_valid 
        CHECK (version > 0)
);

-- FHIR Mappings Table
CREATE TABLE fhir_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    internal_id UUID NOT NULL,
    fhir_resource_id VARCHAR(255) NOT NULL,
    fhir_resource_type fhirresourcetype NOT NULL,
    fhir_server_url VARCHAR(500),
    mapping_version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    sync_status fhirmappingstatus DEFAULT 'pending',
    error_count INTEGER DEFAULT 0,
    last_error_message TEXT,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    tenant_id UUID,
    correlation_id UUID,
    
    -- Unique Constraints
    CONSTRAINT uq_fhir_mappings_internal_type_server 
        UNIQUE (internal_id, fhir_resource_type, fhir_server_url),
    CONSTRAINT uq_fhir_mappings_fhir_resource_server 
        UNIQUE (fhir_resource_id, fhir_server_url),
    
    -- Check Constraints
    CONSTRAINT ck_fhir_mappings_error_count_valid 
        CHECK (error_count >= 0)
);

-- Practice Profiles Table
CREATE TABLE practice_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    npi_number VARCHAR(10) UNIQUE,
    tax_id VARCHAR(20),
    email VARCHAR(255),
    phone VARCHAR(20),
    website VARCHAR(255),
    specialty VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    billing_address_line1 VARCHAR(255),
    billing_address_line2 VARCHAR(255),
    billing_city VARCHAR(100),
    billing_state VARCHAR(2),
    billing_zip_code VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    tenant_id UUID,
    correlation_id UUID,
    
    -- Unique Constraints
    CONSTRAINT uq_practice_profiles_npi 
        UNIQUE (npi_number),
    
    -- Check Constraints
    CONSTRAINT ck_practice_profiles_npi_format 
        CHECK (npi_number ~ '^[0-9]{10}$')
);

-- Locations Table
CREATE TABLE locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    practice_profile_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(2) NOT NULL,
    zip_code VARCHAR(10) NOT NULL,
    phone VARCHAR(20),
    fax VARCHAR(20),
    email VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_primary BOOLEAN DEFAULT false,
    timezone VARCHAR(50),
    accessibility_features TEXT[],
    parking_available BOOLEAN DEFAULT false,
    public_transport_access BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    tenant_id UUID,
    correlation_id UUID,
    
    -- Foreign Keys
    CONSTRAINT fk_locations_practice_profile 
        FOREIGN KEY (practice_profile_id) 
        REFERENCES practice_profiles(id) 
        ON DELETE CASCADE,
    
    -- Check Constraints
    CONSTRAINT ck_locations_zip_format 
        CHECK (zip_code ~ '^[0-9]{5}([0-9]{4})?$')
);

-- =============================================================================
-- INDEXES - PERFORMANCE OPTIMIZATION
-- =============================================================================

-- Auth Tokens Indexes
CREATE INDEX idx_auth_tokens_user_status_type 
    ON auth_tokens (user_id, status, token_type);

CREATE INDEX idx_auth_tokens_tenant_status_expires 
    ON auth_tokens (tenant_id, status, expires_at);

CREATE INDEX idx_auth_tokens_active_hash 
    ON auth_tokens (token_hash) 
    WHERE status = 'active';

-- Encryption Keys Indexes
CREATE INDEX idx_encryption_keys_tenant_name_version 
    ON encryption_keys (tenant_id, key_name, version);

CREATE INDEX idx_encryption_keys_expires_status 
    ON encryption_keys (expires_at, status);

CREATE INDEX idx_encryption_keys_active_tenant_type 
    ON encryption_keys (tenant_id, key_type) 
    WHERE status = 'active';

-- FHIR Mappings Indexes
CREATE INDEX idx_fhir_mappings_server_resource_type 
    ON fhir_mappings (fhir_server_url, fhir_resource_type);

CREATE INDEX idx_fhir_mappings_error_status_count 
    ON fhir_mappings (error_count, sync_status);

CREATE INDEX idx_fhir_mappings_active_internal 
    ON fhir_mappings (internal_id) 
    WHERE is_active = true;

-- Practice Profiles Indexes
CREATE INDEX idx_practice_profiles_tenant_active 
    ON practice_profiles (tenant_id, is_active);

CREATE INDEX idx_practice_profiles_active_name 
    ON practice_profiles (name) 
    WHERE is_active = true;

CREATE INDEX idx_practice_profiles_npi_number 
    ON practice_profiles (npi_number);

CREATE INDEX idx_practice_profiles_email 
    ON practice_profiles (email);

-- Locations Indexes
CREATE INDEX idx_locations_practice_active 
    ON locations (practice_profile_id, is_active);

CREATE INDEX idx_locations_geography 
    ON locations (city, state, zip_code);

CREATE INDEX idx_locations_active_name 
    ON locations (name) 
    WHERE is_active = true;

-- =============================================================================
-- TRIGGERS FOR UPDATED_AT TIMESTAMPS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to all tables with updated_at
CREATE TRIGGER update_auth_tokens_updated_at 
    BEFORE UPDATE ON auth_tokens 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_encryption_keys_updated_at 
    BEFORE UPDATE ON encryption_keys 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fhir_mappings_updated_at 
    BEFORE UPDATE ON fhir_mappings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_practice_profiles_updated_at 
    BEFORE UPDATE ON practice_profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_locations_updated_at 
    BEFORE UPDATE ON locations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_key_rotation_policies_updated_at 
    BEFORE UPDATE ON key_rotation_policies 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- COMMENTS FOR DOCUMENTATION
-- =============================================================================

-- Table Comments
COMMENT ON TABLE auth_tokens IS 'Centralized authentication token management with rotation tracking';
COMMENT ON TABLE encryption_keys IS 'HIPAA-compliant PHI security and key management';
COMMENT ON TABLE fhir_mappings IS 'Internal-to-FHIR resource mappings with error tracking';
COMMENT ON TABLE practice_profiles IS 'Practice management and configuration';
COMMENT ON TABLE locations IS 'Practice office locations and facilities';
COMMENT ON TABLE key_rotation_policies IS 'Encryption key rotation policy management';

-- Key Column Comments
COMMENT ON COLUMN auth_tokens.parent_token_id IS 'Self-referential FK for token rotation chains';
COMMENT ON COLUMN auth_tokens.rotation_count IS 'Number of times this token has been rotated';
COMMENT ON COLUMN encryption_keys.parent_key_id IS 'Self-referential FK for key versioning';
COMMENT ON COLUMN encryption_keys.version IS 'Key version number for rotation tracking';
COMMENT ON COLUMN fhir_mappings.error_count IS 'Number of sync errors encountered';
COMMENT ON COLUMN practice_profiles.npi_number IS 'National Provider Identifier (10 digits)';
COMMENT ON COLUMN locations.is_primary IS 'Indicates if this is the primary location for the practice';

-- =============================================================================
-- SAMPLE DATA (Optional - for development/testing)
-- =============================================================================

-- Sample Key Rotation Policy
INSERT INTO key_rotation_policies (name, rotation_interval_days, max_key_age_days, auto_rotate)
VALUES ('Standard HIPAA Policy', 90, 365, true);

-- =============================================================================
-- SCHEMA VALIDATION QUERIES
-- =============================================================================

-- Verify all foreign keys are properly created
SELECT 
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
      AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND tc.table_schema = 'public'
ORDER BY tc.table_name, kcu.column_name;

-- Verify all indexes are created
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public'
  AND tablename IN ('auth_tokens', 'encryption_keys', 'fhir_mappings', 'practice_profiles', 'locations')
ORDER BY tablename, indexname;

-- Verify all check constraints
SELECT 
    tc.table_name,
    tc.constraint_name,
    cc.check_clause
FROM information_schema.table_constraints tc
JOIN information_schema.check_constraints cc 
    ON tc.constraint_name = cc.constraint_name
WHERE tc.constraint_type = 'CHECK'
  AND tc.table_schema = 'public'
ORDER BY tc.table_name, tc.constraint_name;

-- =============================================================================
-- PERFORMANCE MONITORING QUERIES
-- =============================================================================

-- Monitor index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Monitor table statistics
SELECT 
    schemaname,
    relname as tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples
FROM pg_stat_user_tables 
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================

-- Schema Version Information
COMMENT ON SCHEMA public IS 'PMS Database Schema v2.0 - Post Schema Cleanup & Index Audit - January 6, 2025';