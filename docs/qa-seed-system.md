# QA Seed Data System

Comprehensive system for generating HIPAA-compliant test data for QA environments with sub-5-minute seeding performance.

## Overview

The QA Seed Data System provides:
- **Fast Performance**: Seeds staging environments in under 5 minutes
- **HIPAA Compliance**: No real PHI data, safe domains and phone prefixes
- **Multi-Environment Support**: Minimal, Standard, Load Test, and Integration profiles
- **Multi-Tenant Data**: Proper tenant isolation for testing
- **Comprehensive Validation**: Data integrity and relationship validation
- **Performance Monitoring**: Real-time metrics and benchmarking

## Quick Start

### Prerequisites

```bash
# Ensure you're in the backend directory
cd apps/backend

# Install dependencies
pip install -r requirements.txt

# Set up database connection
export DATABASE_URL="postgresql://user:pass@localhost:5432/pms_qa"
```

### Basic Usage

```bash
# Generate minimal dataset (< 1 minute)
python scripts/qa_seed_manager.py --environment minimal

# Generate standard dataset (< 5 minutes)
python scripts/qa_seed_manager.py --environment standard

# Generate load test dataset (< 30 minutes)
python scripts/qa_seed_manager.py --environment load_test

# Generate integration test dataset
python scripts/qa_seed_manager.py --environment integration
```

## Environment Profiles

### Minimal Environment
- **Target Time**: < 1 minute
- **Use Case**: Quick smoke tests, CI/CD pipelines
- **Record Counts**:
  - Clients: 25
  - Providers: 10
  - Appointments: 50
  - Notes: 25
  - Ledger Entries: 30
  - Locations: 5

### Standard Environment
- **Target Time**: < 5 minutes
- **Use Case**: Regular QA testing, feature validation
- **Record Counts**:
  - Clients: 200
  - Providers: 25
  - Appointments: 500
  - Notes: 300
  - Ledger Entries: 400
  - Locations: 10

### Load Test Environment
- **Target Time**: < 30 minutes
- **Use Case**: Performance testing, stress testing
- **Record Counts**:
  - Clients: 2,000
  - Providers: 100
  - Appointments: 10,000
  - Notes: 5,000
  - Ledger Entries: 8,000
  - Locations: 25

### Integration Environment
- **Target Time**: < 10 minutes
- **Use Case**: End-to-end testing, integration validation
- **Record Counts**:
  - Clients: 500
  - Providers: 50
  - Appointments: 2,000
  - Notes: 1,000
  - Ledger Entries: 1,500
  - Locations: 15

## Configuration

### Environment Variables

```bash
# Database connection
DATABASE_URL="postgresql://user:pass@localhost:5432/pms_qa"

# QA environment (optional, defaults to 'standard')
QA_ENVIRONMENT="standard"

# Performance settings (optional)
QA_BATCH_SIZE=100
QA_PARALLEL_WORKERS=4
QA_USE_BULK_INSERT=true

# Validation settings (optional)
QA_VALIDATION_ENABLED=true
QA_VALIDATION_SAMPLE_SIZE=100
QA_STRICT_MODE=false
```

### Custom Configuration

```python
# config/qa_seed_config.py
from config.qa_seed_config import QAEnvironment, QADataProfile

# Create custom profile
custom_profile = QADataProfile(
    name="Custom QA Dataset",
    description="Custom configuration for specific testing needs",
    target_seed_time_seconds=180,  # 3 minutes
    record_counts={
        'Client': 100,
        'Provider': 15,
        'Appointment': 300,
        'Note': 150,
        'LedgerEntry': 200,
        'Location': 8
    }
)
```

## HIPAA Compliance

### Safe Data Generation

The system ensures HIPAA compliance through:

#### Safe Email Domains
- `example.com`
- `test.local`
- `qa-testing.org`
- `demo.invalid`

#### Safe Phone Prefixes
- `555` (traditional test prefix)
- `000` (clearly fake)
- `999` (reserved for testing)

