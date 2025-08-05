#!/usr/bin/env node
/**
 * Performance Baseline Test Runner
 * Mental Health Practice Management System - HIPAA Compliant
 * 
 * This script runs performance tests to establish baselines and validate budgets
 */

const fs = require('fs');
const path = require('path');
const { execSync, spawn } = require('child_process');
const { performance } = require('perf_hooks');

// Configuration
const CONFIG = {
  artilleryConfig: path.join(__dirname, 'artillery.yml'),
  budgetsConfig: path.join(__dirname, 'performance-budgets.json'),
  baselineFile: path.join(__dirname, 'baseline-results.json'),
  resultsDir: path.join(__dirname, 'results'),
  reportsDir: path.join(__dirname, 'reports')
};

// Ensure directories exist
[CONFIG.resultsDir, CONFIG.reportsDir].forEach(dir => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
});

/**
 * Load performance budgets for current environment
 */
function loadBudgets() {
  try {
    const budgets = JSON.parse(fs.readFileSync(CONFIG.budgetsConfig, 'utf8'));
    const env = process.env.NODE_ENV || 'development';
    return budgets.environments[env] || budgets.environments.development;
  } catch (error) {
    console.error('❌ Failed to load performance budgets:', error.message);
    process.exit(1);
  }
}

/**
 * Check if baseline exists
 */
function hasBaseline() {
  return fs.existsSync(CONFIG.baselineFile);
}

/**
 * Load existing baseline
 */
function loadBaseline() {
  try {
    if (hasBaseline()) {
      return JSON.parse(fs.readFileSync(CONFIG.baselineFile, 'utf8'));
    }
  } catch (error) {
    console.warn('⚠️  Could not load baseline:', error.message);
  }
  return null;
}

/**
 * Run Artillery performance test
 */
function runArtilleryTest(options = {}) {
  return new Promise((resolve, reject) => {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const reportFile = path.join(CONFIG.reportsDir, `report-${timestamp}.json`);
    
    console.log('🚀 Starting Artillery performance test...');
    console.log(`📊 Report will be saved to: ${reportFile}`);
    
    const env = {
      ...process.env,
      ARTILLERY_REPORT_FILE: reportFile
    };
    
    // Add baseline flag if requested
    if (options.saveBaseline) {
      env.SAVE_BASELINE = 'true';
    }
    
    const artilleryArgs = [
      'run',
      CONFIG.artilleryConfig,
      '--output', reportFile
    ];
    
    if (options.quiet) {
      artilleryArgs.push('--quiet');
    }
    
    const artillery = spawn('npx', ['artillery', ...artilleryArgs], {
      stdio: 'inherit',
      env
    });
    
    artillery.on('close', (code) => {
      if (code === 0) {
        console.log('✅ Artillery test completed successfully');
        
        // Load and return results
        try {
          const results = JSON.parse(fs.readFileSync(reportFile, 'utf8'));
          resolve({ results, reportFile });
        } catch (error) {
          reject(new Error(`Failed to parse results: ${error.message}`));
        }
      } else {
        reject(new Error(`Artillery test failed with exit code ${code}`));
      }
    });
    
    artillery.on('error', (error) => {
      reject(new Error(`Failed to start Artillery: ${error.message}`));
    });
  });
}

/**
 * Validate results against performance budgets
 */
