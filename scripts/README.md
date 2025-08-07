# Scripts Directory

This directory contains utility scripts for the PMS application, including development workflow tools and comprehensive seed data management scripts providing HIPAA-compliant anonymized data for development and staging environments.

## Development Workflow Scripts

### `init-feature.sh` - Feature Branch Initialization

A CLI script that helps developers create new feature branches following best practices with automatic draft PR creation.

#### Features:
- ✅ Validates branch names and enforces naming conventions
- ✅ Ensures clean working directory before branch creation
- ✅ Updates main branch with latest changes
- ✅ Creates feature branch from main
- ✅ **NEW**: Automatic draft PR creation with GitHub CLI integration
- ✅ **NEW**: Ticket/issue number linking
- ✅ Provides comprehensive workflow guidance
- ✅ Integrates with branch protection rules

#### Usage:
```bash
# Run from project root
./scripts/init-feature.sh
```

#### Interactive Process:
1. **Branch Name**: Enter your feature branch name (e.g., `feature/user-authentication`)
2. **Validation**: Script validates name format and availability
3. **Ticket Linking**: Optional ticket/issue number input for PR linking
4. **Confirmation**: Confirm branch creation
5. **Setup**: Updates main, creates branch
6. **Draft PR Creation**: Optionally creates a draft PR with structured template
7. **Workflow Guidance**: Displays comprehensive development workflow reminders

#### Branch Name Formats:
- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `hotfix/description` - Critical fixes
- Must be 1-50 characters, alphanumeric with hyphens/underscores

#### Draft PR Features:
- **Automatic Creation**: Uses GitHub CLI to create draft PRs
- **Structured Template**: Includes work-in-progress sections and checklists
- **Ticket Linking**: Automatically references provided ticket numbers
- **Fallback Support**: Provides manual PR creation URLs if GitHub CLI unavailable

#### Pre-flight Checks:
- ✅ Git repository validation
- ✅ Main/master branch existence
- ✅ No uncommitted changes
- ✅ Branch name uniqueness
- ✅ GitHub CLI availability (for draft PR creation)

---

### `ready-for-review.sh` - Draft PR Review Preparation

A CLI script that converts draft PRs to ready-for-review status when development is complete, with comprehensive pre-review checks.

#### Features:
- ✅ Automatic draft PR detection and conversion
- ✅ Pre-review checklist and validation
- ✅ Uncommitted changes detection
- ✅ Automated push of latest changes
- ✅ Comprehensive readiness checklist
- ✅ Next steps guidance for reviewers

#### Usage:
```bash
# Run from project root
./scripts/ready-for-review.sh
```

#### Process Flow:
1. **Environment Checks**: Validates git repo and GitHub CLI authentication
2. **PR Detection**: Finds and validates existing draft PR for current branch
3. **Status Verification**: Confirms PR is in draft status
4. **Readiness Checklist**: Displays comprehensive pre-review checklist
5. **Pre-review Checks**: Validates uncommitted changes and pushes updates
6. **Conversion**: Marks PR as ready for review
7. **Next Steps**: Provides guidance for requesting reviews and managing feedback

#### Readiness Checklist:
- ✅ **Code Quality**: Standards compliance, documentation, no debug code
- ✅ **Testing**: All tests pass, new tests added, edge cases covered
- ✅ **Security**: No exposed secrets, input validation, security best practices
- ✅ **Documentation**: README updates, API docs, complete PR description
- ✅ **Integration**: Dev environment testing, no breaking changes, reversible migrations

#### Requirements:
- GitHub CLI (`gh`) installed and authenticated
- Existing draft PR for current branch
- Clean or committed working directory

#### Error Handling:
- Validates GitHub CLI availability and authentication
- Checks for existing PR on current branch
- Prevents operation on main/master branches
- Handles push failures gracefully

---

# Seed Data Scripts

## Quick Start

