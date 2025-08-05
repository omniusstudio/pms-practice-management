# FHIR Mapping Developer Guide

This guide provides comprehensive documentation for developers working with FHIR resource mappings in the PMS system.

## Overview

The FHIR mapping system provides a bridge between internal PMS resources and FHIR-compliant external systems. It maintains one-to-one mappings between internal resource IDs and FHIR resource IDs, enabling seamless data exchange and synchronization.

## Architecture

### Core Components

1. **FHIRMapping Model** (`models/fhir_mapping.py`)
   - Stores mapping relationships between internal and FHIR resources
   - Tracks synchronization status and error handling
   - Provides audit logging capabilities

2. **FHIRMappingService** (`services/fhir_mapping_service.py`)
   - ORM service layer for managing FHIR mappings
   - Provides CRUD operations and business logic
   - Handles bulk operations and statistics

3. **Database Schema** (Migration: `20250105_1000_add_fhir_mapping_table.py`)
   - PostgreSQL table with proper indexing for fast lookups
   - Unique constraints to ensure data integrity
   - Enum types for resource types and status values

## Supported FHIR Resource Types

The system supports the following FHIR resource types:

- **Patient** - Patient demographics and information
- **Practitioner** - Healthcare providers and staff
- **Encounter** - Patient visits and episodes of care
- **Observation** - Clinical observations and measurements
- **Appointment** - Scheduled appointments and bookings
- **Organization** - Healthcare organizations and facilities
- **Location** - Physical locations and rooms
- **Medication** - Medication information
- **MedicationRequest** - Medication prescriptions
- **DiagnosticReport** - Diagnostic test results
- **Condition** - Patient conditions and diagnoses
- **Procedure** - Medical procedures performed
- **CarePlan** - Care plans and treatment plans
- **DocumentReference** - Clinical documents
- **Coverage** - Insurance coverage information
- **Claim** - Insurance claims
- **ExplanationOfBenefit** - Insurance benefit explanations

## Database Schema

### FHIRMapping Table Structure

```sql
CREATE TABLE fhir_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    internal_id UUID NOT NULL,
    fhir_resource_type fhirresourcetype NOT NULL,
    fhir_resource_id VARCHAR(255) NOT NULL,
    fhir_server_url VARCHAR(500),
    status fhirmappingstatus NOT NULL DEFAULT 'active',
    version VARCHAR(50),
    last_sync_at TIMESTAMP,
    error_count VARCHAR(10) NOT NULL DEFAULT '0',
    last_error TEXT,
    last_error_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT true,
    notes TEXT,
    
    -- Audit fields
    tenant_id VARCHAR(255) NOT NULL,
    correlation_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    
    -- Constraints
    CONSTRAINT uq_fhir_mapping_internal UNIQUE (internal_id, fhir_resource_type, tenant_id),
    CONSTRAINT uq_fhir_mapping_fhir UNIQUE (fhir_resource_id, fhir_resource_type, fhir_server_url, tenant_id)
);
```

### Indexes for Performance

```sql
-- Fast lookups by internal ID
CREATE INDEX idx_fhir_mappings_internal_lookup 
ON fhir_mappings (internal_id, fhir_resource_type, tenant_id);

-- Fast lookups by FHIR ID
CREATE INDEX idx_fhir_mappings_fhir_lookup 
ON fhir_mappings (fhir_resource_id, fhir_resource_type, tenant_id);

-- Resource type filtering
CREATE INDEX idx_fhir_mappings_resource_type 
ON fhir_mappings (fhir_resource_type, tenant_id);

-- Status and sync monitoring
CREATE INDEX idx_fhir_mappings_status 
ON fhir_mappings (status, is_active, tenant_id);

CREATE INDEX idx_fhir_mappings_sync_status 
ON fhir_mappings (last_sync_at, tenant_id) WHERE is_active = true;

-- Error tracking
CREATE INDEX idx_fhir_mappings_errors 
ON fhir_mappings (error_count, last_error_at, tenant_id) WHERE error_count != '0';
```

