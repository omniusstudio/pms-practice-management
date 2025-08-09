# QA Seed Configuration

This directory contains configuration files for the QA seed data system.

## Files

- `qa_seed_config.py` - Main configuration for QA environments and data profiles
- `README.md` - This documentation file

## Quick Start

```python
from config.qa_seed_config import get_qa_seed_config

# Get configuration for standard environment
config = get_qa_seed_config('standard')

# Access record counts
record_counts = config.get_record_counts()
print(f"Will create {record_counts['Client']} clients")

# Get tenant IDs for multi-tenant testing
tenant_ids = config.get_tenant_ids()
print(f"Testing with {len(tenant_ids)} tenants")

# Check HIPAA compliance settings
hipaa_settings = config.get_hipaa_compliance_settings()
print(f"Safe domains: {hipaa_settings['safe_domains']}")
```

## Environment Profiles

| Environment | Target Time | Use Case |
|-------------|-------------|----------|
| `minimal` | < 1 min | CI/CD, smoke tests |
| `standard` | < 5 min | Regular QA testing |
| `load_test` | < 30 min | Performance testing |
| `integration` | < 10 min | E2E testing |

## Configuration Options

### Record Counts
Defines how many records to create for each model:

```python
record_counts = {
    'Client': 200,
    'Provider': 25,
    'Appointment': 500,
    'Note': 300,
    'LedgerEntry': 400,
    'Location': 10
}
```

### HIPAA Compliance
Ensures no real PHI is generated:

```python
hipaa_settings = {
    'safe_domains': ['example.com', 'test.local', 'qa-testing.org'],
    'safe_phone_prefixes': ['555', '000', '999']
}
```

### Performance Settings
Optimizes generation speed:

```python
performance_settings = {
    'batch_size': 100,
    'parallel_workers': 4,
    'use_bulk_insert': True
}
```

### Validation Settings
Controls data validation:

```python
validation_settings = {
    'enabled': True,
    'sample_size': 100,
    'strict_mode': False
}
```

## Usage Examples

### Basic Usage

```python
from config.qa_seed_config import get_qa_seed_config

# Get minimal configuration
config = get_qa_seed_config('minimal')
assert config.environment.value == 'minimal'
assert config.current_profile.target_seed_time_seconds <= 60
```

### Custom Environment

```python
from config.qa_seed_config import QAEnvironment, QADataProfile

# Create custom profile
custom_profile = QADataProfile(
    name="Custom Test Profile",
    description="Tailored for specific testing needs",
    target_seed_time_seconds=120,
    record_counts={
        'Client': 50,
        'Provider': 10,
        'Appointment': 100
    }
)
```

### Environment Detection

```python
from config.qa_seed_config import get_current_environment

# Auto-detect environment from ENV vars
current_env = get_current_environment()
config = get_qa_seed_config(current_env)
```

## Environment Variables

```bash
# Set QA environment
export QA_ENVIRONMENT="standard"

# Override performance settings
export QA_BATCH_SIZE=200
export QA_PARALLEL_WORKERS=8
export QA_USE_BULK_INSERT=true

# Override validation settings
export QA_VALIDATION_ENABLED=true
export QA_VALIDATION_SAMPLE_SIZE=50
export QA_STRICT_MODE=false
```

## Testing

```bash
# Test configuration loading
python -c "from config.qa_seed_config import get_qa_seed_config; print(get_qa_seed_config('minimal'))"

# Run configuration tests
pytest tests/test_qa_seed_system.py::TestQAEnvironmentConfig -v
```

## See Also

- [QA Seed System Documentation](../../docs/qa-seed-system.md)
- [QA Seed Manager](../scripts/qa_seed_manager.py)
- [QA Seed Tests](../tests/test_qa_seed_system.py)