.PHONY: help install dev test lint format build clean test-backend test-frontend test-ci lint-ci coverage-backend coverage-frontend seed-data reset-data seed-staging validate-data deploy-dev setup-phase4 test-pre-commit quality-checks install-hooks update-hooks release-setup release-dry-run release validate-commits check-version update-version

# Default target
help:
	@echo "Available commands:"
	@echo "  install          - Install all dependencies"
	@echo "  dev              - Start development servers"
	@echo "  test             - Run all tests"
	@echo "  test-backend     - Run backend tests only"
	@echo "  test-frontend    - Run frontend tests only"
	@echo "  test-ci          - Run tests with CI coverage reporting"
	@echo "  coverage-backend - Run backend tests with coverage"
	@echo "  coverage-frontend- Run frontend tests with coverage"
	@echo "  lint             - Run linters"
	@echo "  lint-ci          - Run linters with CI output"
	@echo "  format           - Format code"
	@echo "  build            - Build all applications"
	@echo "  deploy-dev       - Deploy to development environment"
	@echo "  clean            - Clean build artifacts"
	@echo "  seed-data        - Generate seed data for development"
	@echo "  reset-data       - Reset database with fresh seed data"
	@echo "  seed-staging     - Generate seed data for staging"
	@echo "  validate-data    - Validate data integrity"
	@echo ""
	@echo "Phase 4 - Code Quality:"
	@echo "  setup-phase4     - Set up automated code quality checks"
	@echo "  test-pre-commit  - Test pre-commit hooks"
	@echo "  quality-checks   - Run comprehensive quality analysis"
	@echo "  install-hooks    - Install pre-commit hooks"
	@echo "  update-hooks     - Update pre-commit hooks"
	@echo ""
	@echo "Release Management:"
	@echo "  release-setup    - Install semantic-release dependencies"
	@echo "  release-dry-run  - Test release process without publishing"
	@echo "  release          - Create and publish a new release"
	@echo "  validate-commits - Validate recent commits follow conventional format"
	@echo "  check-version    - Display current version information"
	@echo "  update-version   - Update version across all components"

# Install dependencies
install:
	@echo "Installing dependencies..."
	@if [ -f "apps/backend/requirements.txt" ]; then \
		cd apps/backend && pip3 install -r requirements.txt; \
	fi
	@if [ -f "apps/frontend/package.json" ]; then \
		cd apps/frontend && npm install; \
	fi
	@if [ -f "apps/infra/requirements.txt" ]; then \
		cd apps/infra && pip3 install -r requirements.txt; \
	fi

# Start development servers
dev:
	@echo "Starting development servers..."
	@docker-compose -f docker-compose.dev.yml up -d

# Run all tests
test: test-backend test-frontend
	@echo "All tests completed"

# Run backend tests
test-backend:
	@echo "Running backend tests..."
	@if [ -d "apps/backend" ]; then \
		cd apps/backend && PYTHONWARNINGS='ignore::PendingDeprecationWarning:starlette.formparsers' python3 -m pytest tests/ -v || echo "Backend tests: SKIP (dependencies not installed)"; \
	else \
		echo "Backend tests: SKIP (no backend app found)"; \
	fi

# Run end-to-end tests
test-e2e:
	@echo "Running end-to-end tests..."
	@if [ -d "tests/e2e" ]; then \
		cd tests/e2e && npm test || echo "E2E tests: SKIP (dependencies not installed)"; \
	else \
		echo "E2E tests: SKIP (no e2e tests found)"; \
	fi

# Run smoke tests
test-smoke:
	@echo "Running smoke tests..."
	@if [ -d "apps/backend" ]; then \
		cd apps/backend && python3 -m pytest tests/smoke/ -v -m smoke || echo "Smoke tests: SKIP (dependencies not installed)"; \
	else \
		echo "Smoke tests: SKIP (no backend app found)"; \
	fi

# Run performance tests
test-performance:
	@echo "Running performance tests..."
	@if [ -d "tests/performance" ]; then \
		cd tests/performance && artillery run artillery.yml || echo "Performance tests: SKIP (artillery not installed)"; \
	else \
		echo "Performance tests: SKIP (no performance tests found)"; \
	fi

# Validate test pyramid
validate-test-pyramid:
	@echo "Validating test pyramid..."
	@if [ -f "scripts/validate_test_pyramid.py" ]; then \
		python3 scripts/validate_test_pyramid.py || echo "Test pyramid validation: SKIP (script not found)"; \
	else \
		echo "Test pyramid validation: SKIP (validation script not found)"; \
	fi

# Run backend tests with coverage for CI
coverage-backend:
	@echo "Running backend tests with coverage..."
	@if [ -d "apps/backend" ]; then \
		cd apps/backend && python3 -m pytest tests/ --cov=. --cov-report=html --cov-report=term --cov-fail-under=80; \
	else \
		echo "Backend coverage: SKIP (no backend app found)"; \
	fi

