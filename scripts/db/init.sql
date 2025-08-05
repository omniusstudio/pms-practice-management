-- Mental Health Practice Management System
-- Initial Database Setup Script
-- HIPAA-compliant database initialization

-- Create database if not exists (handled by Docker)
-- This script runs as part of PostgreSQL container initialization

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create application roles with proper permissions
CREATE ROLE pms_app_role;
CREATE ROLE pms_readonly_role;
CREATE ROLE pms_admin_role;

-- Grant basic permissions to application role
GRANT CONNECT ON DATABASE pms_dev TO pms_app_role;
GRANT USAGE ON SCHEMA public TO pms_app_role;
GRANT CREATE ON SCHEMA public TO pms_app_role;

-- Grant read-only permissions
GRANT CONNECT ON DATABASE pms_dev TO pms_readonly_role;
GRANT USAGE ON SCHEMA public TO pms_readonly_role;

-- Grant admin permissions
GRANT CONNECT ON DATABASE pms_dev TO pms_admin_role;
GRANT ALL PRIVILEGES ON SCHEMA public TO pms_admin_role;

-- Assign roles to the main user
GRANT pms_app_role TO pms_user;
GRANT pms_admin_role TO pms_user;

-- Create audit log table for HIPAA compliance
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    correlation_id VARCHAR(255) NOT NULL,
    user_id UUID,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_audit_log_correlation_id (correlation_id),
    INDEX idx_audit_log_user_id (user_id),
    INDEX idx_audit_log_resource (resource_type, resource_id),
    INDEX idx_audit_log_created_at (created_at)
);

-- Grant permissions on audit log
GRANT SELECT, INSERT ON audit_log TO pms_app_role;
GRANT SELECT ON audit_log TO pms_readonly_role;

-- Create function to automatically update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create function for audit logging
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (correlation_id, action, resource_type, resource_id, new_values)
        VALUES (
            COALESCE(current_setting('app.correlation_id', true), 'system'),
            TG_OP,
            TG_TABLE_NAME,
            NEW.id,
            to_jsonb(NEW)
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (correlation_id, action, resource_type, resource_id, old_values, new_values)
        VALUES (
            COALESCE(current_setting('app.correlation_id', true), 'system'),
            TG_OP,
            TG_TABLE_NAME,
            NEW.id,
            to_jsonb(OLD),
            to_jsonb(NEW)
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (correlation_id, action, resource_type, resource_id, old_values)
        VALUES (
            COALESCE(current_setting('app.correlation_id', true), 'system'),
            TG_OP,
            TG_TABLE_NAME,
            OLD.id,
            to_jsonb(OLD)
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Log successful initialization
INSERT INTO audit_log (correlation_id, action, resource_type, resource_id, new_values)
VALUES (
    'init-script',
    'INITIALIZE',
    'database',
    uuid_generate_v4(),
    '{"message": "Database initialized successfully", "version": "1.0.0"}'
);