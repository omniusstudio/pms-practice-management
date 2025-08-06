# Documentation Reorganization Plan

## Overview
Reorganize markdown files to consolidate documentation under `docs/` directory while keeping only essential root-level files.

## Current State Analysis

### Files to Keep in Root
- `README.md` - Main project documentation
- `CHANGELOG.md` - Version history (standard location)
- `CONTRIBUTING.md` - Contribution guidelines (standard location)

### Files to Move to docs/

#### Project Documentation
- `CI_PIPELINE.md` → `docs/ci-pipeline.md`
- `LOCAL-DEV-WORKFLOW.md` → `docs/local-dev-workflow.md`
- `TESTING.md` → `docs/testing.md`
- `TESTING_GUIDE.md` → `docs/testing-guide.md`
- `TEST_STRATEGY.md` → `docs/test-strategy.md`

#### Implementation & Phase Documentation
- `PHASE1_IMPROVEMENTS.md` → `docs/implementation/phase1-improvements.md`
- `PHASE2_IMPLEMENTATION_PLAN.md` → `docs/implementation/phase2-implementation-plan.md`
- `PHASE3_OPTIMIZATIONS.md` → `docs/implementation/phase3-optimizations.md`
- `PHASE4_COMPLETION_SUMMARY.md` → `docs/implementation/phase4-completion-summary.md`
- `PHASE4_IMPLEMENTATION.md` → `docs/implementation/phase4-implementation.md`

#### Technical Documentation
- `ENCRYPTION_KEYS_IMPLEMENTATION_SUMMARY.md` → `docs/technical/encryption-keys-implementation.md`
- `EVENT_BUS_ETL_IMPLEMENTATION.md` → `docs/technical/event-bus-etl-implementation.md`
- `METRICS_IMPLEMENTATION.md` → `docs/technical/metrics-implementation.md`
- `TERRAFORM_DOCS_INSTALLATION.md` → `docs/technical/terraform-docs-installation.md`

#### Project Management
- `ENHANCEMENT_TICKETS.md` → `docs/project/enhancement-tickets.md`
- `GITHUB_ISSUES_TEMPLATES.md` → `docs/project/github-issues-templates.md`
- `TEST_FAILURE_CARDS.md` → `docs/project/test-failure-cards.md`
- `TEST_IMPLEMENTATION_README.md` → `docs/project/test-implementation-readme.md`

#### Maintenance & Operations
- `HOUSEKEEPING_SUMMARY.md` → `docs/maintenance/housekeeping-summary.md`
- `REPOSITORY_HOUSEKEEPING_PLAN.md` → `docs/maintenance/repository-housekeeping-plan.md`
- `fix-registry-issues.md` → `docs/troubleshooting/fix-registry-issues.md`
- `infrastructure-test.md` → `docs/troubleshooting/infrastructure-test.md`

### Files to Keep in Current Locations

#### App-Specific Documentation (Keep in apps/)
- `apps/backend/AUTH0_INTEGRATION_README.md`
- `apps/backend/AUTOMATED_KEY_ROTATION_GUIDE.md`
- `apps/backend/DATABASE_DOCUMENTATION.md`
- `apps/backend/DATABASE_SETUP_GUIDE.md`
- `apps/backend/PHASE2_COMPLETION_SUMMARY.md`
- `apps/backend/docs/*` (already in proper location)
- `apps/infra/README.md`
- `apps/infra/kubernetes/*`

#### Component-Specific Documentation
- `scripts/README.md`
- `tests/performance/README.md`
- `tests/performance/test-requirements.md`
- `release-artifacts/*.md` (release notes should stay with artifacts)

#### Generated/Cache Files (Keep as-is)
- `.pytest_cache/README.md`
- `apps/backend/.pytest_cache/README.md`
- `.github/pull_request_template.md`
- `tests/e2e/playwright-report/data/*.md`

## Implementation Steps

### Phase 1: Create Directory Structure
```bash
mkdir -p docs/implementation
mkdir -p docs/technical
mkdir -p docs/project
mkdir -p docs/maintenance
mkdir -p docs/troubleshooting
```

### Phase 2: Move Files
1. Move files to new locations
2. Update internal references and links
3. Update README.md with new documentation structure
4. Update .gitignore if needed

### Phase 3: Update References
- Update links in README.md
- Update references in other documentation
- Update CI/CD workflows that reference moved files
- Update any scripts that reference moved files

## Benefits

1. **Cleaner Root Directory**: Only essential files remain in root
2. **Better Organization**: Logical grouping of documentation
3. **Easier Navigation**: Clear documentation hierarchy
4. **Improved Maintainability**: Centralized documentation location
5. **Better Developer Experience**: Easier to find relevant documentation

## Estimated Impact

- **Files to Move**: 19 files from root to docs/
- **New Directory Structure**: 5 new subdirectories in docs/
- **Files Remaining in Root**: 3 essential files (README, CHANGELOG, CONTRIBUTING)
- **References to Update**: Estimated 10-15 files with internal links

## Next Steps

1. Review and approve this plan
2. Execute the reorganization
3. Test all documentation links
4. Update team documentation guidelines
5. Add to repository maintenance procedures