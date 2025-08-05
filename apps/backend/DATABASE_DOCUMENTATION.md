# Database Tables Documentation

This document provides comprehensive documentation for all database tables in the Practice Management System (PMS). Each table serves a specific purpose in managing healthcare practice operations, patient data, and system functionality.

## Table Overview

The database contains 14 tables organized into the following categories:
- **Core Healthcare Data**: appointments, clients, providers, notes
- **Financial Management**: ledger
- **Practice Management**: practice_profiles, locations
- **Security & Authentication**: users, auth_tokens, encryption_keys, key_rotation_policies
- **System Management**: audit_log, fhir_mappings
- **Database Management**: alembic_version

---

## Core Healthcare Data Tables

### 1. `clients` Table
**Purpose**: Stores patient/client demographic and clinical information

**Why we need it**: Central repository for all patient data including demographics, contact information, insurance details, emergency contacts, and clinical information. This is the core entity around which all healthcare services revolve.

**Key Features**:
- Complete demographic information (name, DOB, gender, etc.)
- Contact information and addresses
- Insurance and billing information
- Emergency contact details
- Clinical information and medical history
- Multi-tenant support for practice isolation

**Relationships**:
- One-to-many with appointments, notes, ledger entries
- Links to providers through appointments

---

### 2. `providers` Table
**Purpose**: Stores healthcare provider/practitioner information

**Why we need it**: Manages all healthcare professionals who provide services, including their credentials, contact information, scheduling preferences, and professional details.

**Key Features**:
- Basic provider information (name, credentials, specialties)
- Professional information (license numbers, NPI, DEA)
- Contact and office information
- Scheduling and availability settings
- Multi-tenant support

**Relationships**:
- One-to-many with appointments, notes
- Links to clients through appointments and notes

---

### 3. `appointments` Table
**Purpose**: Manages appointment scheduling and tracking

**Why we need it**: Core scheduling system that connects clients with providers, tracks appointment status, manages scheduling conflicts, and supports billing workflows.

**Key Features**:
- Appointment scheduling (date, time, duration)
- Status tracking (scheduled, confirmed, completed, cancelled, etc.)
- Appointment types (initial, follow-up, consultation, etc.)
- Billing and insurance information
- Cancellation and rescheduling support
- Comprehensive indexing for performance

**Relationships**:
- Many-to-one with clients and providers
- One-to-many with notes
- Links to locations for multi-location practices

---

### 4. `notes` Table
**Purpose**: Stores clinical and administrative notes

**Why we need it**: Essential for clinical documentation, treatment planning, billing support, and legal compliance. Supports various note types and clinical workflows.

**Key Features**:
- Multiple note types (progress notes, assessments, treatment plans, etc.)
- Clinical content (diagnosis codes, treatment goals, interventions)
- Administrative controls (signing, locking, review requirements)
- Billing integration (billable status, CPT codes)
- Audit trail and security features

**Relationships**:
- Many-to-one with clients, providers, and appointments
- Supports clinical workflow and billing processes

---

## Financial Management Tables

### 5. `ledger` Table
**Purpose**: Financial transaction tracking and billing management

**Why we need it**: Complete financial record-keeping for all practice transactions including charges, payments, adjustments, and insurance processing. Essential for billing, accounting, and financial reporting.

**Key Features**:
- Multiple transaction types (charges, payments, adjustments, refunds, etc.)
- Payment method tracking
- Insurance claim management
- Reconciliation and posting controls
- Service date and billing code tracking
- Comprehensive financial reporting support

**Relationships**:
- Many-to-one with clients
- Links to appointments and services for billing

---

## Practice Management Tables

### 6. `practice_profiles` Table
**Purpose**: Practice-level configuration and information

**Why we need it**: Centralizes practice-wide settings, contact information, billing details, and operational parameters. Supports multi-practice deployments and practice-specific customization.

**Key Features**:
- Practice identification (name, NPI, tax ID)
- Contact and address information
- Operational settings (timezone, appointment duration)
- Billing configuration
- Multi-tenant support

**Relationships**:
- One-to-many with locations
- Parent entity for practice-wide settings

---

### 7. `locations` Table
**Purpose**: Physical practice locations and facilities

**Why we need it**: Supports multi-location practices, manages facility information, accessibility features, and location-specific settings for scheduling and operations.

**Key Features**:
- Location identification and contact information
- Complete address and accessibility information
- Operational settings (hours, appointment acceptance)
- Facility features (parking, wheelchair access, etc.)
- Multi-location practice support

**Relationships**:
- Many-to-one with practice_profiles
- Links to appointments for location-based scheduling

---

## Security & Authentication Tables

### 8. `users` Table
**Purpose**: System user authentication and authorization

