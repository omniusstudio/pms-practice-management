# Test Strategy Implementation Guide

This document provides a comprehensive guide to the test strategy and CI gates implementation for the HIPAA-compliant Mental Health Practice Management System.

## 📋 Overview

The test strategy implements a robust test pyramid with comprehensive coverage requirements, automated CI gates, and HIPAA compliance validation.

## 🔺 Test Pyramid Structure

### Unit Tests (60-80% of total tests)
- **Location**: `apps/backend/tests/unit/`
- **Purpose**: Test individual functions and classes in isolation
- **Coverage Target**: 85%+
- **Execution**: Fast (<1s per test)

### Integration Tests (15-25% of total tests)
- **Location**: `apps/backend/tests/integration/`
- **Purpose**: Test component interactions and API endpoints
- **Coverage Target**: 70%+
- **Execution**: Medium speed (1-5s per test)

### End-to-End Tests (5-15% of total tests)
- **Location**: `tests/e2e/`
- **Purpose**: Test complete user workflows
- **Framework**: Playwright
- **Execution**: Slow (5-30s per test)

### Smoke Tests
- **Location**: `apps/backend/tests/smoke/`
- **Purpose**: Deployment validation and critical path verification
- **Execution**: Fast deployment checks

### Performance Tests
- **Location**: `tests/performance/`
- **Purpose**: Load testing and performance benchmarks
- **Framework**: Artillery
- **Execution**: On-demand and CI triggers

## 🎯 Coverage Requirements

| Test Category | Coverage Threshold | Enforcement |
|---------------|-------------------|-------------|
| Overall | 80% | CI Gate |
| Unit Tests | 85% | CI Gate |
| Critical Paths | 90% | Pre-commit Hook |
| HIPAA Compliance | 100% | Blocking Gate |
| Security Functions | 100% | Blocking Gate |

## 🏷️ Test Markers

The following pytest markers are available:

```python
@pytest.mark.unit          # Unit tests
@pytest.mark.integration   # Integration tests
@pytest.mark.e2e          # End-to-end tests
@pytest.mark.smoke        # Smoke tests
@pytest.mark.slow         # Tests taking >5s
@pytest.mark.security     # Security-related tests
@pytest.mark.hipaa        # HIPAA compliance tests
@pytest.mark.performance  # Performance tests
@pytest.mark.critical     # Critical path tests (90% coverage required)
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Backend test dependencies
cd apps/backend
pip install -r requirements.txt

# Frontend test dependencies
cd apps/frontend
npm install

# E2E test dependencies
cd tests/e2e
npm install

# Performance test dependencies
npm install -g artillery
```

### 2. Install Git Hooks

```bash
# Install pre-commit hooks for test enforcement
./scripts/install-git-hooks.sh
```

### 3. Run Tests

```bash
# Run all tests
make test

# Run specific test categories
make test-backend
make test-frontend
make test-e2e
make test-smoke
make test-performance

# Run with coverage
make coverage-backend
make coverage-frontend

# Validate test pyramid
make validate-test-pyramid
```

## 🔧 Available Commands

### Test Execution

```bash
# Basic test commands
make test-backend          # Run backend unit and integration tests
make test-frontend         # Run frontend tests
make test-e2e             # Run end-to-end tests
make test-smoke           # Run smoke tests
make test-performance     # Run performance tests

# Coverage commands
make coverage-backend     # Backend tests with 80% coverage threshold
make coverage-frontend    # Frontend tests with coverage
make coverage-critical    # Critical path tests with 90% coverage
make coverage-hipaa       # HIPAA compliance tests with 100% coverage

# Validation commands
make validate-test-pyramid # Validate test pyramid structure and ratios

# CI command
make test-ci              # Full CI test suite with validation
```

### Manual Test Execution

```bash
# Backend tests by marker
cd apps/backend
python -m pytest -m unit                    # Unit tests only
python -m pytest -m integration             # Integration tests only
python -m pytest -m "hipaa and critical"    # HIPAA critical tests
python -m pytest -m "not slow"              # Skip slow tests

# With coverage
python -m pytest --cov=. --cov-report=html  # Generate HTML coverage report
python -m pytest --cov-fail-under=90        # Fail if coverage below 90%

# Frontend tests
cd apps/frontend
npm test                  # Run all frontend tests
npm run test:coverage     # Run with coverage
npm run test:watch        # Watch mode for development

# E2E tests
cd tests/e2e
npx playwright test                    # Run all E2E tests
npx playwright test --headed           # Run with browser UI
npx playwright test --project=chromium # Run on specific browser

# Performance tests
cd tests/performance
artillery run artillery.yml            # Run performance tests
artillery run artillery.yml --output report.json  # Save results
```

## 🔒 HIPAA Compliance Testing

### Critical HIPAA Test Areas

1. **Authentication & Authorization**
   - Multi-factor authentication
   - Session management
   - Role-based access control

2. **Data Encryption**
   - Data at rest encryption
   - Data in transit encryption
   - Key rotation and management

3. **Audit Logging**
   - PHI access logging
   - Administrative actions
   - Security events

4. **PHI Protection**
   - Data anonymization
   - Access controls
   - Data retention policies

### Running HIPAA Tests

```bash
# Run all HIPAA compliance tests
cd apps/backend
python -m pytest -m hipaa --cov=. --cov-fail-under=100

# Run specific HIPAA test categories
python -m pytest -m "hipaa and auth"        # Authentication tests
python -m pytest -m "hipaa and encryption"  # Encryption tests
python -m pytest -m "hipaa and audit"       # Audit logging tests
```

