## Description

Briefly describe the changes in this PR.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)
- [ ] Performance improvement
- [ ] Security enhancement

## Related Issues

Fixes #(issue number)
Related to #(issue number)

## Changes Made

### Backend Changes
- [ ] API endpoints added/modified
- [ ] Database schema changes
- [ ] Business logic updates
- [ ] Authentication/authorization changes

### Frontend Changes
- [ ] UI components added/modified
- [ ] New pages or routes
- [ ] State management updates
- [ ] Accessibility improvements

### Infrastructure Changes
- [ ] CI/CD pipeline updates
- [ ] Docker/containerization changes
- [ ] Environment configuration
- [ ] Monitoring/logging updates

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] End-to-end tests added/updated
- [ ] Manual testing completed
- [ ] All existing tests pass

### Test Coverage
- Current coverage: __%
- Coverage after changes: __%

## Security Checklist

- [ ] No PHI (Protected Health Information) is logged or exposed
- [ ] Input validation implemented for all new endpoints
- [ ] Authentication and authorization properly enforced
- [ ] Error messages do not expose sensitive information
- [ ] Secrets are not hardcoded or committed
- [ ] HTTPS/TLS used for all external communications
- [ ] SQL injection prevention measures in place
- [ ] XSS prevention measures implemented

## HIPAA Compliance

- [ ] No PHI in logs, error messages, or debug output
- [ ] Audit logging implemented for data access
- [ ] Proper access controls enforced
- [ ] Data encryption at rest and in transit
- [ ] Minimum necessary access principle followed

## Performance Impact

- [ ] No significant performance degradation
- [ ] Database queries optimized
- [ ] Caching strategy considered
- [ ] Load testing performed (if applicable)

## Documentation

- [ ] Code is self-documenting with clear variable/function names
- [ ] Complex logic is commented
- [ ] API documentation updated (if applicable)
- [ ] README updated (if applicable)
- [ ] Migration guide provided (for breaking changes)

## Deployment

- [ ] Database migrations included (if applicable)
- [ ] Environment variables documented
- [ ] Feature flags configured (if applicable)
- [ ] Rollback plan documented
- [ ] Deployment steps verified in staging

## Screenshots/Videos

<!-- Include screenshots or videos of UI changes -->

## Additional Notes

<!-- Any additional information that reviewers should know -->

## Reviewer Checklist

### Code Quality
- [ ] Code follows project coding standards
- [ ] No code smells or anti-patterns
- [ ] Proper error handling implemented
- [ ] Logging is appropriate and secure

### Security Review
- [ ] Security implications reviewed
- [ ] No security vulnerabilities introduced
- [ ] Access controls properly implemented
- [ ] Data handling complies with HIPAA

### Testing Review
- [ ] Test coverage is adequate
- [ ] Tests are meaningful and comprehensive
- [ ] Edge cases are covered
- [ ] Tests pass consistently

### Documentation Review
- [ ] Code is well-documented
- [ ] API changes are documented
- [ ] User-facing changes are documented

---

**By submitting this PR, I confirm that:**
- I have tested these changes thoroughly
- I have followed the project's coding standards
- I have ensured HIPAA compliance in all changes
- I have not introduced any security vulnerabilities
- I have updated relevant documentation