**Why we need it**: Manages system access for all users (providers, staff, administrators) with OAuth2/OIDC integration, role-based access control, and comprehensive security features.

**Key Features**:
- OAuth2/OIDC authentication support
- Multi-factor authentication (MFA)
- Role-based access control
- Session and security tracking
- Provider linking for clinical users
- Comprehensive audit trail

**Relationships**:
- One-to-many with auth_tokens
- Links to providers for clinical users

---

### 9. `auth_tokens` Table
**Purpose**: Authentication token management

**Why we need it**: Secure token-based authentication supporting multiple token types (access, refresh, API keys), with proper expiration, revocation, and security controls.

**Key Features**:
- Multiple token types (access, refresh, API, etc.)
- Token lifecycle management (expiration, revocation)
- Security tracking (usage, IP addresses)
- Rate limiting and abuse prevention
- Comprehensive audit logging

**Relationships**:
- Many-to-one with users
- Foreign key constraint ensures data integrity

---

### 10. `encryption_keys` Table
**Purpose**: Encryption key management for PHI security

**Why we need it**: HIPAA-compliant encryption key management supporting multiple key types, external key management services, and automated rotation for protecting sensitive healthcare data.

**Key Features**:
- Multiple key types (PHI, PII, financial, clinical, etc.)
- External KMS integration (AWS KMS, Azure Key Vault, etc.)
- Key lifecycle management
- Tenant isolation for multi-practice security
- Compliance and audit support

**Relationships**:
- Links to key_rotation_policies for automated management
- Supports tenant-based key isolation

---

### 11. `key_rotation_policies` Table
**Purpose**: Automated encryption key rotation management

**Why we need it**: Implements automated key rotation policies for compliance requirements, security best practices, and operational efficiency in managing encryption keys.

**Key Features**:
- Multiple rotation triggers (time-based, usage-based, event-based)
- Flexible rotation schedules
- Compliance policy enforcement
- Automated rotation workflows
- Policy status management

**Relationships**:
- Links to encryption_keys for policy enforcement
- Supports automated security operations

---

## System Management Tables

### 12. `audit_log` Table
**Purpose**: Comprehensive system audit trail

**Why we need it**: HIPAA compliance requires comprehensive audit logging of all system access and data modifications. Provides security monitoring, compliance reporting, and forensic capabilities.

**Key Features**:
- Complete request tracking (HTTP methods, endpoints, parameters)
- User identification and session tracking
- Data change logging (before/after values)
- Security event monitoring
- Performance and error tracking
- Compliance reporting support

**Relationships**:
- Links to users for action attribution
- Comprehensive system activity tracking

---

### 13. `fhir_mappings` Table
**Purpose**: FHIR interoperability and data exchange

**Why we need it**: Healthcare interoperability requires FHIR (Fast Healthcare Interoperability Resources) compliance for data exchange with other healthcare systems, EHRs, and health information exchanges.

**Key Features**:
- Maps internal data to FHIR resource types
- Supports multiple FHIR resource types (Patient, Practitioner, Encounter, etc.)
- Version control for FHIR specifications
- Mapping status and error tracking
- Interoperability compliance

**Relationships**:
- Maps to various internal entities (clients, providers, appointments, etc.)
- Enables healthcare data exchange

---

### 14. `alembic_version` Table
**Purpose**: Database migration version tracking

**Why we need it**: Alembic database migration tool requires this table to track the current database schema version, enabling safe and consistent database upgrades and rollbacks.

**Key Features**:
- Single row table storing current migration version
- Enables database schema version control
- Supports safe database upgrades and rollbacks
- Essential for deployment automation

---

## Multi-Tenant Architecture

Most tables include `tenant_id` fields to support multi-tenant architecture, allowing:
- Complete data isolation between practices
- Shared infrastructure with secure separation
- Practice-specific customization
- Scalable SaaS deployment model

## Security and Compliance

The database design incorporates:
- **HIPAA Compliance**: Comprehensive audit logging, encryption key management, and access controls
- **Data Integrity**: Foreign key constraints, cascading deletes, and referential integrity
- **Security**: Multi-factor authentication, token management, and encryption
- **Performance**: Comprehensive indexing strategy for all tables
- **Scalability**: Multi-tenant architecture and optimized queries

## Relationships Summary

The database maintains referential integrity through:
- **Client-centric design**: Most clinical data relates to clients
- **Provider associations**: Links providers to appointments and notes
- **Financial tracking**: Ledger entries tied to clients and services
- **Security hierarchy**: Users → auth_tokens → system access
- **Practice management**: practice_profiles → locations → appointments
- **Audit trail**: Comprehensive logging of all system activities

This design supports a complete healthcare practice management system with robust security, compliance, and operational capabilities.