```bash
# Local development
make seed-data          # Generate seed data
make reset-data         # Reset with fresh data
make validate-data      # Validate data integrity

# Staging environment
make seed-staging       # Generate staging data
make validate-staging   # Validate staging data
make clean-staging      # Clean staging data
```

## Scripts Overview

### Core Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `seed_manager.py` | Central seed data management | CLI for all seed operations |
| `seed_local.py` | Local development data | Optimized for development workflow |
| `seed_staging.py` | Staging environment data | Production-like datasets |

### Legacy Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `db/seed_data.py` | Original seed script | Deprecated - use new scripts |
| `db/seed_practice_data.py` | Practice-specific seeding | Integrated into new system |

## Features

### ✅ HIPAA Compliance
- All data is anonymized and synthetic
- No real PHI (Protected Health Information)
- Compliance validation built-in
- Safe email domains (`.local`)
- Test phone number ranges

### ✅ Multi-Tenant Support
- Proper tenant isolation
- Configurable tenant IDs
- Cross-tenant relationship validation
- Tenant-specific data generation

### ✅ Comprehensive Coverage
- **Core Models**: Practice profiles, locations, clients, providers
- **Clinical Data**: Appointments, notes, clinical records
- **Financial Data**: Ledger entries, billing information
- **Security**: Auth tokens, encryption keys
- **Integration**: FHIR mappings, external system links

### ✅ Data Integrity
- Relationship consistency validation
- Foreign key integrity checks
- Tenant isolation verification
- Automated data quality assurance

## Environment Configurations

### Local Development
- **Records**: ~280 total records across all models
- **Tenants**: 3 development tenants
- **Focus**: Fast generation, realistic relationships
- **Use Case**: Daily development, feature testing

### Staging Environment
- **Records**: ~1,000+ total records across all models
- **Tenants**: 5 staging tenants
- **Focus**: Production-like scale, load testing
- **Use Case**: Integration testing, performance validation

## Usage Examples

### Basic Operations

```bash
# Generate local development data
python scripts/seed_local.py

# Reset local database
python scripts/seed_local.py --reset

# Validate data integrity
python scripts/seed_local.py --validate

# Generate staging data
python scripts/seed_staging.py --reset

# Clean staging environment
python scripts/seed_staging.py --cleanup
```

### Advanced Operations

```bash
# Custom data generation
python scripts/seed_manager.py generate --count 50 --tenants custom_tenant

# Environment-specific reset
python scripts/seed_manager.py reset --environment test

# Data validation only
python scripts/seed_manager.py validate

# Complete data cleanup
python scripts/seed_manager.py clean --confirm
```

### Quiet Mode (CI/CD)

```bash
# Reduced logging for automated environments
python scripts/seed_local.py --quiet
python scripts/seed_staging.py --quiet
```

## Data Models

### Core Business Models

```python
# Practice and Location Data
PracticeProfile     # Medical practice information
Location           # Practice locations and facilities

# People and Relationships
Client             # Patient/client records (anonymized)
Provider           # Healthcare providers and staff

# Clinical Operations
Appointment        # Scheduled appointments
Note              # Clinical notes and documentation
LedgerEntry       # Financial transactions
```

### Security and Integration Models

```python
# Authentication and Security
AuthToken          # Authentication tokens
EncryptionKey      # Encryption key management

# External Integration
FHIRMapping        # FHIR resource mappings
```

## Validation System

The seed data system includes comprehensive validation:

### Validation Checks

1. **Tenant Isolation**
   - Ensures all related records share tenant IDs
   - Prevents cross-tenant data leakage
   - Validates appointment/client/provider relationships

2. **Relationship Integrity**
   - Validates foreign key relationships
   - Ensures referential integrity
   - Checks for orphaned records

3. **HIPAA Compliance**
   - Scans for potentially real data patterns
   - Validates email domain safety
   - Checks for suspicious data patterns

### Validation Output

```bash
=== VALIDATION RESULTS ===
Tenant Isolation: ✓ PASS
Relationships: ✓ PASS
Hipaa Compliance: ✓ PASS

✅ All validations passed!
```