function validateBudgets(results) {
  const budgets = loadBudgets();
  const violations = [];
  const warnings = [];
  
  console.log('\n📋 Validating performance budgets...');
  
  // API latency validation
  if (results.aggregate && results.aggregate.latency) {
    const { p50, p95, p99 } = results.aggregate.latency;
    
    // P50 validation
    if (p50 > budgets.api.p50_latency_ms) {
      violations.push({
        metric: 'API P50 Latency',
        actual: `${p50}ms`,
        budget: `${budgets.api.p50_latency_ms}ms`,
        severity: p50 > budgets.api.p50_latency_ms * 1.2 ? 'critical' : 'warning'
      });
    }
    
    // P95 validation
    if (p95 > budgets.api.p95_latency_ms) {
      violations.push({
        metric: 'API P95 Latency',
        actual: `${p95}ms`,
        budget: `${budgets.api.p95_latency_ms}ms`,
        severity: 'critical'
      });
    }
    
    // P99 validation
    if (p99 > budgets.api.p99_latency_ms) {
      violations.push({
        metric: 'API P99 Latency',
        actual: `${p99}ms`,
        budget: `${budgets.api.p99_latency_ms}ms`,
        severity: 'warning'
      });
    }
  }
  
  // Error rate validation
  if (results.aggregate && results.aggregate.codes) {
    const codes = results.aggregate.codes;
    const totalRequests = Object.values(codes).reduce((sum, count) => sum + count, 0);
    const errorRequests = Object.entries(codes)
      .filter(([code]) => parseInt(code) >= 400)
      .reduce((sum, [, count]) => sum + count, 0);
    
    const errorRate = totalRequests > 0 ? (errorRequests / totalRequests) * 100 : 0;
    
    if (errorRate > budgets.api.error_rate_percent) {
      violations.push({
        metric: 'API Error Rate',
        actual: `${errorRate.toFixed(2)}%`,
        budget: `${budgets.api.error_rate_percent}%`,
        severity: 'critical'
      });
    }
  }
  
  return {
    passed: violations.length === 0,
    violations,
    warnings,
    summary: {
      total_checks: violations.length + warnings.length,
      passed_checks: warnings.length,
      failed_checks: violations.length
    }
  };
}

/**
 * Compare results with baseline
 */
function compareWithBaseline(currentResults) {
  const baseline = loadBaseline();
  
  if (!baseline) {
    return {
      hasBaseline: false,
      message: 'No baseline found - current results will become the baseline'
    };
  }
  
  console.log('\n📊 Comparing with baseline...');
  console.log(`📅 Baseline date: ${baseline.timestamp}`);
  
  const regressions = [];
  const improvements = [];
  
  // Compare latency metrics
  if (baseline.results.aggregate && currentResults.aggregate) {
    const baselineLatency = baseline.results.aggregate.latency;
    const currentLatency = currentResults.aggregate.latency;
    
    if (baselineLatency && currentLatency) {
      // P50 comparison
      const p50Change = ((currentLatency.p50 - baselineLatency.p50) / baselineLatency.p50) * 100;
      if (Math.abs(p50Change) > 5) { // 5% threshold
        if (p50Change > 0) {
          regressions.push({
            metric: 'P50 Latency',
            baseline: `${baselineLatency.p50}ms`,
            current: `${currentLatency.p50}ms`,
            change: `+${p50Change.toFixed(1)}%`
          });
        } else {
          improvements.push({
            metric: 'P50 Latency',
            baseline: `${baselineLatency.p50}ms`,
            current: `${currentLatency.p50}ms`,
            change: `${p50Change.toFixed(1)}%`
          });
        }
      }
      
      // P95 comparison
      const p95Change = ((currentLatency.p95 - baselineLatency.p95) / baselineLatency.p95) * 100;
      if (Math.abs(p95Change) > 5) {
        if (p95Change > 0) {
          regressions.push({
            metric: 'P95 Latency',
            baseline: `${baselineLatency.p95}ms`,
            current: `${currentLatency.p95}ms`,
            change: `+${p95Change.toFixed(1)}%`
          });
        } else {
          improvements.push({
            metric: 'P95 Latency',
            baseline: `${baselineLatency.p95}ms`,
            current: `${currentLatency.p95}ms`,
            change: `${p95Change.toFixed(1)}%`
          });
        }
      }
    }
  }
  
  return {
    hasBaseline: true,
    baseline_date: baseline.timestamp,
    regressions,
    improvements,
    summary: {
      total_comparisons: regressions.length + improvements.length,
      regressions: regressions.length,
      improvements: improvements.length
    }
  };
}

/**
 * Generate performance report
 */
function generateReport(testResults, budgetValidation, baselineComparison) {
  const timestamp = new Date().toISOString();
  const reportFile = path.join(CONFIG.reportsDir, `performance-report-${timestamp.replace(/[:.]/g, '-')}.json`);
  
  const report = {
    timestamp,
    environment: {
      node_env: process.env.NODE_ENV || 'development',
      git_commit: process.env.GITHUB_SHA || 'unknown',
      ci: process.env.CI === 'true'
    },
    test_results: testResults.results,
    budget_validation: budgetValidation,
    baseline_comparison: baselineComparison,
    summary: {
      overall_status: budgetValidation.passed && baselineComparison.regressions?.length === 0 ? 'PASS' : 'FAIL',
      budget_status: budgetValidation.passed ? 'PASS' : 'FAIL',
      regression_status: baselineComparison.regressions?.length === 0 ? 'PASS' : 'FAIL'
    }
  };
  
  fs.writeFileSync(reportFile, JSON.stringify(report, null, 2));
  console.log(`\n📄 Performance report saved: ${reportFile}`);
  
  return report;
}

