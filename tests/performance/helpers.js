/**
 * Artillery.js Helper Functions for Performance Budget and Baseline Testing
 * Mental Health Practice Management System - HIPAA Compliant
 */

const fs = require('fs');
const path = require('path');

// Performance budgets configuration
const PERFORMANCE_BUDGETS = {
  api: {
    p50_ms: 200,
    p95_ms: 500,
    error_rate_percent: 1.0,
    availability_percent: 99.9
  },
  frontend: {
    page_load_p95_ms: 2000,
    error_rate_percent: 2.0
  }
};

// Baseline data storage
const BASELINE_FILE = path.join(__dirname, 'baseline-results.json');
const RESULTS_DIR = path.join(__dirname, 'results');

// Ensure results directory exists
if (!fs.existsSync(RESULTS_DIR)) {
  fs.mkdirSync(RESULTS_DIR, { recursive: true });
}

/**
 * Generate random test data that's HIPAA compliant (no real PHI)
 */
function generateTestData() {
  const firstNames = ['Test', 'Demo', 'Sample', 'Mock', 'Example'];
  const lastNames = ['User', 'Patient', 'Provider', 'Admin', 'Client'];
  const domains = ['example.com', 'test.org', 'demo.net'];
  
  return {
    firstName: firstNames[Math.floor(Math.random() * firstNames.length)],
    lastName: lastNames[Math.floor(Math.random() * lastNames.length)],
    email: `test${Math.floor(Math.random() * 10000)}@${domains[Math.floor(Math.random() * domains.length)]}`,
    phone: `555-${String(Math.floor(Math.random() * 900) + 100)}-${String(Math.floor(Math.random() * 9000) + 1000)}`,
    uuid: generateUUID()
  };
}

/**
 * Generate a simple UUID for testing
 */
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Random email generator for testing
 */
function randomEmail() {
  const testData = generateTestData();
  return testData.email;
}

/**
 * Random first name generator
 */
function randomFirstName() {
  const testData = generateTestData();
  return testData.firstName;
}

/**
 * Random last name generator
 */
function randomLastName() {
  const testData = generateTestData();
  return testData.lastName;
}

/**
 * Random phone number generator
 */
function randomPhoneNumber() {
  const testData = generateTestData();
  return testData.phone;
}

/**
 * Random UUID generator
 */
function randomUUID() {
  return generateUUID();
}

/**
 * Load baseline results from file
 */
function loadBaseline() {
  try {
    if (fs.existsSync(BASELINE_FILE)) {
      const data = fs.readFileSync(BASELINE_FILE, 'utf8');
      return JSON.parse(data);
    }
  } catch (error) {
    console.warn('Could not load baseline data:', error.message);
  }
  return null;
}

/**
 * Save baseline results to file
 */
function saveBaseline(results) {
  try {
    const baselineData = {
      timestamp: new Date().toISOString(),
      git_commit: process.env.GITHUB_SHA || 'unknown',
      environment: process.env.NODE_ENV || 'development',
      results: results,
      budgets: PERFORMANCE_BUDGETS
    };
    
    fs.writeFileSync(BASELINE_FILE, JSON.stringify(baselineData, null, 2));
    console.log('Baseline saved successfully');
  } catch (error) {
    console.error('Failed to save baseline:', error.message);
  }
}

/**
 * Validate performance against budgets
 */
function validateBudgets(stats) {
  const violations = [];
  const results = {
    passed: true,
    violations: [],
    summary: {}
  };

  // API budget validation
  if (stats.latency && stats.latency.p50) {
    const p50Ms = stats.latency.p50;
    results.summary.api_p50_ms = p50Ms;
    
    if (p50Ms > PERFORMANCE_BUDGETS.api.p50_ms) {
      violations.push({
        metric: 'API P50 Latency',
        actual: `${p50Ms}ms`,
        budget: `${PERFORMANCE_BUDGETS.api.p50_ms}ms`,
        severity: 'warning'
      });
    }
  }

  if (stats.latency && stats.latency.p95) {
    const p95Ms = stats.latency.p95;
    results.summary.api_p95_ms = p95Ms;
    
    if (p95Ms > PERFORMANCE_BUDGETS.api.p95_ms) {
      violations.push({
        metric: 'API P95 Latency',
        actual: `${p95Ms}ms`,
        budget: `${PERFORMANCE_BUDGETS.api.p95_ms}ms`,
        severity: 'critical'
      });
    }
  }

  // Error rate validation
  if (stats.codes) {
    const totalRequests = Object.values(stats.codes).reduce((sum, count) => sum + count, 0);
    const errorRequests = Object.entries(stats.codes)
      .filter(([code]) => code.startsWith('4') || code.startsWith('5'))
      .reduce((sum, [, count]) => sum + count, 0);
    
    const errorRate = totalRequests > 0 ? (errorRequests / totalRequests) * 100 : 0;
    results.summary.error_rate_percent = errorRate;
    
    if (errorRate > PERFORMANCE_BUDGETS.api.error_rate_percent) {
      violations.push({
        metric: 'API Error Rate',
        actual: `${errorRate.toFixed(2)}%`,
        budget: `${PERFORMANCE_BUDGETS.api.error_rate_percent}%`,
        severity: 'critical'
      });
    }
  }

  results.violations = violations;
  results.passed = violations.length === 0;
  
  return results;
}

/**
 * Compare current results with baseline
 */