## Factory System

The seed data uses a factory-based approach for data generation:

### Factory Hierarchy

```
BaseFactory (HIPAA compliance)
├── PracticeProfileFactory
├── LocationFactory
├── ClientFactory
├── ProviderFactory
├── AppointmentFactory
├── NoteFactory
├── LedgerEntryFactory
├── AuthTokenFactory
├── EncryptionKeyFactory
└── FHIRMappingFactory
    ├── PatientMappingFactory
    ├── PractitionerMappingFactory
    └── AppointmentMappingFactory
```

### Factory Features

- **HIPAA Compliance**: Built-in safety checks
- **Realistic Data**: Uses faker for authentic-looking data
- **Relationship Handling**: Proper foreign key management
- **Tenant Awareness**: Multi-tenant data generation
- **Customizable**: Easy to extend and modify

## CI/CD Integration

### GitHub Actions

```yaml
# Example workflow step
- name: Setup Test Data
  run: |
    make seed-staging
    make validate-staging
```

### Docker Integration

```dockerfile
# Seed data during container build
RUN python scripts/seed_local.py --quiet
```

### Environment Variables

```bash
# Optional configuration
export SEED_TENANT_PREFIX="ci_test"
export SEED_RECORD_COUNT="50"
export PYTHONPATH="$PYTHONPATH:$(pwd)/apps/backend"
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Solution: Add backend to Python path
   export PYTHONPATH="$PYTHONPATH:$(pwd)/apps/backend"
   ```

2. **Database Connection**
   ```bash
   # Test database connectivity
   python -c "from database import SessionLocal; print('DB Connected')"
   ```

3. **Memory Issues**
   ```bash
   # Use smaller datasets
   python scripts/seed_manager.py generate --count 10
   ```

4. **Validation Failures**
   ```bash
   # Check specific validation issues
   python scripts/seed_local.py --validate
   ```

### Debug Mode

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run with debug output
python scripts/seed_local.py
```

## Performance

### Benchmarks

| Environment | Records | Generation Time | Memory Usage |
|-------------|---------|-----------------|---------------|
| Local | ~280 | ~30 seconds | ~50MB |
| Staging | ~1,000+ | ~2 minutes | ~150MB |

### Optimization Tips

1. **Batch Processing**: Generate data in smaller batches
2. **Database Indexing**: Ensure proper indexes exist
3. **Memory Management**: Monitor memory usage with large datasets
4. **Parallel Processing**: Consider for very large staging datasets

## Security Considerations

### Data Safety

- ✅ No real PHI data generation
- ✅ Anonymized email addresses (`.local` domains)
- ✅ Test phone number ranges
- ✅ Synthetic names and addresses
- ✅ Compliance validation checks

### Access Control

- Scripts require database access
- Staging scripts include cleanup capabilities
- Production databases are explicitly blocked
- Tenant isolation is enforced

## Maintenance

### Regular Tasks

1. **Update Factories**: Keep factories current with model changes
2. **Validation Updates**: Add new validation checks as needed
3. **Performance Monitoring**: Track generation times and memory usage
4. **Documentation**: Keep this README updated with changes

### Version Compatibility

- Python 3.8+
- SQLAlchemy 1.4+
- Factory Boy 3.2+
- Faker 18.0+

## Contributing

### Adding New Factories

1. Create factory in `apps/backend/factories/`
2. Extend `BaseFactory` for HIPAA compliance
3. Add to `factories/__init__.py`
4. Update `seed_manager.py` to include new model
5. Add validation checks if needed
6. Update documentation

### Testing Factories

```python
# Test factory in isolation
from factories import ClientFactory

client = ClientFactory()
print(f"Generated client: {client.first_name} {client.last_name}")
```

## Support

For issues with seed data scripts:

1. Check validation output for specific errors
2. Review factory implementations
3. Examine SeedManager logs
4. Ensure database migrations are current
5. Verify Python path configuration

---

**⚠️ Important**: These scripts are for development and staging only. Never run against production databases.