/**
 * Print summary to console
 */
function printSummary(report) {
  console.log('\n' + '='.repeat(60));
  console.log('📊 PERFORMANCE TEST SUMMARY');
  console.log('='.repeat(60));
  
  // Overall status
  const statusIcon = report.summary.overall_status === 'PASS' ? '✅' : '❌';
  console.log(`${statusIcon} Overall Status: ${report.summary.overall_status}`);
  
  // Budget validation
  const budgetIcon = report.budget_validation.passed ? '✅' : '❌';
  console.log(`${budgetIcon} Budget Validation: ${report.summary.budget_status}`);
  
  if (report.budget_validation.violations.length > 0) {
    console.log('   Budget Violations:');
    report.budget_validation.violations.forEach(violation => {
      const icon = violation.severity === 'critical' ? '🚨' : '⚠️';
      console.log(`   ${icon} ${violation.metric}: ${violation.actual} (budget: ${violation.budget})`);
    });
  }
  
  // Baseline comparison
  if (report.baseline_comparison.hasBaseline) {
    const regressionIcon = report.baseline_comparison.regressions.length === 0 ? '✅' : '❌';
    console.log(`${regressionIcon} Regression Check: ${report.summary.regression_status}`);
    
    if (report.baseline_comparison.regressions.length > 0) {
      console.log('   Performance Regressions:');
      report.baseline_comparison.regressions.forEach(regression => {
        console.log(`   📉 ${regression.metric}: ${regression.current} vs ${regression.baseline} (${regression.change})`);
      });
    }
    
    if (report.baseline_comparison.improvements.length > 0) {
      console.log('   Performance Improvements:');
      report.baseline_comparison.improvements.forEach(improvement => {
        console.log(`   📈 ${improvement.metric}: ${improvement.current} vs ${improvement.baseline} (${improvement.change})`);
      });
    }
  } else {
    console.log('ℹ️  No baseline found - this will become the new baseline');
  }
  
  console.log('='.repeat(60));
}

/**
 * Main execution function
 */
async function main() {
  const args = process.argv.slice(2);
  const options = {
    saveBaseline: args.includes('--save-baseline') || args.includes('--baseline'),
    quiet: args.includes('--quiet'),
    skipBudgets: args.includes('--skip-budgets')
  };
  
  console.log('🎯 Performance Baseline Test Runner');
  console.log('====================================');
  
  if (options.saveBaseline) {
    console.log('📊 Running in baseline mode - results will be saved as new baseline');
  }
  
  try {
    // Run performance test
    const testResults = await runArtilleryTest(options);
    
    // Validate against budgets
    let budgetValidation = { passed: true, violations: [], warnings: [] };
    if (!options.skipBudgets) {
      budgetValidation = validateBudgets(testResults.results);
    }
    
    // Compare with baseline
    const baselineComparison = compareWithBaseline(testResults.results);
    
    // Generate report
    const report = generateReport(testResults, budgetValidation, baselineComparison);
    
    // Print summary
    printSummary(report);
    
    // Exit with appropriate code
    const shouldFail = !budgetValidation.passed || (baselineComparison.regressions && baselineComparison.regressions.length > 0);
    if (shouldFail && process.env.CI === 'true') {
      console.log('\n❌ Exiting with error code due to performance issues');
      process.exit(1);
    }
    
    console.log('\n✅ Performance test completed successfully');
    
  } catch (error) {
    console.error('❌ Performance test failed:', error.message);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main().catch(error => {
    console.error('❌ Unexpected error:', error);
    process.exit(1);
  });
}

module.exports = {
  runArtilleryTest,
  validateBudgets,
  compareWithBaseline,
  generateReport,
  loadBudgets,
  hasBaseline,
  loadBaseline
};