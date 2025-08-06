# Phase 2 Implementation Plan: Type Hints, Logging & PHI Scrubbing

## Overview
This document outlines the comprehensive implementation plan for Phase 2 improvements:
1. **Comprehensive Type Hints** - Add missing type annotations across the codebase
2. **Standardized Logging** - Implement consistent structured logging patterns
3. **Shared PHI Scrubbing Configuration** - Centralize and standardize PHI protection

## 1. Comprehensive Type Hints Implementation

### Current State Analysis
- ✅ Most API endpoints have proper type hints
- ❌ Dependency functions missing return type annotations
- ❌ Utility functions have incomplete type hints
- ❌ Service layer functions need better type annotations
- ❌ Factory classes missing type hints
- ❌ Test functions lack proper type annotations

### Files Requiring Type Hint Improvements

#### High Priority (Core API & Services)
1. **`api/events.py`**
   - `get_event_bus_service()` - missing return type
   - `get_etl_service()` - missing return type

2. **`services/database_service.py`**
   - Multiple methods need better type annotations
   - Generic type parameters for better type safety

3. **`services/etl_pipeline.py`**
   - Service methods missing comprehensive type hints
   - Async function return types need clarification

#### Medium Priority (Utilities & Middleware)
4. **`utils/error_handlers.py`**
   - Exception handling functions need better typing
   - Generic error types for better type safety

5. **`middleware/metrics.py`**
   - Metrics collection functions missing type hints
   - Path scrubbing functions need annotations

6. **`utils/phi_scrubber.py`**
   - Already has good type hints, minor improvements needed

#### Low Priority (Tests & Factories)
7. **`factories/*.py`**
   - Factory methods missing return type annotations
   - LazyFunction and LazyAttribute need better typing

8. **`tests/*.py`**
   - Test functions missing parameter and return types
   - Fixture functions need type annotations

### Type Hint Standards
```python
# Function with comprehensive type hints
from typing import Optional, Dict, List, Union, Any
from uuid import UUID

async def get_user_data(
    user_id: UUID,
    include_sensitive: bool = False,
    fields: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Get user data with optional field filtering."""
    pass

# Dependency function with proper typing
from fastapi import Depends
from services.auth_service import AuthService

async def get_auth_service() -> AuthService:
    """Get authentication service dependency."""
    return AuthService()
```

## 2. Standardized Logging Implementation

### Current State Analysis
- ✅ PHI scrubbing is implemented and working
- ✅ Correlation ID tracking is functional
- ❌ Inconsistent logging patterns across modules
- ❌ Some modules still use basic `logging` instead of structured logging
- ❌ Missing standardized log levels and formats

### Logging Standardization Plan

#### Create Centralized Logging Configuration
```python
# utils/logging_config.py
import structlog
from typing import Any, Dict
from utils.phi_scrubber import scrub_phi

def configure_structured_logging() -> None:
    """Configure structured logging with PHI scrubbing."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            phi_scrubbing_processor,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def phi_scrubbing_processor(logger, method_name, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Processor to scrub PHI from all log entries."""
    return scrub_phi(event_dict)
```

#### Standardized Logger Usage Pattern
```python
# Standard import pattern
import structlog
from middleware.correlation import get_correlation_id

logger = structlog.get_logger(__name__)

# Standard logging patterns
class SomeService:
    def __init__(self):
        self.logger = structlog.get_logger(self.__class__.__name__)
    
    async def process_data(self, data: Dict[str, Any], correlation_id: str) -> None:
        self.logger.info(
            "Processing data started",
            correlation_id=correlation_id,
            data_size=len(data),
            operation="data_processing"
        )
        
        try:
            # Process data
            result = await self._do_processing(data)
            
            self.logger.info(
                "Processing completed successfully",
                correlation_id=correlation_id,
                result_count=len(result),
                operation="data_processing"
            )
        except Exception as e:
            self.logger.error(
                "Processing failed",
                correlation_id=correlation_id,
                error=str(e),
                error_type=type(e).__name__,
                operation="data_processing"
            )
            raise
```

### Files Requiring Logging Standardization

1. **`services/etl_pipeline.py`** - Convert to structured logging
2. **`services/database_service.py`** - Add comprehensive logging
3. **`api/events.py`** - Enhance existing logging
4. **`middleware/metrics.py`** - Add structured logging
5. **`utils/error_handlers.py`** - Standardize error logging

## 3. Shared PHI Scrubbing Configuration

### Current State Analysis
- ✅ PHI scrubbing patterns are defined
- ✅ Basic scrubbing functions work
- ❌ Configuration is hardcoded
- ❌ No environment-specific PHI patterns
- ❌ Missing centralized configuration management

### PHI Scrubbing Improvements