## Usage Examples

### Basic CRUD Operations

#### Creating a Mapping

```python
from services.fhir_mapping_service import FHIRMappingService
from models.fhir_mapping import FHIRResourceType

service = FHIRMappingService(db_session)

# Create a patient mapping
mapping = service.create_mapping(
    internal_id=patient.id,
    fhir_resource_type=FHIRResourceType.PATIENT,
    fhir_resource_id="patient-12345",
    tenant_id="clinic-1",
    fhir_server_url="https://fhir.example.com",
    created_by="api-user",
    notes="Initial patient sync"
)
```

#### Retrieving Mappings

```python
# Get mapping by internal ID
mapping = service.get_mapping_by_internal_id(
    internal_id=patient.id,
    fhir_resource_type=FHIRResourceType.PATIENT,
    tenant_id="clinic-1"
)

# Get mapping by FHIR ID
mapping = service.get_mapping_by_fhir_id(
    fhir_resource_id="patient-12345",
    fhir_resource_type=FHIRResourceType.PATIENT,
    tenant_id="clinic-1",
    fhir_server_url="https://fhir.example.com"
)

# Get all mappings for a resource type
mappings = service.get_mappings_by_resource_type(
    fhir_resource_type=FHIRResourceType.PATIENT,
    tenant_id="clinic-1"
)
```

#### Updating Mappings

```python
# Update FHIR resource ID
updated_mapping = service.update_mapping(
    mapping_id=mapping.id,
    fhir_resource_id="patient-67890",
    updated_by="sync-service",
    notes="Updated after FHIR server migration"
)

# Mark as synced
synced_mapping = service.mark_mapping_synced(
    mapping_id=mapping.id,
    version="v2.1",
    updated_by="sync-service"
)

# Record an error
error_mapping = service.record_mapping_error(
    mapping_id=mapping.id,
    error_message="FHIR server timeout",
    updated_by="sync-service"
)
```

### Synchronization Workflows

#### Finding Mappings That Need Sync

```python
# Get mappings that haven't been synced in the last hour
needing_sync = service.get_mappings_needing_sync(
    threshold_minutes=60,
    tenant_id="clinic-1",
    resource_type=FHIRResourceType.PATIENT
)

for mapping in needing_sync:
    try:
        # Perform FHIR sync operation
        sync_result = sync_to_fhir_server(mapping)
        
        # Mark as synced on success
        service.mark_mapping_synced(
            mapping_id=mapping.id,
            version=sync_result.version,
            updated_by="sync-service"
        )
    except Exception as e:
        # Record error on failure
        service.record_mapping_error(
            mapping_id=mapping.id,
            error_message=str(e),
            updated_by="sync-service"
        )
```

#### Bulk Operations

```python
# Bulk create mappings
mappings_data = [
    {
        "internal_id": patient1.id,
        "fhir_resource_type": FHIRResourceType.PATIENT,
        "fhir_resource_id": "patient-001",
    },
    {
        "internal_id": patient2.id,
        "fhir_resource_type": FHIRResourceType.PATIENT,
        "fhir_resource_id": "patient-002",
    },
]

created_mappings, errors = service.bulk_create_mappings(
    mappings_data=mappings_data,
    tenant_id="clinic-1",
    created_by="bulk-import"
)

print(f"Created {len(created_mappings)} mappings")
if errors:
    print(f"Errors: {errors}")
```

### Error Handling and Monitoring

#### Getting Mappings with Errors

```python
# Get all mappings with errors
error_mappings = service.get_mappings_with_errors(
    tenant_id="clinic-1",
    resource_type=FHIRResourceType.PATIENT
)

for mapping in error_mappings:
    print(f"Mapping {mapping.id} has {mapping.error_count} errors")
    print(f"Last error: {mapping.last_error}")
    print(f"Last error at: {mapping.last_error_at}")
```

#### Getting Statistics

