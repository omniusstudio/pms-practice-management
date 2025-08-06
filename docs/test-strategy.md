# Test Strategy & CI Gates

## Overview

This document defines the comprehensive test strategy for the HIPAA-compliant Mental Health Practice Management System, implementing a proper test pyramid with appropriate CI gates and coverage thresholds.

## Test Pyramid Implementation

### 1. Unit Tests (70% of tests)
**Purpose**: Test individual components in isolation
**Coverage Target**: 85%
**Location**: `apps/backend/tests/test_*.py`, `apps/frontend/src/**/*.test.ts`

**Categories**:
- Model validation and business logic
- Utility functions and helpers
- Component rendering and behavior
- Service layer methods
- PHI scrubbing and security functions

**Examples**:
```python
# Backend unit tests
def test_phi_scrubbing():
    """Test PHI data is properly scrubbed from logs."""
    
def test_user_model_validation():
    """Test user model field validation."""
```

```typescript
// Frontend unit tests
test('LoginForm validates required fields', () => {
  // Test form validation logic
});
```

### 2. Integration Tests (25% of tests)
**Purpose**: Test component interactions and API endpoints
**Coverage Target**: 75%
**Location**: `apps/backend/tests/integration/`, `apps/frontend/src/integration/`

**Categories**:
- API endpoint testing with database
- Service layer integration
- Authentication flows
- Database operations with real connections
- Event bus and ETL pipeline integration

**Examples**:
```python
# Backend integration tests
def test_create_patient_endpoint():
    """Test patient creation via API with database."""
    
def test_auth_middleware_integration():
    """Test authentication middleware with real tokens."""
```

### 3. End-to-End Tests (5% of tests)
**Purpose**: Test complete user workflows
**Coverage Target**: Critical paths only
**Location**: `tests/e2e/`

**Categories**:
- User login and authentication
- Patient registration workflow
- Appointment scheduling
- Clinical note creation
- Billing and payment processing

## CI Gates Configuration

### Quality Gates

#### 1. Code Quality Gate
- **Linting**: Must pass flake8, ESLint
- **Formatting**: Must pass Black, Prettier
- **Type Checking**: Must pass mypy, TypeScript compiler
- **Security**: Must pass Bandit, npm audit

#### 2. Test Coverage Gate
- **Backend**: Minimum 70% overall, 85% for critical modules
- **Frontend**: Minimum 70% overall, 80% for components
- **Critical Modules**: 90% coverage required
  - Authentication and authorization
  - PHI handling and scrubbing
  - Audit logging
  - Encryption key management

#### 3. Security Gate
- **Dependency Scanning**: No high/critical vulnerabilities
- **SAST**: Static analysis security testing
- **PHI Protection**: All PHI patterns must be scrubbed in tests
- **Secrets Detection**: No hardcoded secrets or keys

#### 4. Performance Gate
- **API Response Time**: < 500ms for 95th percentile
- **Frontend Bundle Size**: < 2MB gzipped
- **Database Query Performance**: No N+1 queries

### Branch Protection Rules

#### Main Branch
- Require pull request reviews (2 reviewers)
- Require status checks to pass:
  - `lint`
  - `test-backend`
  - `test-frontend`
  - `security-scan`
  - `quality-gate`
- Require branches to be up to date
- Require conversation resolution
- Restrict pushes to admins only

#### Develop Branch
- Require pull request reviews (1 reviewer)
- Require status checks to pass:
  - `lint`
  - `test-backend`
  - `test-frontend`
- Allow force pushes for maintainers

## Test Categories and Markers

### Backend Test Markers
```python
# pytest.ini markers
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests (>5s)
    security: Security-related tests
    hipaa: HIPAA compliance tests
    performance: Performance tests
    smoke: Smoke tests for deployment
```

### Frontend Test Categories
```typescript
// vitest.config.ts test patterns
export default defineConfig({
  test: {
    include: [
      'src/**/*.{test,spec}.{js,ts,tsx}',
      'src/integration/**/*.test.{js,ts,tsx}',
      'tests/e2e/**/*.test.{js,ts,tsx}'
    ]
  }
});
```

## Critical Test Scenarios

### HIPAA Compliance Tests
1. **PHI Protection**
   - Verify no PHI in logs, errors, or debug output
   - Test PHI scrubbing in all data flows
   - Validate encryption at rest and in transit

2. **Audit Logging**
   - All CRUD operations generate audit logs
   - Audit logs contain required HIPAA fields
   - Audit logs are immutable and tamper-evident

3. **Access Control**
   - Role-based access control enforcement
   - Unauthorized access returns safe errors
   - Session management and timeout handling

### Security Tests
1. **Authentication**
   - Token validation and expiration
   - Multi-factor authentication flows
   - Password policy enforcement

2. **Authorization**
   - Role-based permissions
   - Resource-level access control
   - Tenant isolation

3. **Data Protection**
   - Encryption key rotation
   - Secure data transmission
   - Input validation and sanitization

## Performance Testing

### Load Testing
- **Tool**: Artillery.js or k6
- **Scenarios**:
  - Normal load: 100 concurrent users
  - Peak load: 500 concurrent users
  - Stress test: 1000 concurrent users

### Performance Benchmarks
- **API Endpoints**: < 200ms average response time
- **Database Queries**: < 100ms for simple queries
- **Frontend Load Time**: < 3s initial load
- **Memory Usage**: < 512MB per backend instance

## Test Data Management

### Test Data Strategy
1. **Synthetic Data Only**: No real PHI in any test environment
2. **Factory Pattern**: Use factories for consistent test data
3. **Database Isolation**: Each test uses isolated transactions
4. **Cleanup**: Automatic cleanup after test completion

### Test Environments
1. **Local Development**: SQLite with minimal data
2. **CI/CD**: PostgreSQL with comprehensive test data
3. **Staging**: Production-like data volume (anonymized)
4. **Performance**: Large dataset for load testing

## Monitoring and Reporting

### Test Metrics
- Test execution time trends
- Coverage percentage over time
- Flaky test identification
- Performance regression detection

### Reporting Tools
- **Coverage**: Codecov integration
- **Test Results**: GitHub Actions test reporting
- **Performance**: Lighthouse CI for frontend
- **Security**: GitHub Security tab integration

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Update CI configuration with new gates
- [ ] Implement missing test categories
- [ ] Set up E2E testing framework
- [ ] Configure coverage thresholds

### Phase 2: Enhancement (Week 2)
- [ ] Add performance testing
- [ ] Implement security test automation
- [ ] Set up test data factories
- [ ] Configure monitoring and alerting

### Phase 3: Optimization (Week 3)
- [ ] Optimize test execution time
- [ ] Implement parallel test execution
- [ ] Add visual regression testing
- [ ] Set up test result analytics

## Rollback Plan

If new CI gates cause issues:
1. Temporarily lower coverage thresholds
2. Mark failing tests as expected failures
3. Disable specific gates while maintaining core quality
4. Communicate timeline for fixes to team

## Success Metrics

- **Coverage**: Maintain >70% overall, >85% critical modules
- **CI Speed**: Complete pipeline in <15 minutes
- **Reliability**: <5% flaky test rate
- **Security**: Zero high/critical vulnerabilities in production
- **Performance**: Meet all defined SLA thresholds