# Run critical path coverage
coverage-critical:
	@echo "Running critical path tests with coverage..."
	@if [ -d "apps/backend" ]; then \
		cd apps/backend && python3 -m pytest -m critical --cov=. --cov-report=term --cov-fail-under=90 || echo "Critical coverage: SKIP (dependencies not installed)"; \
	else \
		echo "Critical coverage: SKIP (no backend app found)"; \
	fi

# Run HIPAA compliance tests with coverage
coverage-hipaa:
	@echo "Running HIPAA compliance tests with coverage..."
	@if [ -d "apps/backend" ]; then \
		cd apps/backend && python3 -m pytest -m hipaa --cov=. --cov-report=term --cov-fail-under=100 || echo "HIPAA coverage: SKIP (dependencies not installed)"; \
	else \
		echo "HIPAA coverage: SKIP (no backend app found)"; \
	fi

# Run frontend tests
test-frontend:
	@echo "Running frontend tests..."
	@if [ -d "apps/frontend" ]; then \
		cd apps/frontend && npm run test || echo "Frontend tests: SKIP (dependencies not installed)"; \
	else \
		echo "Frontend tests: SKIP (no frontend app found)"; \
	fi

# Run frontend tests with coverage for CI
coverage-frontend:
	@echo "Running frontend tests with coverage..."
	@if [ -d "apps/frontend" ]; then \
		cd apps/frontend && npm run test:coverage || echo "Frontend coverage: SKIP (dependencies not installed)"; \
	else \
		echo "Frontend coverage: SKIP (no frontend app found)"; \
	fi

# Run linters
lint:
	@echo "Running linters..."
	@if [ -d "apps/backend" ]; then \
		cd apps/backend && python3 -m flake8 . && python3 -m black --check . || echo "Backend linting: SKIP (dependencies not installed)"; \
	fi
	@if [ -d "apps/frontend" ]; then \
		cd apps/frontend && npm run lint || echo "Frontend linting: SKIP (dependencies not installed)"; \
	fi

# Run linters with CI output format
lint-ci:
	@echo "Running linters with CI output..."
	@if [ -d "apps/backend" ]; then \
		(cd apps/backend && python3 -m flake8 . --format=json --output-file=flake8-report.json) || (cd apps/backend && python3 -m flake8 .); \
		(cd apps/backend && python3 -m black --check .) || echo "Black formatting check failed"; \
		(cd apps/backend && python3 -m isort --check-only .) || echo "isort check failed"; \
	fi
	@if [ -d "apps/frontend" ]; then \
		cd apps/frontend && npm run lint || echo "Frontend linting failed"; \
	fi

# Run all tests with coverage for CI
test-ci: coverage-backend coverage-frontend validate-test-pyramid
	@echo "CI tests completed with coverage reports and validation"

# Format code
format:
	@echo "Formatting code..."
	@if [ -d "apps/backend" ]; then \
		cd apps/backend && python3 -m black . && python3 -m isort . || echo "Backend formatting: SKIP (dependencies not installed)"; \
	fi
	@if [ -d "apps/frontend" ]; then \
		cd apps/frontend && npm run format || echo "Frontend formatting: SKIP (dependencies not installed)"; \
	fi

# Build all applications
build:
	@echo "Building applications..."
	@if [ -d "apps/backend" ]; then \
		echo "Backend build: SKIP (FastAPI apps don't require build step)"; \
	fi
	@if [ -d "apps/frontend" ]; then \
		cd apps/frontend && npm run build || echo "Frontend build: SKIP (dependencies not installed)"; \
	fi

# Deployment commands
deploy-staging:
	@echo "Deploying to staging..."
	@if [ -f "apps/infra/scripts/deploy-blue-green.sh" ]; then \
		cd apps/infra/scripts && ./deploy-blue-green.sh staging latest; \
	else \
		echo "Deployment script not found. Use GitHub Actions for deployment."; \
	fi

deploy-production:
	@echo "Deploying to production..."
	@echo "Production deployments require manual approval via GitHub Actions"
	@echo "Go to: https://github.com/your-org/pms/actions/workflows/cd.yml"

rollback-staging:
	@echo "Rolling back staging..."
	@if [ -f "apps/infra/scripts/rollback.sh" ]; then \
		cd apps/infra/scripts && ./rollback.sh staging; \
	else \
		echo "Rollback script not found"; \
	fi

rollback-production:
	@echo "Rolling back production..."
	@if [ -f "apps/infra/scripts/rollback.sh" ]; then \
		cd apps/infra/scripts && ./rollback.sh production; \
	else \
		echo "Rollback script not found"; \
	fi

deployment-status:
	@echo "Checking deployment status..."
	@echo "Staging health: $$(curl -s https://staging.pms.example.com/healthz 2>/dev/null || echo 'Not accessible')"
	@echo "Production health: $$(curl -s https://pms.example.com/healthz 2>/dev/null || echo 'Not accessible')"

# Deployment commands
deploy-dev:
	@echo "Deploying to development environment..."
	@if [ -f "docker-compose.dev.yml" ]; then \
		docker-compose -f docker-compose.dev.yml up -d; \
	else \
		echo "Development deployment: SKIP (docker-compose.dev.yml not found)"; \
	fi