```python
# Get mapping statistics
stats = service.get_mapping_stats(tenant_id="clinic-1")

print(f"Total mappings: {stats['total']}")
print(f"Active mappings: {stats['active']}")
print(f"Mappings with errors: {stats['with_errors']}")
print(f"Mappings needing sync: {stats['needing_sync']}")
```

## Integration with FHIR Endpoints

### Patient Endpoint Example

```python
from fastapi import APIRouter, Depends, HTTPException
from services.fhir_mapping_service import FHIRMappingService
from models.fhir_mapping import FHIRResourceType

router = APIRouter()

@router.post("/patients/{patient_id}/fhir")
async def create_patient_fhir_mapping(
    patient_id: str,
    fhir_data: dict,
    db_session = Depends(get_db_session),
    current_user = Depends(get_current_user)
):
    """Create FHIR mapping for a patient."""
    service = FHIRMappingService(db_session)
    
    try:
        # Create FHIR resource on external server
        fhir_response = await create_fhir_patient(fhir_data)
        
        # Create mapping
        mapping = service.create_mapping(
            internal_id=patient_id,
            fhir_resource_type=FHIRResourceType.PATIENT,
            fhir_resource_id=fhir_response.id,
            tenant_id=current_user.tenant_id,
            fhir_server_url=FHIR_SERVER_URL,
            created_by=current_user.id,
            notes="Created via API"
        )
        
        return {
            "mapping_id": mapping.id,
            "fhir_resource_id": mapping.fhir_resource_id,
            "status": "created"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patients/{patient_id}/fhir")
async def get_patient_fhir_mapping(
    patient_id: str,
    db_session = Depends(get_db_session),
    current_user = Depends(get_current_user)
):
    """Get FHIR mapping for a patient."""
    service = FHIRMappingService(db_session)
    
    mapping = service.get_mapping_by_internal_id(
        internal_id=patient_id,
        fhir_resource_type=FHIRResourceType.PATIENT,
        tenant_id=current_user.tenant_id
    )
    
    if not mapping:
        raise HTTPException(status_code=404, detail="FHIR mapping not found")
    
    return mapping.to_dict()

@router.put("/patients/{patient_id}/fhir/sync")
async def sync_patient_fhir(
    patient_id: str,
    db_session = Depends(get_db_session),
    current_user = Depends(get_current_user)
):
    """Synchronize patient data with FHIR server."""
    service = FHIRMappingService(db_session)
    
    mapping = service.get_mapping_by_internal_id(
        internal_id=patient_id,
        fhir_resource_type=FHIRResourceType.PATIENT,
        tenant_id=current_user.tenant_id
    )
    
    if not mapping:
        raise HTTPException(status_code=404, detail="FHIR mapping not found")
    
    try:
        # Perform sync with FHIR server
        sync_result = await sync_patient_with_fhir(mapping)
        
        # Update mapping
        service.mark_mapping_synced(
            mapping_id=mapping.id,
            version=sync_result.version,
            updated_by=current_user.id
        )
        
        return {"status": "synced", "version": sync_result.version}
        
    except Exception as e:
        # Record error
        service.record_mapping_error(
            mapping_id=mapping.id,
            error_message=str(e),
            updated_by=current_user.id
        )
        
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
```

## Best Practices

### 1. Always Use Tenant Isolation

```python
# Always include tenant_id in queries
mapping = service.get_mapping_by_internal_id(
    internal_id=resource_id,
    fhir_resource_type=resource_type,
    tenant_id=current_user.tenant_id  # Always include this
)
```

### 2. Handle Errors Gracefully

```python
try:
    mapping = service.create_mapping(...)
except ValueError as e:
    if "already exists" in str(e):
        # Handle duplicate mapping
        existing_mapping = service.get_mapping_by_internal_id(...)
        return existing_mapping
    else:
        raise
```

### 3. Use Correlation IDs for Tracing