## 🚪 CI Gates

### Quality Gate
- **Trigger**: All pull requests
- **Checks**:
  - Code linting (flake8, ESLint)
  - Type checking (mypy, TypeScript)
  - Security scanning (bandit, npm audit)
  - Test pyramid validation

### Test Gate
- **Trigger**: All pull requests
- **Checks**:
  - Unit tests pass
  - Integration tests pass
  - Coverage thresholds met
  - HIPAA compliance tests pass

### Performance Gate
- **Trigger**: PRs labeled 'performance-test'
- **Checks**:
  - Load testing passes
  - Response time benchmarks met
  - Resource usage within limits

### Security Gate
- **Trigger**: All pull requests
- **Checks**:
  - Security vulnerability scans
  - Dependency vulnerability checks
  - HIPAA compliance validation

## 🔄 Pre-commit Hooks

The pre-commit hook enforces:

1. **Test Structure Validation**
   - Required test directories exist
   - Test files follow naming conventions
   - Proper test markers are used

2. **Coverage Enforcement**
   - Overall coverage ≥ 80%
   - Critical path coverage ≥ 90%
   - HIPAA compliance coverage = 100%

3. **Security Checks**
   - No secrets in code
   - No PHI in logs or error messages
   - Security test coverage

4. **Code Quality**
   - Linting passes
   - Type checking passes
   - Test files exist for critical changes

### Bypassing Hooks (Not Recommended)

```bash
# Skip pre-commit hooks (emergency only)
git commit --no-verify

# Uninstall hooks
rm .git/hooks/pre-commit
```

## 📊 Test Reporting

### Coverage Reports

```bash
# Generate HTML coverage report
cd apps/backend
python -m pytest --cov=. --cov-report=html
open htmlcov/index.html

# Generate JSON coverage report for CI
python -m pytest --cov=. --cov-report=json
```

### Test Results

- **JUnit XML**: Generated for CI integration
- **HTML Reports**: Available for local development
- **JSON Reports**: For automated processing

### Performance Reports

```bash
# Generate performance report
cd tests/performance
artillery run artillery.yml --output performance-report.json

# View performance metrics
artillery report performance-report.json
```

## 🐛 Troubleshooting

### Common Issues

1. **Tests Failing Locally**
   ```bash
   # Clear pytest cache
   cd apps/backend
   rm -rf .pytest_cache __pycache__
   
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

2. **Coverage Below Threshold**
   ```bash
   # Identify uncovered lines
   python -m pytest --cov=. --cov-report=term-missing
   
   # Generate detailed HTML report
   python -m pytest --cov=. --cov-report=html
   ```

3. **E2E Tests Failing**
   ```bash
   # Install browser dependencies
   cd tests/e2e
   npx playwright install
   
   # Run with debug mode
   npx playwright test --debug
   ```

4. **Performance Tests Timing Out**
   ```bash
   # Check if backend is running
   curl http://localhost:8000/healthz
   
   # Reduce load in artillery.yml
   # Increase timeout values
   ```

### Debug Commands

```bash
# Validate test pyramid structure
python scripts/validate_test_pyramid.py

# Check test discovery
cd apps/backend
python -m pytest --collect-only

# Run specific failing test with verbose output
python -m pytest tests/unit/test_specific.py::test_function -v -s

# Check coverage for specific module
python -m pytest tests/unit/test_auth.py --cov=services.auth --cov-report=term
```

## 📈 Metrics and Monitoring

### Key Metrics

- **Test Execution Time**: Track test suite performance
- **Coverage Trends**: Monitor coverage over time
- **Flaky Test Detection**: Identify unstable tests
- **Performance Benchmarks**: Track application performance

### Monitoring

- **CI Dashboard**: GitHub Actions provides test results
- **Coverage Reports**: Generated on each CI run
- **Performance Trends**: Artillery reports track performance
- **Security Scans**: Automated vulnerability detection

## 🔄 Maintenance

### Regular Tasks

1. **Weekly**
   - Review test execution times
   - Check for flaky tests
   - Update performance benchmarks

2. **Monthly**
   - Review coverage trends
   - Update test data
   - Validate HIPAA compliance tests

3. **Quarterly**
   - Review test pyramid ratios
   - Update performance thresholds
   - Security test review

### Updating Tests

```bash
# Add new test markers to pytest.ini
# Update coverage thresholds in .coveragerc
# Modify CI workflows in .github/workflows/
# Update Makefile commands as needed
```

## 📚 Additional Resources

- [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Detailed testing guidelines
- [TEST_STRATEGY.md](./TEST_STRATEGY.md) - Complete test strategy document
- [CI_PIPELINE.md](./CI_PIPELINE.md) - CI/CD pipeline documentation
- [Playwright Documentation](https://playwright.dev/)
- [Artillery Documentation](https://artillery.io/docs/)
- [pytest Documentation](https://docs.pytest.org/)

## 🆘 Support

For issues with the test infrastructure:

1. Check this README for common solutions
2. Review the troubleshooting section
3. Check CI logs for detailed error messages
4. Validate test pyramid structure with the validation script
5. Ensure all dependencies are properly installed

---

**Remember**: The test strategy is designed to ensure HIPAA compliance and maintain high code quality. Always run tests before committing and ensure coverage thresholds are met.