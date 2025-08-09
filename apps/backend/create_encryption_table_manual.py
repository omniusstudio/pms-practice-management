#!/usr/bin/env python3

from sqlalchemy import text

from database import engine


def create_encryption_table():
    conn = engine.connect()
    try:
        # Create the encryption_keys table with proper ENUMs
        create_table_sql = """
        CREATE TABLE encryption_keys (
            id UUID PRIMARY KEY,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            correlation_id VARCHAR(255),
            tenant_id VARCHAR(255),
            key_name VARCHAR(255) NOT NULL,
            key_type keytype NOT NULL,
            kms_key_id VARCHAR(512) NOT NULL UNIQUE,
            kms_provider keyprovider NOT NULL,
            kms_region VARCHAR(100),
            kms_endpoint VARCHAR(512),
            status keystatus NOT NULL DEFAULT 'PENDING',
            version VARCHAR(50) NOT NULL DEFAULT '1',
            activated_at TIMESTAMP WITH TIME ZONE,
            expires_at TIMESTAMP WITH TIME ZONE,
            rotated_at TIMESTAMP WITH TIME ZONE,
            last_used_at TIMESTAMP WITH TIME ZONE,
            parent_key_id UUID REFERENCES encryption_keys(id)
                ON DELETE SET NULL,
            can_rollback BOOLEAN NOT NULL DEFAULT true,
            rollback_expires_at TIMESTAMP WITH TIME ZONE,
            key_algorithm VARCHAR(100) NOT NULL DEFAULT 'AES-256-GCM',
            key_purpose TEXT,
            compliance_tags TEXT,
            authorized_services TEXT,
            access_policy TEXT,
            created_by_token_id UUID REFERENCES auth_tokens(id)
                ON DELETE SET NULL,
            rotated_by_token_id UUID REFERENCES auth_tokens(id)
                ON DELETE SET NULL
        );
        """

        conn.execute(text(create_table_sql))

        # Create indexes
        indexes = [
            (
                "CREATE INDEX ix_encryption_keys_key_name "
                "ON encryption_keys (key_name);"
            ),
            (
                "CREATE INDEX ix_encryption_keys_key_type "
                "ON encryption_keys (key_type);"
            ),
            (
                "CREATE UNIQUE INDEX ix_encryption_keys_kms_key_id "
                "ON encryption_keys (kms_key_id);"
            ),
            ("CREATE INDEX ix_encryption_keys_status " "ON encryption_keys (status);"),
            (
                "CREATE INDEX ix_encryption_keys_kms_provider "
                "ON encryption_keys (kms_provider);"
            ),
            (
                "CREATE INDEX ix_encryption_keys_expires_at "
                "ON encryption_keys (expires_at);"
            ),
            (
                "CREATE INDEX ix_encryption_keys_last_used_at "
                "ON encryption_keys (last_used_at);"
            ),
            (
                "CREATE INDEX ix_encryption_keys_parent_key_id "
                "ON encryption_keys (parent_key_id);"
            ),
            (
                "CREATE INDEX ix_encryption_keys_created_by_token_id "
                "ON encryption_keys (created_by_token_id);"
            ),
            (
                "CREATE INDEX ix_encryption_keys_rotated_by_token_id "
                "ON encryption_keys (rotated_by_token_id);"
            ),
        ]

        for index_sql in indexes:
            conn.execute(text(index_sql))

        conn.commit()
        print("Successfully created encryption_keys table and indexes")

    except Exception as e:
        conn.rollback()
        print(f"Error creating table: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    create_encryption_table()
