# Performance Budget & Baseline Testing Suite

This directory contains the performance testing infrastructure for the Mental Health Practice Management System, including performance budgets, baseline testing, and automated validation.

## 🎯 Overview

The performance testing suite provides:

- **Performance Budgets**: Predefined thresholds for key performance metrics
- **Baseline Testing**: Automated comparison against historical performance data
- **CI/CD Integration**: Automated performance validation in the deployment pipeline
- **HIPAA Compliance**: Ensures performance testing adheres to healthcare data privacy requirements
- **Comprehensive Reporting**: Detailed performance reports and dashboards

## 📁 File Structure

```
tests/performance/
├── artillery.yml                    # Artillery load testing configuration
├── helpers.js                      # Artillery helper functions and budget validation
├── baseline-test.js                # Main baseline test runner script
├── performance-budgets.json        # Performance budget definitions
├── package.json                    # Node.js dependencies
├── baseline-results.json           # Current performance baseline (auto-generated)
├── results/                        # Test execution results
├── reports/                        # Generated performance reports
└── README.md                       # This file
```

## 🚀 Quick Start

### Prerequisites

- Node.js 16+ and npm 8+
- Artillery.js (installed globally or via npm)
- Access to the target environment

### Installation

```bash
# Install dependencies
npm install

# Install Artillery globally (optional)
npm run install:global

# Validate configuration
npm run validate:config
```

### Running Tests

```bash
# Run performance test with budget validation
npm test

# Run and save as new baseline
npm run test:baseline

# Run in quiet mode (less verbose output)
npm run test:quiet

# Run without budget validation
npm run test:skip-budgets

# Clean previous results
npm run clean
```

## 📊 Performance Budgets

Performance budgets are defined in `performance-budgets.json` and include:

### API Performance Budgets

| Environment | P50 Latency | P95 Latency | P99 Latency | Error Rate | Throughput |
|-------------|-------------|-------------|-------------|------------|-----------|
| Development| 300ms       | 800ms       | 1500ms      | 2.0%       | 50 RPS    |
| Staging     | 250ms       | 600ms       | 1200ms      | 1.5%       | 100 RPS   |
| Production  | 200ms       | 500ms       | 1000ms      | 1.0%       | 200 RPS   |

### Frontend Performance Budgets

| Environment | Page Load P50 | Page Load P95 | FCP | LCP | CLS | Error Rate |
|-------------|---------------|---------------|-----|-----|-----|------------|
| Development| 1500ms        | 3000ms        | 1200ms | 2500ms | 0.1 | 3.0% |
| Staging     | 1200ms        | 2500ms        | 1000ms | 2000ms | 0.08| 2.0% |
| Production  | 1000ms        | 2000ms        | 800ms  | 1500ms | 0.05| 1.0% |

### Critical Endpoints

Special budget thresholds for business-critical endpoints:

- `/api/auth/login`: P95 < 300ms, Error Rate < 0.5%
- `/api/patients`: P95 < 400ms, Error Rate < 1.0%
- `/api/appointments`: P95 < 500ms, Error Rate < 1.0%
- `/api/health`: P95 < 100ms, Error Rate < 0.1%

## 🎯 Baseline Testing

### How Baselines Work

1. **Initial Baseline**: First test run establishes the baseline
2. **Comparison**: Subsequent runs compare against the baseline
3. **Regression Detection**: Alerts when performance degrades beyond thresholds
4. **Baseline Updates**: Baselines can be updated when performance improves

### Regression Thresholds

- **Latency**: 20% increase triggers regression alert
- **Error Rate**: 50% increase triggers regression alert
- **Throughput**: 15% decrease triggers regression alert

### Updating Baselines

