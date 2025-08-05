# Release Management System

This document describes the automated semantic versioning and release management system implemented for the PMS (Practice Management System).

## Overview

The PMS now uses **semantic versioning** with automated release management, replacing the previous date-based versioning system. This provides:

- **Clear change communication**: Breaking changes, new features, and bug fixes are clearly identified
- **Automated release process**: Releases are created automatically based on conventional commits
- **HIPAA compliance**: All release notes are automatically sanitized for sensitive information
- **Rollback capabilities**: Enhanced version tracking for safer deployments
- **Integration with CI/CD**: Seamless integration with existing deployment pipelines

## Semantic Versioning

We follow [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes that require user action
- **MINOR** (0.X.0): New features that are backwards compatible
- **PATCH** (0.0.X): Bug fixes that are backwards compatible

### Examples
- `1.0.0` → `1.0.1`: Bug fix
- `1.0.1` → `1.1.0`: New feature
- `1.1.0` → `2.0.0`: Breaking change

## Conventional Commits

All commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Commit Types

| Type | Description | Version Bump |
|------|-------------|-------------|
| `feat` | New feature | MINOR |
| `fix` | Bug fix | PATCH |
| `perf` | Performance improvement | PATCH |
| `refactor` | Code refactoring | PATCH |
| `docs` | Documentation changes | None |
| `style` | Code style changes | None |
| `test` | Test changes | None |
| `chore` | Build/tooling changes | None |
| `ci` | CI/CD changes | None |
| `build` | Build system changes | None |
| `revert` | Revert previous commit | Depends on reverted commit |

### Breaking Changes

To indicate breaking changes, use one of these methods:

1. Add `!` after the type: `feat!: remove deprecated API`
2. Add `BREAKING CHANGE:` in the footer:
   ```
   feat: add new authentication system
   
   BREAKING CHANGE: The old authentication endpoints have been removed.
   Users must migrate to the new OAuth2 system.
   ```

### Examples

```bash
# New feature
feat(auth): add multi-factor authentication support

# Bug fix
fix(api): resolve patient data validation error

# Breaking change
feat!: migrate to new database schema

# Performance improvement
perf(db): optimize patient query performance

# Documentation
docs: update API documentation for v2 endpoints

# Chore
chore(deps): update security dependencies
```

## Release Process

### Automated Release (Recommended)

1. **Develop with conventional commits**:
   ```bash
   git commit -m "feat(patients): add patient search functionality"
   git commit -m "fix(auth): resolve login timeout issue"
   ```

2. **Push to main branch**:
   ```bash
   git push origin main
   ```

3. **Automated release workflow**:
   - GitHub Actions validates commits
   - Semantic-release determines version bump
   - Release notes are generated
   - GitHub release is created
   - CD pipeline is triggered

### Manual Release

1. **Install dependencies**:
   ```bash
   make release-setup
   ```

2. **Test release (dry-run)**:
   ```bash
   make release-dry-run
   ```

3. **Create release**:
   ```bash
   make release
   ```

## Available Commands

### Release Management

```bash
# Install semantic-release dependencies
make release-setup

# Test release process without publishing
make release-dry-run

# Create and publish a new release
make release

# Validate recent commits follow conventional format
make validate-commits

# Display current version information
make check-version

# Update version across all components
make update-version VERSION=1.2.3
```

### Testing

```bash
# Test the entire release system
./scripts/test-release-system.sh
```

## File Structure

### Configuration Files

- `.releaserc.json` - Semantic-release configuration
- `.commitlintrc.json` - Commit message validation rules
- `.github/workflows/release.yml` - Automated release workflow
- `.pre-commit-config.yaml` - Pre-commit hooks including commit validation

### Scripts

- `scripts/update-version.sh` - Updates version across all components
- `scripts/generate-release-notes.js` - Generates HIPAA-compliant release notes
- `scripts/test-release-system.sh` - Tests the entire release system

### Version Files

- `VERSION` - Current semantic version
- `apps/backend/version.json` - Backend version information
- `apps/frontend/package.json` - Frontend version information
- `CHANGELOG.md` - Automated changelog

## HIPAA Compliance

### Automatic Sanitization

All release notes are automatically sanitized to remove:

- Patient identifiers (SSN, MRN, etc.)
- Personal information (emails, phone numbers, addresses)
- API keys and tokens
- Database connection strings
- Internal system references
- IP addresses

### Compliance Notice

Every release includes a HIPAA compliance notice:

> **HIPAA Compliance Notice:** This release has been reviewed for HIPAA compliance. All sensitive information has been redacted from release notes.

### Manual Review

While automatic sanitization is comprehensive, always review release notes before publication, especially for:

- Custom patient identifiers
- Business-specific sensitive data
- Regulatory compliance information

## Integration with CI/CD

### GitHub Actions Workflows

1. **Release Workflow** (`.github/workflows/release.yml`):
   - Validates conventional commits
   - Creates semantic releases
   - Generates release notes
   - Triggers deployment

2. **CD Workflow** (`.github/workflows/cd.yml`):
   - Enhanced to accept semantic versions
   - Supports both semantic and date-based versions
   - Includes version information in deployments

### Version Endpoints

- **Backend**: `GET /version` - Returns current version and deployment info
- **Frontend**: Version info embedded in build artifacts

## Rollback Process

### Automated Rollback

```bash
# Trigger rollback via GitHub Actions
gh workflow run cd.yml -f environment=production -f rollback=true
```

### Manual Rollback

1. **Identify previous version**:
   ```bash
   aws ssm get-parameter --name "/pms/production/previous-version"
   ```

2. **Deploy previous version**:
   ```bash
   make deploy VERSION=1.2.3 ENVIRONMENT=production
   ```

## Monitoring and Alerts

### Version Tracking

- AWS SSM Parameter Store tracks current and previous versions
- Prometheus metrics include version information
- Health endpoints return version data

### Release Notifications

Configure notifications in `.github/workflows/release.yml`:

- Slack webhooks
- Email notifications
- Teams integration
- JIRA ticket updates

## Troubleshooting

### Common Issues

1. **Commit validation fails**:
   ```bash
   # Check commit format
   make validate-commits
   
   # Fix commit message
   git commit --amend -m "feat: your feature description"
   ```

2. **Release not created**:
   - Ensure commits follow conventional format
   - Check if changes warrant a release (docs/style changes don't trigger releases)
   - Verify GitHub token permissions

3. **Version mismatch**:
   ```bash
   # Check current versions
   make check-version
   
   # Manually update if needed
   make update-version VERSION=1.2.3
   ```

### Debug Mode

```bash
# Run semantic-release with debug output
DEBUG=semantic-release:* npx semantic-release --dry-run
```

## Migration from Date-Based Versioning

### Backward Compatibility

The system supports both semantic and date-based versions during the transition:

- New releases use semantic versioning
- Existing deployments with date-based versions continue to work
- Rollback to date-based versions is supported

### Migration Steps

1. **Team Training**: Ensure all developers understand conventional commits
2. **Gradual Adoption**: Start with feature branches, then main branch
3. **Monitor**: Watch for any issues during the transition period
4. **Full Migration**: Once stable, remove date-based version fallbacks

## Best Practices

### Commit Messages

- Use imperative mood: "add feature" not "added feature"
- Be specific: "fix login timeout" not "fix bug"
- Include scope when relevant: "feat(auth): add SSO support"
- Reference issues: "fix(api): resolve patient query issue (#123)"

### Release Strategy

- **Feature branches**: Use conventional commits from the start
- **Pull requests**: Ensure PR titles follow conventional format
- **Hotfixes**: Use `fix:` type for urgent production fixes
- **Breaking changes**: Communicate clearly and provide migration guides

### Version Planning

- **Major releases**: Plan breaking changes carefully
- **Minor releases**: Group related features together
- **Patch releases**: Release bug fixes quickly
- **Pre-releases**: Use for beta testing (`1.0.0-beta.1`)

## Support

For questions or issues with the release system:

1. **Documentation**: Check this guide and linked resources
2. **Testing**: Run `./scripts/test-release-system.sh`
3. **Debug**: Use dry-run mode to test changes
4. **Team**: Contact the development team for assistance

## Resources

- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Release](https://semantic-release.gitbook.io/)
- [Keep a Changelog](https://keepachangelog.com/)
- [HIPAA Compliance Guidelines](https://www.hhs.gov/hipaa/)

---

*This documentation is maintained as part of the PMS release management system. For updates or corrections, please submit a pull request.*