#### PHI Field Detection
The system automatically rejects any attempt to create fields with PHI-related names:
- `ssn`, `social_security_number`
- `real_name`, `actual_email`
- `driver_license`, `passport`

### Validation

```python
# Example validation check
from factories.base import BaseFactory

# This will raise ValueError: PHI field detected
try:
    BaseFactory._check_for_phi({'ssn': '123-45-6789'})
except ValueError as e:
    print(f"Blocked PHI: {e}")
```

## Performance Optimization

### Batch Processing

```python
# Optimized for performance
config = get_qa_seed_config('standard')
perf_settings = config.get_performance_settings()

print(f"Batch size: {perf_settings['batch_size']}")
print(f"Parallel workers: {perf_settings['parallel_workers']}")
print(f"Bulk insert: {perf_settings['use_bulk_insert']}")
```

### Performance Targets

| Environment | Target Time | Records/Second | Typical Usage |
|-------------|-------------|----------------|---------------|
| Minimal     | < 1 min     | 50+           | CI/CD, Smoke Tests |
| Standard    | < 5 min     | 100+          | Regular QA |
| Load Test   | < 30 min    | 200+          | Performance Testing |
| Integration | < 10 min    | 150+          | E2E Testing |

## Multi-Tenant Support

### Tenant Configuration

```python
# Get tenant IDs for testing
config = get_qa_seed_config('standard')
tenant_ids = config.get_tenant_ids()

print(f"Testing with {len(tenant_ids)} tenants: {tenant_ids}")
# Output: Testing with 3 tenants: ['tenant-qa-001', 'tenant-qa-002', 'tenant-qa-003']
```

### Data Isolation

Each tenant receives isolated data:
- Separate client pools
- Dedicated provider assignments
- Isolated appointment scheduling
- Independent ledger entries

## Monitoring and Metrics

### Performance Metrics

```python
# Example output from seed generation
{
    'environment': 'standard',
    'profile_name': 'Standard QA Dataset',
    'total_time_seconds': 245.7,
    'target_time_seconds': 300,
    'performance_ratio': 0.819,
    'target_met': True,
    'total_records_created': 1435,
    'records_per_second': 5.84,
    'validation_time_seconds': 12.3,
    'errors': [],
    'success': True
}
```

### Real-time Monitoring

```bash
# Monitor seed generation progress
python scripts/qa_seed_manager.py --environment standard --verbose

# Output:
# 🚀 Starting QA seed generation for 'standard' environment
# 📊 Target: 1435 records in < 300 seconds
# ⏱️  Progress: [████████████████████████████████] 100% (1435/1435)
# ✅ Completed in 245.7s (5.84 records/sec)
# 🎯 Performance target: MET (81.9% of target time)
```

## Testing

### Unit Tests

```bash
# Run QA seed system tests
pytest tests/test_qa_seed_system.py -v

# Run specific test categories
pytest tests/test_qa_seed_system.py::TestHIPAACompliance -v
pytest tests/test_qa_seed_system.py::TestPerformanceTargets -v
```

### Integration Tests

```bash
# Run integration tests (requires database)
pytest tests/integration/test_qa_seed_integration.py -v -m integration

# Run load tests (CI only)
pytest tests/integration/test_qa_seed_integration.py -v -m slow
```

### Performance Benchmarking

```bash
# Benchmark all environments
for env in minimal standard load_test integration; do
    echo "Benchmarking $env environment..."
    time python scripts/qa_seed_manager.py --environment $env
done
```

## Troubleshooting

### Common Issues

#### Slow Performance

```bash
# Check database connection
psql $DATABASE_URL -c "SELECT version();"

# Verify database has proper indexes
psql $DATABASE_URL -c "\di"

# Check system resources
top -p $(pgrep -f qa_seed_manager)
```

#### Memory Issues

```python
# Reduce batch size for memory-constrained environments
export QA_BATCH_SIZE=50
export QA_PARALLEL_WORKERS=2

python scripts/qa_seed_manager.py --environment standard
```

