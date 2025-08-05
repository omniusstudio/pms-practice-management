# Mental Health Practice Management System

A HIPAA-compliant Practice Management System designed for mental health practices.

## Repository Structure

This is a mono-repository containing multiple applications and packages:

```
├── apps/                    # Applications
│   ├── backend/            # REST API server
│   ├── frontend/           # Web application
│   └── infra/              # Infrastructure as code
├── packages/               # Shared packages
│   ├── shared-types/       # TypeScript type definitions
│   ├── shared-utils/       # Common utilities
│   └── shared-config/      # Shared configuration
├── docs/                   # Documentation
├── scripts/                # Build and deployment scripts
└── tools/                  # Development tools
```

## Prerequisites

- Node.js 18.x or higher
- Python 3.11 or higher
- Docker and Docker Compose
- Make

## Local Development Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd PMS
   ```

2. Install dependencies:
   ```bash
   make install
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your local configuration
   ```

4. Start development services:
   ```bash
   make dev
   ```

## Continuous Integration (CI)

The project includes a comprehensive CI pipeline that runs on every pull request to ensure code quality and prevent regressions.

### CI Pipeline Features

- **Automated Testing**: Backend and frontend tests with coverage reporting
- **Code Quality**: Linting and formatting checks for Python and TypeScript
- **Security Scanning**: Vulnerability detection with Trivy
- **Build Validation**: Ensures applications build successfully
- **Quality Gates**: Blocks merges on test failures or quality issues
- **Performance**: Completes in under 10 minutes with parallel execution

### Quick CI Commands

```bash
# Run all CI tests locally
make test-ci

# Run linting with CI output format
make lint-ci

# Run backend tests with coverage
make coverage-backend

# Run frontend tests with coverage
make coverage-frontend
```

### CI Pipeline Jobs

1. **Lint** (5 min) - Code quality checks
2. **Backend Tests** (8 min) - Python/FastAPI testing with PostgreSQL
3. **Frontend Tests** (6 min) - React/TypeScript testing with Vitest
4. **Security Scan** (5 min) - Vulnerability scanning
5. **Build** (8 min) - Application building and artifact storage
6. **Quality Gate** - Final validation and merge control

### Coverage Requirements

- **Backend**: 70% minimum coverage with pytest-cov
- **Frontend**: 70% minimum coverage with c8/vitest
- **Reports**: XML, HTML, and JSON formats generated
- **Integration**: Codecov for trend analysis

### Artifacts Generated

- Test coverage reports (HTML/XML/JSON)
- JUnit test results
- Build artifacts with version info
- Security scan results (SARIF)
- Lint reports (JSON)

For detailed CI pipeline documentation, see [CI_PIPELINE.md](CI_PIPELINE.md).

## Testing

### Running Tests

```bash
# Run all tests
make test

# Backend tests only
make test-backend

# Frontend tests only
make test-frontend

# With coverage reporting
make test-ci
```

### Test Structure

- **Backend**: pytest with FastAPI test client
- **Frontend**: Vitest with React Testing Library
- **Coverage**: Comprehensive reporting with thresholds
- **Security**: PHI-safe test data only

4. Start development services:
   ```bash
   make dev
   ```

## Available Commands

- `make install` - Install all dependencies
- `make dev` - Start development servers
- `make test` - Run all tests
- `make lint` - Run linters
- `make format` - Format code
- `make build` - Build all applications
- `make clean` - Clean build artifacts

## Creating New Services

Use the service template generator to create new applications or packages:

```bash
# Create a new backend service
./scripts/create-service.sh user-service backend

# Create a new frontend application
./scripts/create-service.sh admin-dashboard frontend

# Create a new shared package
./scripts/create-service.sh shared-auth package
```

Available service types:
- `backend` - FastAPI-based backend service
- `frontend` - React-based frontend application
- `package` - Shared TypeScript package

## Testing

Run the full test suite:
```bash
make test
```

Run tests for specific applications:
```bash
make test-backend
make test-frontend
```

## HIPAA Compliance

This system is designed with HIPAA compliance in mind:

- No PHI (Protected Health Information) in logs
- Encryption in transit and at rest
- Role-based access control (RBAC)
- Audit logging for all data access
- Secure error handling without PHI exposure

## Development Workflow

1. **Create a new service:**
   ```bash
   ./scripts/create-service.sh backend user-service
   ./scripts/create-service.sh frontend dashboard
   ./scripts/create-service.sh package shared-validation
   ```

2. **Run tests:**
   ```bash
   make test
   ```

3. **Lint and format code:**
   ```bash
   make lint
   make format
   ```

4. **Build applications:**
   ```bash
   make build
   ```

## Deployment

The system uses a blue/green deployment strategy with automated staging deployments and manual production deployments.

### Quick Deployment Commands

```bash
# Check deployment status
make deployment-status

# Deploy to staging (via GitHub Actions)
make deploy-staging

# Deploy to production (requires approval)
make deploy-production

# Rollback if needed
make rollback-staging
make rollback-production
```

### Deployment Pipeline

- **Staging:** Auto-deploys on `main` branch merge
- **Production:** Manual deployment with approval gate
- **Rollback:** One-click rollback to previous version
- **Monitoring:** Real-time deployment dashboard

For detailed deployment procedures, see [DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development guidelines.

## Security

For security concerns, please see our security policy in [SECURITY.md](./SECURITY.md).