function compareWithBaseline(currentStats) {
  const baseline = loadBaseline();
  if (!baseline) {
    console.log('No baseline found - this will become the new baseline');
    return { hasBaseline: false, regressions: [] };
  }

  const regressions = [];
  const comparison = {
    hasBaseline: true,
    regressions: [],
    improvements: [],
    baseline_date: baseline.timestamp
  };

  // Compare P50 latency
  if (baseline.results.latency && currentStats.latency) {
    const baselineP50 = baseline.results.latency.p50 || 0;
    const currentP50 = currentStats.latency.p50 || 0;
    const regressionThreshold = baselineP50 * 1.2; // 20% regression threshold
    
    if (currentP50 > regressionThreshold) {
      regressions.push({
        metric: 'P50 Latency',
        baseline: `${baselineP50}ms`,
        current: `${currentP50}ms`,
        regression: `${((currentP50 - baselineP50) / baselineP50 * 100).toFixed(1)}%`
      });
    } else if (currentP50 < baselineP50 * 0.9) {
      comparison.improvements.push({
        metric: 'P50 Latency',
        improvement: `${((baselineP50 - currentP50) / baselineP50 * 100).toFixed(1)}%`
      });
    }
  }

  // Compare P95 latency
  if (baseline.results.latency && currentStats.latency) {
    const baselineP95 = baseline.results.latency.p95 || 0;
    const currentP95 = currentStats.latency.p95 || 0;
    const regressionThreshold = baselineP95 * 1.2;
    
    if (currentP95 > regressionThreshold) {
      regressions.push({
        metric: 'P95 Latency',
        baseline: `${baselineP95}ms`,
        current: `${currentP95}ms`,
        regression: `${((currentP95 - baselineP95) / baselineP95 * 100).toFixed(1)}%`
      });
    }
  }

  comparison.regressions = regressions;
  return comparison;
}

/**
 * Artillery hook: before test execution
 */
function beforeTest(context, events, done) {
  console.log('🚀 Starting performance budget validation...');
  console.log('📊 Performance Budgets:');
  console.log(`   API P50: < ${PERFORMANCE_BUDGETS.api.p50_ms}ms`);
  console.log(`   API P95: < ${PERFORMANCE_BUDGETS.api.p95_ms}ms`);
  console.log(`   Error Rate: < ${PERFORMANCE_BUDGETS.api.error_rate_percent}%`);
  
  return done();
}

/**
 * Artillery hook: after test execution
 */
function afterTest(context, events, done) {
  const stats = context.vars.$artillery_report || {};
  
  console.log('\n📈 Performance Test Results:');
  
  // Validate against budgets
  const budgetResults = validateBudgets(stats);
  
  if (budgetResults.passed) {
    console.log('✅ All performance budgets passed!');
  } else {
    console.log('❌ Performance budget violations detected:');
    budgetResults.violations.forEach(violation => {
      const icon = violation.severity === 'critical' ? '🚨' : '⚠️';
      console.log(`   ${icon} ${violation.metric}: ${violation.actual} (budget: ${violation.budget})`);
    });
  }
  
  // Compare with baseline
  const comparison = compareWithBaseline(stats);
  
  if (comparison.hasBaseline) {
    if (comparison.regressions.length > 0) {
      console.log('\n📉 Performance regressions detected:');
      comparison.regressions.forEach(regression => {
        console.log(`   🔻 ${regression.metric}: ${regression.current} vs ${regression.baseline} (${regression.regression} slower)`);
      });
    }
    
    if (comparison.improvements.length > 0) {
      console.log('\n📈 Performance improvements:');
      comparison.improvements.forEach(improvement => {
        console.log(`   🔺 ${improvement.metric}: ${improvement.improvement} faster`);
      });
    }
  }
  
  // Save results
  const timestamp = new Date().toISOString();
  const resultsFile = path.join(RESULTS_DIR, `results-${timestamp.replace(/[:.]/g, '-')}.json`);
  
  const fullResults = {
    timestamp,
    stats,
    budget_validation: budgetResults,
    baseline_comparison: comparison,
    environment: {
      node_env: process.env.NODE_ENV,
      git_commit: process.env.GITHUB_SHA,
      ci: process.env.CI === 'true'
    }
  };
  
  try {
    fs.writeFileSync(resultsFile, JSON.stringify(fullResults, null, 2));
    console.log(`\n💾 Results saved to: ${resultsFile}`);
  } catch (error) {
    console.error('Failed to save results:', error.message);
  }
  
  // Update baseline if this is a baseline run
  if (process.env.SAVE_BASELINE === 'true') {
    saveBaseline(stats);
    console.log('\n📊 New baseline saved');
  }
  
  // Exit with error code if budgets failed (for CI/CD)
  if (!budgetResults.passed && process.env.CI === 'true') {
    console.log('\n❌ Exiting with error code due to budget violations');
    process.exit(1);
  }
  
  return done();
}

// Export functions for Artillery
module.exports = {
  // Template functions for Artillery scenarios
  $randomEmail: randomEmail,
  $randomFirstName: randomFirstName,
  $randomLastName: randomLastName,
  $randomPhoneNumber: randomPhoneNumber,
  $randomUUID: randomUUID,
  
  // Lifecycle hooks
  beforeTest,
  afterTest,
  
  // Utility functions
  validateBudgets,
  compareWithBaseline,
  loadBaseline,
  saveBaseline,
  PERFORMANCE_BUDGETS
};