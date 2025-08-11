# IAM Policy Documentation

## Overview

This document outlines the Identity and Access Management (IAM) policies for the Mental Health Practice Management System, implementing least-privilege access control principles across all environments.

## Kubernetes RBAC Policies

### Service Account Strategy

Each service has a dedicated service account with minimal required permissions:

- **pms-backend**: API server with database and configuration access
- **pms-frontend**: Static content server with configuration access only
- **pms-backup**: Backup operations with read-only access to resources
- **pms-monitoring**: Metrics collection with read-only cluster access

### Environment-Specific Roles

#### Development Environment
- **Broader logging access** for debugging
- **Pod exec permissions** for troubleshooting
- **ConfigMap write access** for configuration testing

#### Staging Environment
- **Production-like restrictions** with limited debugging access
- **Read-only access** to most resources
- **Controlled write access** to specific resources

#### Production Environment
- **Minimal required permissions** only
- **No debugging access**
- **Strict resource isolation**
- **Audit logging** for all access

### Least-Privilege Principles Applied

1. **No Wildcard Permissions**: All resource access is explicitly defined
2. **Namespace Isolation**: Services can only access resources in their namespace
3. **Resource-Specific Access**: Permissions granted only for required resource types
4. **Verb Restrictions**: Only necessary actions (get, list, create, etc.) are allowed
5. **Time-Based Access**: Temporary elevated permissions for maintenance windows

## Application RBAC Policies

### User Roles and Permissions

#### Administrator
- **Full system access** including user management
- **Audit trail access** for compliance reviews
- **System configuration** management
- **Financial reports** and billing access

#### Clinician
- **Patient data access** (read/write)
- **Clinical notes** management
- **Appointment scheduling**
- **Treatment plan** creation and updates

#### Biller
- **Billing data access** (read/write)
- **Financial reports** (read-only)
- **Patient information** (limited to billing-relevant data)
- **Insurance claims** management

#### Front Desk
- **Appointment management** (read/write)
- **Patient registration** (limited fields)
- **Basic patient information** (non-clinical)
- **Schedule viewing** for all providers

### Permission Matrix

| Resource | Admin | Clinician | Biller | Front Desk |
|----------|-------|-----------|--------|-----------|
| Patient PHI | Full | Clinical Only | Billing Only | Registration Only |
| Appointments | Full | Own + Assigned | Read Only | Full |
| Financial Data | Full | None | Full | None |
| User Management | Full | None | None | None |
| System Config | Full | None | None | None |
| Audit Logs | Full | Own Actions | Own Actions | Own Actions |

## Access Review Process

### Quarterly Review Cycle

1. **Week 1**: Automated access audit report generation
2. **Week 2**: Manual review of user permissions and roles
3. **Week 3**: Cleanup of unused accounts and excessive permissions
4. **Week 4**: Documentation updates and compliance reporting

### Review Checklist

- [ ] All service accounts have minimum required permissions
- [ ] No wildcard permissions in any role
- [ ] User roles match current job responsibilities
- [ ] Inactive accounts are disabled or removed
- [ ] Temporary access grants are expired or renewed
- [ ] Audit logs show no unauthorized access attempts
- [ ] Compliance requirements are met (HIPAA, SOC2)

### Automated Monitoring

- **Daily**: Permission usage monitoring
- **Weekly**: Unused permission identification
- **Monthly**: Role effectiveness analysis
- **Quarterly**: Comprehensive access review

## Compliance and Audit

### HIPAA Requirements

- **Minimum Necessary Standard**: Users can only access PHI required for their job function
- **Access Controls**: Technical safeguards prevent unauthorized PHI access
- **Audit Controls**: All PHI access is logged and monitored
- **Assigned Security Responsibility**: Clear ownership of access management

### Audit Trail Requirements

- **User Authentication**: All login attempts logged
- **Resource Access**: All data access logged with user context
- **Permission Changes**: All role/permission modifications logged
- **System Changes**: All configuration changes logged

## Implementation Timeline

### Phase 1: Kubernetes RBAC Enhancement (Current)
- Enhanced service account permissions
- Environment-specific role definitions
- Removal of wildcard permissions
- Implementation of resource-specific access

### Phase 2: Application RBAC Improvements
- Enhanced role validation middleware
- Quarterly access review API endpoints
- Access review logging implementation
- Access review checklist automation

### Phase 3: Monitoring & Compliance
- RBAC audit logging enhancement
- Access review dashboard creation
- Automated access review reminders
- Compliance reporting automation

## Rollback Procedures

### Emergency Access Restoration

1. **Immediate**: Restore previous RBAC configuration from backup
2. **Short-term**: Grant temporary elevated permissions for critical operations
3. **Long-term**: Investigate and fix permission issues while maintaining security

### Configuration Backup

- **Daily**: Automated backup of all RBAC configurations
- **Pre-change**: Manual backup before any permission modifications
- **Versioned**: All configurations stored in version control

## Security Considerations

### Threat Mitigation

- **Privilege Escalation**: Strict role boundaries prevent unauthorized elevation
- **Lateral Movement**: Namespace isolation limits blast radius
- **Data Exfiltration**: Minimal data access reduces exposure risk
- **Insider Threats**: Comprehensive audit logging enables detection

### Regular Security Reviews

- **Monthly**: Permission effectiveness analysis
- **Quarterly**: Comprehensive security assessment
- **Annually**: Full IAM policy review and update

---

*Last Updated: January 2025*
*Next Review: April 2025*
*Document Owner: Security Team*