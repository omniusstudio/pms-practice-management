# Repository Housekeeping Plan

## Overview
This document outlines the housekeeping tasks identified for the PMS repository to improve maintainability, reduce storage usage, and eliminate technical debt.

## Identified Issues

### 1. Large Node Modules (581MB in tests/performance)
- **Issue**: Performance tests contain 545MB of node_modules
- **Impact**: Repository bloat, slow clones
- **Action**: Clean up and optimize performance test dependencies

### 2. Temporary and Cache Files
- **Issue**: Various temporary files found in node_modules
- **Impact**: Unnecessary storage usage
- **Action**: Clean up temporary files and update .gitignore

### 3. Disabled/Unused Files
- **Issue**: Multiple `.disabled` files and unused test files
- **Files**: 
  - `apps/backend/models/user.py.disabled`
  - `apps/backend/services/auth_service.py.disabled`
  - `apps/backend/tests/test_auth_tokens.py.disabled`
  - `apps/backend/tests/test_key_rotation.py.disabled`
  - `apps/backend/tests/test_schema_cleanup_audit.py.disabled`
- **Action**: Remove or consolidate disabled files

### 4. Placeholder Code and TODOs
- **Issue**: Extensive placeholder code in unit tests
- **Impact**: False test coverage, maintenance burden
- **Action**: Replace placeholders with proper implementations or remove

### 5. Duplicate Documentation
- **Issue**: Multiple README files with overlapping content
- **Files**: Multiple README.md files across different directories
- **Action**: Consolidate and cross-reference documentation

### 6. Large Generated Files
- **Issue**: Large generated files committed to repository
- **Files**: 
  - `test_pyramid_report.json` (780K)
  - `test_integration.db` (736K)
  - `apps/frontend/eslint-report.json` (large JSON)
- **Action**: Move to .gitignore or generate dynamically

## Housekeeping Tasks

### Phase 1: Immediate Cleanup (High Impact)
1. ✅ Clean up node_modules temporary files (25 files removed)
2. ✅ Remove disabled files (7 files removed)
3. ✅ Clean up large generated files (3 files, ~1.5MB saved)
4. ✅ Update .gitignore patterns (added test artifacts)
5. ✅ Create performance test cleanup script

### Phase 2: Code Quality (Medium Impact)
1. ⏳ Replace placeholder unit tests
2. ⏳ Consolidate duplicate documentation
3. ⏳ Remove TODO comments where appropriate

### Phase 3: Optimization (Low Impact)
1. ⏳ Optimize performance test dependencies
2. ⏳ Review and consolidate configuration files
3. ⏳ Archive old documentation

## Storage Impact
- **Before**: ~581MB tests directory
- **Target**: <100MB tests directory
- **Expected Savings**: ~480MB

## Implementation Status
- **Started**: January 2024
- **Phase 1 Target**: Complete within 1 hour
- **Full Completion**: Within 1 day

## Maintenance
- **Regular Cleanup**: Monthly
- **Automated Checks**: Add to CI pipeline
- **Documentation Review**: Quarterly

---
*This plan will be updated as housekeeping tasks are completed.*