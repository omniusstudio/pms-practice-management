# Seed Data Management Guide

This guide covers the comprehensive seed data system for the PMS application, providing HIPAA-compliant anonymized data for local development and staging environments.

## Overview

The seed data system provides:
- **HIPAA-compliant anonymized data** for all core models
- **Multi-tenant support** with proper tenant isolation
- **Automated scripts** for local and staging environments
- **Data integrity validation** and relationship consistency
- **Rollback capabilities** and clean data management

## Quick Start

### Local Development

```bash
# Generate seed data for local development
make seed-data

# Reset local database with fresh data
make reset-data

# Validate local data integrity
make validate-data
```

### Staging Environment

```bash
# Generate seed data for staging
make seed-staging

# Validate staging data
make validate-staging

# Clean staging data (CI/CD use)
make clean-staging
```

## Architecture

### Core Components

1. **SeedManager** (`scripts/seed_manager.py`)
   - Centralized seed data management
   - Multi-tenant data generation
   - Data validation and integrity checks
   - CLI interface for all operations

2. **Environment-Specific Scripts**
   - `scripts/seed_local.py` - Local development data
   - `scripts/seed_staging.py` - Staging environment data

3. **HIPAA-Compliant Factories**
   - Located in `apps/backend/factories/`
   - Generate realistic but anonymized data
   - Ensure no real PHI is created

### Data Models Covered

| Model | Factory | Description |
|-------|---------|-------------|
| PracticeProfile | PracticeProfileFactory | Medical practice information |
| Location | LocationFactory | Practice locations and facilities |
| Client | ClientFactory | Patient/client records (anonymized) |
| Provider | ProviderFactory | Healthcare providers and staff |
| Appointment | AppointmentFactory | Scheduled appointments |
| Note | NoteFactory | Clinical notes and documentation |
| LedgerEntry | LedgerEntryFactory | Financial transactions |
| AuthToken | AuthTokenFactory | Authentication tokens |
| EncryptionKey | EncryptionKeyFactory | Encryption key management |
| FHIRMapping | FHIRMappingFactory | FHIR resource mappings |

## Environment Configurations

### Local Development

```python
LOCAL_CONFIG = {
    'counts': {
        'practice_profiles': 3,
        'locations': 6,
        'clients': 25,
        'providers': 8,
        'appointments': 50,
        'notes': 75,
        'ledger_entries': 100,
        'auth_tokens': 15,
        'encryption_keys': 10,
        'fhir_mappings': 80
    },
    'tenant_ids': [
        'dev_tenant_001',
        'dev_tenant_002',
        'dev_tenant_003'
    ]
}
```

### Staging Environment

```python
STAGING_CONFIG = {
    'counts': {
        'practice_profiles': 5,
        'locations': 12,
        'clients': 100,
        'providers': 20,
        'appointments': 200,
        'notes': 300,
        'ledger_entries': 400,
        'auth_tokens': 30,
        'encryption_keys': 20,
        'fhir_mappings': 250
    },
    'tenant_ids': [
        'staging_tenant_001',
        'staging_tenant_002',
        'staging_tenant_003',
        'staging_tenant_004',
        'staging_tenant_005'
    ]
}
```

## Usage Examples

### Direct Script Usage

```bash
# Local development
python scripts/seed_local.py                    # Generate data
python scripts/seed_local.py --reset           # Reset with fresh data
python scripts/seed_local.py --validate        # Validate existing data
python scripts/seed_local.py --quiet           # Reduce logging

# Staging environment
python scripts/seed_staging.py                 # Generate data
python scripts/seed_staging.py --reset         # Reset with fresh data
python scripts/seed_staging.py --validate      # Validate existing data
python scripts/seed_staging.py --cleanup       # Clean all data

# Advanced seed manager
python scripts/seed_manager.py generate --count 50
python scripts/seed_manager.py clean --confirm
python scripts/seed_manager.py reset --environment test
python scripts/seed_manager.py validate
```

### Makefile Commands

```bash
# Local development
make seed-data          # Generate local seed data
make reset-data         # Reset local database
make validate-data      # Validate local data
make clean-data         # Clean all data (WARNING: destructive)

# Staging environment
make seed-staging       # Generate staging seed data
make validate-staging   # Validate staging data
make clean-staging      # Clean staging data
```

## HIPAA Compliance

### Data Safety Measures

