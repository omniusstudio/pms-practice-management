# Mental Health PMS - Setup Guide

This document provides setup instructions for the Mental Health Practice Management System mono-repository.

## Repository Structure

The repository is organized as a mono-repo with the following structure:

```
├── apps/                    # Applications
│   ├── backend/            # FastAPI REST API server
│   ├── frontend/           # React web application
│   └── infra/              # Infrastructure as code (Terraform)
├── packages/               # Shared packages
│   ├── shared-types/       # TypeScript type definitions
│   ├── shared-utils/       # Common utilities
│   └── shared-config/      # Shared configuration
├── docs/                   # Documentation
├── scripts/                # Build and deployment scripts
├── tools/                  # Development tools
└── .github/                # GitHub workflows and templates
```

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd PMS
   ```

2. **Run tests** (validates setup)
   ```bash
   make test
   ```

3. **Install dependencies** (optional, for full development)
   ```bash
   make install
   ```

4. **Start development environment**
   ```bash
   make dev
   ```

## Acceptance Criteria Status

✅ **`make test` runs locally and in CI with zero failures**
- Backend tests: 3 passing tests
- Frontend tests: 3 passing tests
- No external dependencies required for basic testing

✅ **Linters/formatters run locally and in CI**
- Backend: Python (black, flake8, isort)
- Frontend: ESLint and Prettier
- Graceful handling of missing dependencies

✅ **New app/service template command documented**
- Script: `./scripts/create-service.sh`
- Supports: backend, frontend, package types
- Documented in README.md

## Development Workflow

### Creating New Services

Use the service template generator:

```bash
# Backend service
./scripts/create-service.sh user-auth backend

# Frontend app
./scripts/create-service.sh admin-panel frontend

# Shared package
./scripts/create-service.sh shared-validation package
```

### Running Tests

```bash
# All tests
make test

# Backend only
make test-backend

# Frontend only
make test-frontend
```

### Code Quality

```bash
# Run linters
make lint

# Format code
make format
```

## HIPAA Compliance Features

- **No PHI in logs**: Structured logging without sensitive data
- **Secure error handling**: Safe error messages without PHI exposure
- **Audit logging**: Built-in audit trail capabilities
- **Access controls**: RBAC framework ready
- **Encryption**: Configuration for data encryption at rest and in transit

## CI/CD Pipeline

The repository includes GitHub Actions workflows:

- **Continuous Integration** (`.github/workflows/ci.yml`)
  - Runs tests for all applications
  - Performs security scanning
  - Validates code quality
  - Builds applications

## Configuration Files

- **`.editorconfig`**: Consistent coding standards
- **`.gitignore`**: Excludes build artifacts and sensitive files
- **`CODEOWNERS`**: Defines code review requirements
- **`CONTRIBUTING.md`**: Development guidelines
- **Pull Request Template**: Ensures proper review process

## Next Steps

1. **Set up development environment**:
   - Install Python 3.11+
   - Install Node.js 18+
   - Install Docker and Docker Compose

2. **Configure environment variables**:
   - Copy `.env.example` to `.env.local`
   - Update with your local configuration

3. **Start contributing**:
   - Read `CONTRIBUTING.md`
   - Create feature branches
   - Follow the pull request template

## Support

For questions or issues:
- Check existing documentation in `/docs`
- Review `CONTRIBUTING.md` for development guidelines
- Create an issue using the GitHub issue templates