#### Create Centralized PHI Configuration
```python
# config/phi_config.py
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class PHICategory(Enum):
    """Categories of PHI for different scrubbing levels."""
    IDENTIFIERS = "identifiers"  # SSN, MRN, etc.
    CONTACT = "contact"  # Email, phone, address
    DEMOGRAPHIC = "demographic"  # Names, DOB
    FINANCIAL = "financial"  # Insurance, payment info
    MEDICAL = "medical"  # Diagnoses, treatments
    CUSTOM = "custom"  # Organization-specific patterns

@dataclass
class PHIPattern:
    """PHI pattern configuration."""
    name: str
    pattern: str
    replacement: str
    category: PHICategory
    enabled: bool = True
    environment_specific: bool = False

class PHIConfig:
    """Centralized PHI scrubbing configuration."""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self._patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict[str, PHIPattern]:
        """Load PHI patterns based on environment."""
        base_patterns = {
            "ssn_dashed": PHIPattern(
                name="ssn_dashed",
                pattern=r"\b\d{3}-\d{2}-\d{4}\b",
                replacement="[SSN-REDACTED]",
                category=PHICategory.IDENTIFIERS
            ),
            "email": PHIPattern(
                name="email",
                pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                replacement="[EMAIL-REDACTED]",
                category=PHICategory.CONTACT
            ),
            # ... more patterns
        }
        
        # Add environment-specific patterns
        if self.environment == "production":
            base_patterns.update(self._get_production_patterns())
        
        return base_patterns
    
    def get_active_patterns(self, category: Optional[PHICategory] = None) -> List[Tuple[str, str]]:
        """Get active PHI patterns for scrubbing."""
        patterns = []
        for pattern_config in self._patterns.values():
            if not pattern_config.enabled:
                continue
            if category and pattern_config.category != category:
                continue
            patterns.append((pattern_config.pattern, pattern_config.replacement))
        return patterns
```

#### Environment-Specific Configuration
```python
# config/phi_environments.py
from typing import Dict
from .phi_config import PHIPattern, PHICategory

DEVELOPMENT_PATTERNS: Dict[str, PHIPattern] = {
    "test_patient": PHIPattern(
        name="test_patient",
        pattern=r"\bTest Patient\b",
        replacement="[TEST-PATIENT]",
        category=PHICategory.DEMOGRAPHIC,
        environment_specific=True
    )
}

PRODUCTION_PATTERNS: Dict[str, PHIPattern] = {
    "strict_name": PHIPattern(
        name="strict_name",
        pattern=r"\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b",
        replacement="[NAME-REDACTED]",
        category=PHICategory.DEMOGRAPHIC,
        environment_specific=True
    )
}

STAGING_PATTERNS: Dict[str, PHIPattern] = {
    # Staging-specific patterns
}
```

## Implementation Timeline

### Week 1: Type Hints Foundation
- [ ] Add type hints to core API endpoints (`api/events.py`)
- [ ] Improve service layer type annotations (`services/database_service.py`)
- [ ] Add dependency function return types

### Week 2: Logging Standardization
- [ ] Create centralized logging configuration
- [ ] Convert `services/etl_pipeline.py` to structured logging
- [ ] Standardize logging in `services/database_service.py`
- [ ] Update error handling logging patterns

### Week 3: PHI Configuration System
- [ ] Create centralized PHI configuration classes
- [ ] Implement environment-specific PHI patterns
- [ ] Update PHI scrubber to use new configuration
- [ ] Add PHI configuration validation

### Week 4: Integration & Testing
- [ ] Complete remaining type hint additions
- [ ] Test logging standardization across all modules
- [ ] Validate PHI scrubbing with new configuration
- [ ] Update documentation and examples

## Success Criteria

### Type Hints
- [ ] 95%+ of functions have proper type annotations
- [ ] mypy passes with strict configuration
- [ ] IDE provides better autocomplete and error detection

### Logging
- [ ] All modules use structured logging consistently
- [ ] Correlation IDs are present in all log entries
- [ ] PHI scrubbing works automatically across all logs
- [ ] Log format is consistent and parseable

### PHI Scrubbing
- [ ] Centralized configuration system is functional
- [ ] Environment-specific patterns work correctly
- [ ] PHI scrubbing coverage is comprehensive
- [ ] Configuration is easily maintainable

## Risk Mitigation

1. **Type Hint Compatibility**: Test with multiple Python versions
2. **Logging Performance**: Benchmark structured logging impact
3. **PHI False Positives**: Validate scrubbing patterns don't over-scrub
4. **Configuration Complexity**: Keep PHI config simple and well-documented

## Documentation Updates Required

1. Update `docs/LOGGING_GUIDELINES.md` with new patterns
2. Create `docs/TYPE_HINTS_GUIDE.md`
3. Update `docs/PHI_SCRUBBING.md` with new configuration
4. Add examples to `docs/LOGGING_EXAMPLES.md`