#### HIPAA Validation Errors

```python
# Check for PHI in generated data
from scripts.qa_seed_manager import QASeedManager

manager = QASeedManager('minimal')
result = manager.generate_seed_data()

if result['errors']:
    for error in result['errors']:
        if 'PHI' in error:
            print(f"HIPAA violation: {error}")
```

### Performance Tuning

#### Database Optimization

```sql
-- Optimize for bulk inserts
SET synchronous_commit = OFF;
SET wal_buffers = '16MB';
SET checkpoint_segments = 32;
SET checkpoint_completion_target = 0.9;
```

#### Application Tuning

```python
# Custom performance settings
perf_config = {
    'batch_size': 200,        # Larger batches for better throughput
    'parallel_workers': 8,    # More workers for CPU-bound tasks
    'use_bulk_insert': True,  # Enable bulk insert optimization
    'connection_pool_size': 20 # Larger connection pool
}
```

## API Reference

### QASeedManager

```python
from scripts.qa_seed_manager import QASeedManager

# Initialize manager
manager = QASeedManager(
    environment='standard',  # Environment profile
    session=None,           # Optional database session
    config_override=None    # Optional config override
)

# Generate seed data
result = manager.generate_seed_data()

# Access performance metrics
metrics = manager.performance_metrics
```

### Configuration API

```python
from config.qa_seed_config import get_qa_seed_config, QAEnvironment

# Get configuration
config = get_qa_seed_config('standard')

# Access settings
record_counts = config.get_record_counts()
tenant_ids = config.get_tenant_ids()
hipaa_settings = config.get_hipaa_compliance_settings()
perf_settings = config.get_performance_settings()
validation_settings = config.get_validation_settings()
```

## Best Practices

### Development Workflow

1. **Start with Minimal**: Use minimal environment for rapid development cycles
2. **Test with Standard**: Validate features with standard dataset
3. **Load Test Regularly**: Run load tests before major releases
4. **Monitor Performance**: Track seed generation times and optimize as needed

### CI/CD Integration

```yaml
# .github/workflows/qa-seed.yml
name: QA Seed Data Tests

on: [push, pull_request]

jobs:
  test-seed-system:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd apps/backend
          pip install -r requirements.txt
      
      - name: Test minimal seed generation
        run: |
          cd apps/backend
          python scripts/qa_seed_manager.py --environment minimal
      
      - name: Run seed system tests
        run: |
          cd apps/backend
          pytest tests/test_qa_seed_system.py -v
```

### Security Considerations

1. **Never use real PHI**: Always use safe, fake data
2. **Validate data**: Run HIPAA compliance checks
3. **Secure connections**: Use encrypted database connections
4. **Audit logs**: Monitor seed data generation activities
5. **Access control**: Restrict seed generation to authorized personnel

## Migration Guide

### From Legacy Seed Scripts

```bash
# Old way
python seed_practice_data.py

# New way
python scripts/qa_seed_manager.py --environment standard
```

### Configuration Migration

```python
# Old configuration
CLIENT_COUNT = 200
PROVIDER_COUNT = 25

# New configuration
from config.qa_seed_config import get_qa_seed_config
config = get_qa_seed_config('standard')
record_counts = config.get_record_counts()
```

## Support

For issues, questions, or contributions:

1. **Documentation**: Check this guide and inline code documentation
2. **Tests**: Run the test suite to validate your environment
3. **Issues**: Create GitHub issues for bugs or feature requests
4. **Performance**: Use the monitoring tools to diagnose performance issues

## Changelog

### v1.0.0 (Current)
- Initial release with full QA seed system
- HIPAA-compliant data generation
- Multi-environment support (Minimal, Standard, Load Test, Integration)
- Performance optimization with sub-5-minute seeding
- Comprehensive test coverage
- Multi-tenant data isolation
- Real-time monitoring and metrics