1. **No Real PHI**: All data is generated using faker libraries
2. **Anonymized Patterns**: Email addresses use `.local` domains
3. **Safe Phone Numbers**: Use test number ranges
4. **Synthetic Names**: Generated names with no real person correlation
5. **Compliance Validation**: Automated checks for suspicious patterns

### BaseFactory Features

```python
class BaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Base factory with HIPAA compliance checks."""
    
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # HIPAA compliance validation
        sensitive_fields = ['ssn', 'social_security', 'real_email']
        for field in sensitive_fields:
            if field in kwargs:
                raise ValueError(f"Sensitive field {field} not allowed")
        
        return super()._create(model_class, *args, **kwargs)
```

## Data Validation

### Validation Checks

1. **Tenant Isolation**: Ensures all related records share tenant IDs
2. **Relationship Integrity**: Validates foreign key relationships
3. **HIPAA Compliance**: Checks for potentially real data patterns
4. **Data Consistency**: Verifies logical data relationships

### Validation Results

```bash
=== VALIDATION RESULTS ===
Tenant Isolation: ✓ PASS
Relationships: ✓ PASS
Hipaa Compliance: ✓ PASS

✅ All validations passed!
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Staging Deployment

jobs:
  deploy-staging:
    steps:
      - name: Setup Database
        run: |
          # Database migration
          make migrate
          
      - name: Seed Staging Data
        run: |
          make seed-staging
          
      - name: Validate Data
        run: |
          make validate-staging
          
      - name: Run Tests
        run: |
          make test
          
      - name: Cleanup (if needed)
        if: failure()
        run: |
          make clean-staging
```

### Docker Integration

```dockerfile
# In your Dockerfile
COPY scripts/ /app/scripts/
COPY apps/backend/factories/ /app/apps/backend/factories/

# Seed data during container startup
RUN python scripts/seed_local.py --quiet
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure backend directory is in Python path
   export PYTHONPATH="$PYTHONPATH:$(pwd)/apps/backend"
   ```

2. **Database Connection Issues**
   ```bash
   # Check database configuration
   python -c "from database import SessionLocal; print('DB OK')"
   ```

3. **Validation Failures**
   ```bash
   # Run validation with detailed output
   python scripts/seed_local.py --validate
   ```

4. **Memory Issues with Large Datasets**
   ```bash
   # Use smaller batch sizes for staging
   python scripts/seed_manager.py generate --count 10
   ```

### Debugging

```python
# Enable debug logging
import logging
logging.getLogger().setLevel(logging.DEBUG)

# Check generated data
seed_manager = SeedManager()
data = seed_manager.generate_seed_data(counts={'clients': 5})
print(f"Generated {len(data['clients'])} clients")
```

## Best Practices

### Development Workflow

1. **Start Fresh**: Always use `make reset-data` for clean development
2. **Validate Regularly**: Run `make validate-data` after major changes
3. **Test with Staging Data**: Use `make seed-staging` for load testing
4. **Clean Up**: Use `make clean-data` when switching branches

### Factory Development

1. **Extend BaseFactory**: Always inherit from BaseFactory
2. **Use Faker Providers**: Leverage faker for realistic data
3. **Maintain Relationships**: Ensure proper foreign key handling
4. **Test Factories**: Write tests for custom factories

### Performance Optimization

1. **Batch Operations**: Generate data in batches for large datasets
2. **Database Indexing**: Ensure proper indexes for seed data queries
3. **Memory Management**: Monitor memory usage with large datasets
4. **Parallel Generation**: Consider parallel processing for staging data

## Rollback Instructions

### Emergency Rollback

```bash
# Complete database reset
make clean-data
make reset-data

# Validate after rollback
make validate-data
```

### Selective Rollback

```python
# Using SeedManager directly
from scripts.seed_manager import SeedManager

seed_manager = SeedManager()

# Clean specific model types
seed_manager.session.query(Appointment).delete()
seed_manager.session.query(Note).delete()
seed_manager.session.commit()

# Regenerate specific data
seed_manager.generate_seed_data(counts={
    'appointments': 20,
    'notes': 30
})
```

## Support

For issues with seed data:

1. Check the validation output for specific errors
2. Review the factory implementations in `apps/backend/factories/`
3. Examine the SeedManager logs for detailed error information
4. Ensure database migrations are up to date
5. Verify PYTHONPATH includes the backend directory

---

**Note**: This seed data system is designed for development and staging environments only. Never run seed scripts against production databases.