```python
mapping = service.create_mapping(
    ...,
    correlation_id=request.headers.get("X-Correlation-ID"),
    created_by=current_user.id
)
```

### 4. Monitor Sync Status

```python
# Regular sync monitoring
needing_sync = service.get_mappings_needing_sync(
    threshold_minutes=30,  # Sync every 30 minutes
    tenant_id=tenant_id
)

if needing_sync:
    logger.info(f"Found {len(needing_sync)} mappings needing sync")
    # Trigger sync process
```

### 5. Handle Bulk Operations Efficiently

```python
# Use bulk operations for large datasets
if len(mappings_to_create) > 10:
    created_mappings, errors = service.bulk_create_mappings(
        mappings_data=mappings_to_create,
        tenant_id=tenant_id,
        created_by=user_id
    )
else:
    # Use individual creates for small datasets
    for mapping_data in mappings_to_create:
        service.create_mapping(**mapping_data)
```

## Troubleshooting

### Common Issues

1. **Duplicate Mapping Errors**
   - Check for existing mappings before creating new ones
   - Use `get_mapping_by_internal_id()` to verify

2. **Sync Failures**
   - Check error logs in `last_error` field
   - Monitor `error_count` for persistent issues
   - Verify FHIR server connectivity

3. **Performance Issues**
   - Ensure proper indexing is in place
   - Use bulk operations for large datasets
   - Monitor query performance

### Debugging Queries

```python
# Enable SQL logging for debugging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Check mapping statistics
stats = service.get_mapping_stats(tenant_id="your-tenant")
print(f"Stats: {stats}")

# Find problematic mappings
error_mappings = service.get_mappings_with_errors(tenant_id="your-tenant")
for mapping in error_mappings:
    print(f"Error in mapping {mapping.id}: {mapping.last_error}")
```

## Testing

Comprehensive tests are available in `tests/test_fhir_mapping.py`. Run tests with:

```bash
pytest tests/test_fhir_mapping.py -v
```

The test suite covers:
- Model functionality and constraints
- Service layer operations
- All supported resource types
- Error handling scenarios
- Audit logging capabilities
- Bulk operations
- Synchronization workflows

## Migration and Deployment

### Running the Migration

```bash
# Apply the FHIR mapping migration
alembic upgrade head
```

### Rollback (if needed)

```bash
# Rollback the FHIR mapping migration
alembic downgrade -1
```

### Verification

```sql
-- Verify table creation
\d fhir_mappings

-- Check enum types
\dT fhirresourcetype
\dT fhirmappingstatus

-- Verify indexes
\di fhir_mappings*
```

## Monitoring and Observability

### Key Metrics to Track

1. **Mapping Creation Rate**
   - New mappings created per hour/day
   - Success/failure rates

2. **Sync Performance**
   - Mappings synced per hour
   - Average sync time
   - Sync failure rates

3. **Error Rates**
   - Mappings with errors
   - Most common error types
   - Error resolution time

4. **Data Quality**
   - Orphaned mappings (internal resource deleted)
   - Duplicate mappings
   - Inconsistent data

### Sample Monitoring Queries

```sql
-- Mappings created in last 24 hours
SELECT COUNT(*) as new_mappings
FROM fhir_mappings 
WHERE created_at >= NOW() - INTERVAL '24 hours';

-- Mappings with errors
SELECT fhir_resource_type, COUNT(*) as error_count
FROM fhir_mappings 
WHERE error_count != '0' AND is_active = true
GROUP BY fhir_resource_type;

-- Sync performance
SELECT 
    fhir_resource_type,
    COUNT(*) as total_mappings,
    COUNT(last_sync_at) as synced_mappings,
    AVG(EXTRACT(EPOCH FROM (NOW() - last_sync_at))/3600) as avg_hours_since_sync
FROM fhir_mappings 
WHERE is_active = true
GROUP BY fhir_resource_type;
```

This guide provides the foundation for working with FHIR mappings in the PMS system. For additional questions or support, consult the test suite or reach out to the development team.