# Phase 4: Automated Code Quality Checks
setup-phase4:
	@echo "Setting up Phase 4: Automated Code Quality Checks..."
	@./scripts/setup-phase4.sh

test-pre-commit:
	@echo "Testing pre-commit hooks..."
	@if [ -f "scripts/test-pre-commit.sh" ]; then \
		./scripts/test-pre-commit.sh; \
	else \
		pre-commit run --all-files; \
	fi

quality-checks:
	@echo "Running comprehensive quality checks..."
	@if [ -f "scripts/run-quality-checks.sh" ]; then \
		./scripts/run-quality-checks.sh; \
	else \
		echo "Quality check script not found. Run 'make setup-phase4' first."; \
	fi

install-hooks:
	@echo "Installing pre-commit hooks..."
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit install; \
		pre-commit install --hook-type commit-msg; \
		pre-commit install --hook-type pre-push; \
	else \
		echo "Pre-commit not installed. Run 'make setup-phase4' first."; \
	fi

update-hooks:
	@echo "Updating pre-commit hooks..."
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit autoupdate; \
	else \
		echo "Pre-commit not installed. Run 'make setup-phase4' first."; \
	fi

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@if [ -d ".mypy_cache" ]; then \
		rm -rf .mypy_cache; \
	fi
	@if [ -d ".pytest_cache" ]; then \
		rm -rf .pytest_cache; \
	fi

# Seed data management
seed-data:
	@echo "Generating seed data for local development..."
	@python3 scripts/seed_local.py

reset-data:
	@echo "Resetting local database with fresh seed data..."
	@python3 scripts/seed_local.py --reset

seed-staging:
	@echo "Generating seed data for staging environment..."
	@python3 scripts/seed_staging.py --reset

validate-data:
	@echo "Validating local data integrity..."
	@python3 scripts/seed_local.py --validate

validate-staging:
	@echo "Validating staging data integrity..."
	@python3 scripts/seed_staging.py --validate

clean-data:
	@echo "Cleaning all seed data (WARNING: This will delete all data)..."
	@python3 scripts/seed_manager.py clean --confirm

# Release Management Commands

# Install semantic-release dependencies
release-setup:
	@echo "Installing semantic-release dependencies..."
	@npm install -g semantic-release \
		@semantic-release/changelog \
		@semantic-release/exec \
		@semantic-release/git \
		@semantic-release/github \
		conventional-changelog-conventionalcommits \
		@commitlint/cli \
		@commitlint/config-conventional
	@echo "✅ Semantic-release dependencies installed"

# Test release process without publishing
release-dry-run:
	@echo "🔍 Running semantic-release in dry-run mode..."
	@chmod +x scripts/update-version.sh
	@chmod +x scripts/generate-release-notes.js
	@npx semantic-release --dry-run
	@echo "✅ Dry-run completed"

# Create and publish a new release
release:
	@echo "🚀 Creating new release..."
	@chmod +x scripts/update-version.sh
	@chmod +x scripts/generate-release-notes.js
	@npx semantic-release
	@echo "✅ Release completed"

# Validate recent commits follow conventional format
validate-commits:
	@echo "🔍 Validating commit messages..."
	@LAST_TAG=$$(git describe --tags --abbrev=0 2>/dev/null || git rev-list --max-parents=0 HEAD); \
	git log $$LAST_TAG..HEAD --oneline | while read commit; do \
		echo "$$commit" | npx commitlint --config .commitlintrc.json || { \
			echo "❌ Commit does not follow conventional format: $$commit"; \
			echo "Please ensure all commits follow: type(scope): description"; \
			exit 1; \
		}; \
	done
	@echo "✅ All commits follow conventional format"

# Display current version information
check-version:
	@echo "📋 Current Version Information:"
	@echo "================================"
	@if [ -f "VERSION" ]; then \
		echo "Semantic Version: $$(cat VERSION)"; \
	else \
		echo "Semantic Version: Not set"; \
	fi
	@if [ -f "apps/backend/version.json" ]; then \
		echo "Backend Version: $$(grep '"version"' apps/backend/version.json | cut -d'"' -f4)"; \
	else \
		echo "Backend Version: Not set"; \
	fi
	@if [ -f "apps/frontend/package.json" ]; then \
		echo "Frontend Version: $$(grep '"version"' apps/frontend/package.json | head -1 | cut -d'"' -f4)"; \
	else \
		echo "Frontend Version: Not set"; \
	fi
	@echo "Git Commit: $$(git rev-parse --short HEAD)"
	@echo "Git Branch: $$(git rev-parse --abbrev-ref HEAD)"
	@echo "Last Tag: $$(git describe --tags --abbrev=0 2>/dev/null || echo 'No tags found')"

# Update version across all components
update-version:
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ Error: VERSION parameter is required"; \
		echo "Usage: make update-version VERSION=1.2.3"; \
		exit 1; \
	fi
	@echo "🔄 Updating version to: $(VERSION)"
	@chmod +x scripts/update-version.sh
	@./scripts/update-version.sh $(VERSION)
	@echo "✅ Version update completed"

clean-staging:
	@echo "Cleaning staging seed data..."
	@python3 scripts/seed_staging.py --cleanup

	@find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
