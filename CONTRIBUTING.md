# Contributing to Mental Health Practice Management System

Thank you for contributing to our HIPAA-compliant Practice Management System. This document provides guidelines for contributing to the project.

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code.

## Development Workflow

### 1. Setting Up Your Development Environment

1. Fork the repository
2. Clone your fork locally
3. Install dependencies: `make install`
4. Create a feature branch: `git checkout -b feature/your-feature-name`

### 2. Making Changes

1. Make your changes in the appropriate directory:
   - Backend changes: `apps/backend/`
   - Frontend changes: `apps/frontend/`
   - Infrastructure changes: `apps/infra/`
   - Shared code: `packages/`

2. Follow the coding standards:
   - Run `make lint` to check for linting errors
   - Run `make format` to format your code
   - Run `make test` to ensure all tests pass

### 3. Committing Changes

Use conventional commit messages:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(backend): add patient authentication endpoint
fix(frontend): resolve login form validation issue
docs: update API documentation for user management
```

### 4. Pull Request Process

1. Push your changes to your fork
2. Create a pull request against the main branch
3. Fill out the pull request template completely
4. Ensure all CI checks pass
5. Request review from appropriate team members

## Coding Standards

### General Principles

1. **HIPAA Compliance First**: Never log, store, or expose PHI
2. **Security by Default**: Implement least privilege access
3. **Test Coverage**: Maintain high test coverage (>80%)
4. **Documentation**: Document all public APIs and complex logic

### Backend (Python)

- Follow PEP 8 style guide
- Use type hints for all function signatures
- Maximum line length: 88 characters
- Use `black` for formatting and `flake8` for linting
- Write docstrings for all public functions and classes

```python
def create_patient(patient_data: PatientCreateRequest) -> PatientResponse:
    """Create a new patient record.
    
    Args:
        patient_data: Patient information for creation
        
    Returns:
        Created patient information (no PHI in logs)
        
    Raises:
        ValidationError: If patient data is invalid
        AuthorizationError: If user lacks permission
    """
    pass
```

### Frontend (TypeScript/React)

- Use TypeScript for all new code
- Follow React best practices and hooks patterns
- Use functional components with hooks
- Maximum line length: 100 characters
- Use Prettier for formatting and ESLint for linting

```typescript
interface PatientFormProps {
  onSubmit: (data: PatientFormData) => void;
  loading?: boolean;
}

export const PatientForm: React.FC<PatientFormProps> = ({ onSubmit, loading = false }) => {
  // Component implementation
};
```

### Database

- Use migrations for all schema changes
- Include both up and down migration scripts
- Add appropriate indexes for performance
- Include data validation constraints
- Never include PHI in seed data

## Testing Guidelines

### Unit Tests

- Write tests for all business logic
- Mock external dependencies
- Test both happy path and error cases
- Use descriptive test names

### Integration Tests

- Test API endpoints end-to-end
- Use test databases with anonymized data
- Test authentication and authorization
- Verify error handling and logging

### Security Testing

- Test RBAC enforcement
- Verify PHI is not exposed in errors
- Test input validation and sanitization
- Verify audit logging functionality

## HIPAA Compliance Guidelines

### Do's

- ✅ Use correlation IDs for request tracking
- ✅ Log user actions for audit trails
- ✅ Encrypt sensitive data at rest and in transit
- ✅ Implement proper access controls
- ✅ Use secure error messages

### Don'ts

- ❌ Never log PHI (names, SSNs, medical records, etc.)
- ❌ Don't expose PHI in error messages
- ❌ Don't store PHI in client-side storage
- ❌ Don't include PHI in URLs or query parameters
- ❌ Don't commit secrets or credentials to version control

## Review Process

### Code Review Checklist

- [ ] Code follows project coding standards
- [ ] All tests pass and coverage is maintained
- [ ] No PHI is logged or exposed
- [ ] Security best practices are followed
- [ ] Documentation is updated if needed
- [ ] Breaking changes are documented
- [ ] Performance impact is considered

### Security Review

All changes involving:
- Authentication/authorization
- Data access patterns
- External integrations
- Logging/monitoring

Require additional security review from the security team.

## Getting Help

- Check existing documentation in `/docs`
- Search existing issues and pull requests
- Ask questions in team chat channels
- Schedule pair programming sessions for complex features

## Release Process

1. All changes must be reviewed and approved
2. CI/CD pipeline must pass all checks
3. Security scan must pass
4. Staging deployment must be tested
5. Production deployment requires additional approval

Thank you for helping us build a secure, compliant, and reliable Practice Management System!