```bash
# Save current results as new baseline
SAVE_BASELINE=true npm test

# Or use the dedicated script
npm run test:baseline
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|----------|
| `NODE_ENV` | Target environment | `development` |
| `SAVE_BASELINE` | Save results as baseline | `false` |
| `CI` | Running in CI environment | `false` |
| `GITHUB_SHA` | Git commit hash | `unknown` |
| `TEST_DURATION` | Test duration in minutes | `5` |

### Artillery Configuration

The `artillery.yml` file defines:

- **Target URL**: Application endpoint to test
- **Load Phases**: Warm-up, normal, peak, and stress phases
- **Scenarios**: Different user workflows and API endpoints
- **Processor**: Custom JavaScript functions in `helpers.js`

### Budget Configuration

Edit `performance-budgets.json` to modify:

- Environment-specific budgets
- Critical endpoint thresholds
- Regression detection sensitivity
- Alerting configuration

## 📈 Monitoring & Dashboards

### Grafana Dashboard

The performance dashboard (`/apps/infra/monitoring/performance-dashboard.json`) provides:

- Real-time performance metrics
- Budget compliance status
- Baseline comparison charts
- Performance trend analysis
- Critical endpoint monitoring

### Prometheus Alerts

Performance alerts (`/apps/infra/monitoring/performance-alerts.yml`) include:

- Budget violation alerts
- Regression detection alerts
- Critical endpoint performance alerts
- HIPAA compliance performance alerts

## 🔄 CI/CD Integration

### GitHub Workflow

The `.github/workflows/performance-budget.yml` workflow:

- Runs on pull requests and main branch pushes
- Validates performance budgets
- Compares against baselines
- Posts results as PR comments
- Updates baselines automatically
- Fails builds on budget violations

### Triggering Performance Tests

```bash
# Manual trigger with custom parameters
gh workflow run performance-budget.yml \
  -f save_baseline=true \
  -f environment=staging \
  -f test_duration=10
```

### PR Integration

Performance tests run automatically on PRs and provide:

- Budget validation results
- Regression analysis
- Performance comparison charts
- Actionable recommendations

## 🏥 HIPAA Compliance

### Data Privacy

- **No Real PHI**: All test data uses synthetic, non-identifiable information
- **Secure Transmission**: Tests use encrypted connections
- **Data Retention**: Performance data retained per compliance policies
- **Access Control**: Test execution requires appropriate permissions

### Compliance Monitoring

Special performance budgets for HIPAA-critical components:

- **Audit Log Latency**: < 200ms P95
- **PHI Scrubbing Latency**: < 100ms P95
- **Encryption Overhead**: < 5% performance impact

## 🛠️ Troubleshooting

### Common Issues

#### Test Failures

```bash
# Check application health
curl -f $APP_URL/api/health

# Validate Artillery configuration
npm run artillery:validate

# Run with verbose logging
DEBUG=* npm test
```

#### Budget Violations

1. **Identify Root Cause**: Check specific metrics that failed
2. **Analyze Trends**: Look at historical performance data
3. **Code Review**: Examine recent changes that might impact performance
4. **Infrastructure**: Check system resources and scaling

#### Baseline Issues

```bash
# Reset baseline (use with caution)
rm baseline-results.json
SAVE_BASELINE=true npm test

# Compare with previous baselines
ls -la results/
```

### Debug Mode

```bash
# Enable debug logging
DEBUG=artillery:* npm test

# Artillery verbose mode
artillery run artillery.yml --verbose
```

## 📚 Best Practices

### Test Design

1. **Realistic Load**: Use production-like traffic patterns
2. **Gradual Ramp-up**: Include warm-up phases
3. **Multiple Scenarios**: Test different user workflows
4. **Data Variety**: Use diverse test data sets

### Budget Management

1. **Conservative Budgets**: Set achievable but challenging targets
2. **Regular Reviews**: Update budgets as system evolves
3. **Environment Alignment**: Ensure budgets match environment capabilities
4. **Stakeholder Buy-in**: Get agreement on performance targets

### Baseline Maintenance

1. **Regular Updates**: Update baselines after significant improvements
2. **Version Control**: Track baseline changes with code changes
3. **Documentation**: Document reasons for baseline updates
4. **Rollback Plan**: Keep previous baselines for comparison

## 🔗 Related Documentation

- [Test Strategy](../../TEST_STRATEGY.md)
- [Test Implementation](../../TEST_IMPLEMENTATION_README.md)
- [Metrics Implementation](../../apps/infra/monitoring/METRICS_IMPLEMENTATION.md)
- [SLO Configuration](../../apps/infra/monitoring/slo-config.yml)
- [API Dashboard](../../apps/infra/monitoring/api-dashboard.json)

## 🤝 Contributing

### Adding New Tests

1. Update `artillery.yml` with new scenarios
2. Add corresponding budget thresholds
3. Update documentation
4. Test locally before submitting PR

### Modifying Budgets

1. Analyze current performance data
2. Propose changes with justification
3. Get stakeholder approval
4. Update configuration files
5. Monitor impact after deployment

### Reporting Issues

When reporting performance issues:

1. Include test results and logs
2. Specify environment and configuration
3. Provide steps to reproduce
4. Attach relevant screenshots or charts

---

**Note**: This performance testing suite is designed specifically for healthcare applications and includes HIPAA compliance considerations. Always ensure test data is synthetic and non-identifiable.