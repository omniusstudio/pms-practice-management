#!/usr/bin/env python3
"""
Kubernetes RBAC Audit Script for PMS
Generates compliance reports and identifies permission violations
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import logging


@dataclass
class RBACViolation:
    """Represents an RBAC policy violation"""
    service_account: str
    role: str
    resource: str
    verb: str
    severity: str
    description: str
    recommendation: str


@dataclass
class AccessReviewItem:
    """Represents an item for quarterly access review"""
    service_account: str
    role: str
    permissions: List[str]
    last_reviewed: str
    next_review: str
    status: str
    justification: str


class RBACAuditor:
    """Main RBAC auditing class"""

    def __init__(self, namespace: str = "pms"):
        self.namespace = namespace
        self.violations: List[RBACViolation] = []
        self.review_items: List[AccessReviewItem] = []
        self.kubectl_available = self._check_kubectl()

    def _check_kubectl(self) -> bool:
        """Check if kubectl is available and configured"""
        try:
            result = subprocess.run(
                ['kubectl', 'version', '--client'],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _run_kubectl(self, args: List[str]) -> Optional[Dict[str, Any]]:
        """Run kubectl command and return JSON output"""
        if not self.kubectl_available:
            print("Warning: kubectl not available")
            return None

        try:
            cmd = ['kubectl'] + args + ['-o', 'json']
            result = subprocess.run(
                cmd, capture_output=True, text=True
            )

            if result.returncode != 0:
                print(f"kubectl error: {result.stderr}")
                return None

            return json.loads(result.stdout)
        except Exception as e:
            print(f"Error running kubectl: {e}")
            return None

    def audit_service_accounts(self) -> List[Dict[str, Any]]:
        """Audit all service accounts in the namespace"""
        print(f"Auditing service accounts in namespace: {self.namespace}")

        sa_data = self._run_kubectl(
            ['get', 'serviceaccounts', '-n', self.namespace]
        )
        if not sa_data:
            return []

        service_accounts = []
        for sa in sa_data.get('items', []):
            sa_name = sa['metadata']['name']

            rb_data = self._run_kubectl(
                ['get', 'rolebindings', '-n', self.namespace]
            )
            role_bindings = []

            if rb_data:
                for rb in rb_data.get('items', []):
                    subjects = rb.get('spec', {}).get('subjects', [])
                    for subject in subjects:
                        if (subject.get('kind') == 'ServiceAccount' and
                                subject.get('name') == sa_name):
                            role_bindings.append({
                                'name': rb['metadata']['name'],
                                'role': rb['spec']['roleRef']['name']
                            })

            service_accounts.append({
                'name': sa_name,
                'metadata': sa.get('metadata', {}),
                'role_bindings': role_bindings
            })

        return service_accounts

    def audit_roles(self) -> List[Dict[str, Any]]:
        """Audit all roles and their permissions"""
        print(f"Auditing roles in namespace: {self.namespace}")

        roles_data = self._run_kubectl(
            ['get', 'roles', '-n', self.namespace]
        )
        if not roles_data:
            return []

        roles = []
        for role in roles_data.get('items', []):
            role_name = role['metadata']['name']
            rules = role.get('rules', [])

            permissions = []
            for rule in rules:
                resources = rule.get('resources', [])
                verbs = rule.get('verbs', [])
                resource_names = rule.get('resourceNames', [])

                for resource in resources:
                    for verb in verbs:
                        permission = f"{verb}:{resource}"
                        if resource_names:
                            names = ','.join(resource_names)
                            permission += f":{names}"
                        permissions.append(permission)

                        self._check_permission_violation(
                            role_name, resource, verb, resource_names
                        )

            roles.append({
                'name': role_name,
                'metadata': role.get('metadata', {}),
                'rules': rules,
                'permissions': permissions
            })

        return roles

    def _check_permission_violation(self, role_name: str, resource: str,
                                   verb: str, resource_names: List[str]):
        """Check for specific permission violations"""

        # Check for wildcard permissions
        if resource == '*' or verb == '*':
            self.violations.append(RBACViolation(
                service_account="N/A",
                role=role_name,
                resource=resource,
                verb=verb,
                severity="high",
                description=f"Wildcard permission: {verb}:{resource}",
                recommendation="Replace with specific resource names"
            ))

        # Check for excessive write permissions
        write_verbs = [
            'create', 'update', 'patch', 'delete', 'deletecollection'
        ]
        if verb in write_verbs and not resource_names:
            self.violations.append(RBACViolation(
                service_account="N/A",
                role=role_name,
                resource=resource,
                verb=verb,
                severity="medium",
                description=f"Unrestricted write: {verb}:{resource}",
                recommendation="Restrict to specific resource names"
            ))

        # Check for sensitive resource access
        sensitive = ['secrets', 'serviceaccounts', 'roles', 'rolebindings']
        if (resource in sensitive and
                verb in ['create', 'update', 'patch', 'delete']):
            self.violations.append(RBACViolation(
                service_account="N/A",
                role=role_name,
                resource=resource,
                verb=verb,
                severity="high",
                description=f"Sensitive resource access: {verb}:{resource}",
                recommendation="Ensure this is absolutely necessary"
            ))

    def generate_access_review(self, service_accounts: List[Dict],
                              roles: List[Dict]) -> List[AccessReviewItem]:
        """Generate quarterly access review items"""
        print("Generating quarterly access review items...")

        review_items = []
        current_date = datetime.now()

        for sa in service_accounts:
            sa_name = sa['name']
            metadata = sa.get('metadata', {})
            annotations = metadata.get('annotations', {})

            last_reviewed = annotations.get('last-reviewed', 'never')
            review_frequency = annotations.get('review-frequency', 'quarterly')

            # Calculate next review date
            if last_reviewed != 'never':
                try:
                    last_date = datetime.strptime(last_reviewed, '%Y-%m-%d')
                    if review_frequency == 'quarterly':
                        next_date = last_date + timedelta(days=90)
                    else:
                        next_date = last_date + timedelta(days=365)
                    next_review = next_date.strftime('%Y-%m-%d')
                except ValueError:
                    next_review = 'unknown'
            else:
                next_review = current_date.strftime('%Y-%m-%d')

            # Determine status
            status = 'active'
            if next_review != 'unknown':
                try:
                    next_date = datetime.strptime(next_review, '%Y-%m-%d')
                    if current_date > next_date:
                        status = 'overdue'
                except ValueError:
-                    pass
+                    logging.warning(
+                        "Could not parse next_review date '%s' for service account '%s'",
+                        next_review,
+                        sa_name,
+                    )

            # Get permissions
            permissions = []
            for rb in sa.get('role_bindings', []):
                role_name = rb['role']
                for role in roles:
                    if role['name'] == role_name:
                        permissions.extend(role['permissions'])

            review_items.append(AccessReviewItem(
                service_account=sa_name,
                role=', '.join([rb['role'] for rb in sa.get('role_bindings', [])]),
                permissions=permissions,
                last_reviewed=last_reviewed,
                next_review=next_review,
                status=status,
                justification=annotations.get(
                    'description', 'No justification provided'
                )
            ))

        self.review_items = review_items
        return review_items

    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        print("Generating compliance report...")

        service_accounts = self.audit_service_accounts()
        roles = self.audit_roles()
        review_items = self.generate_access_review(service_accounts, roles)

        total_violations = len(self.violations)
        high_violations = len([v for v in self.violations if v.severity == 'high'])
        overdue_reviews = len([r for r in review_items if r.status == 'overdue'])

        compliance_score = max(
            0, 100 - (high_violations * 20) - (total_violations * 5) - (overdue_reviews * 10)
        )

        return {
            'audit_date': datetime.now().isoformat(),
            'namespace': self.namespace,
            'compliance_score': compliance_score,
            'summary': {
                'total_service_accounts': len(service_accounts),
                'total_roles': len(roles),
                'total_violations': total_violations,
                'high_severity_violations': high_violations,
                'overdue_reviews': overdue_reviews
            },
            'service_accounts': service_accounts,
            'roles': roles,
            'violations': [asdict(v) for v in self.violations],
            'access_review_items': [asdict(r) for r in review_items],
            'recommendations': self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        high_count = len([v for v in self.violations if v.severity == 'high'])
        if high_count > 0:
            recommendations.append(
                "Address high-severity RBAC violations immediately"
            )

        overdue_count = len([r for r in self.review_items if r.status == 'overdue'])
        if overdue_count > 0:
            recommendations.append(
                f"Complete {overdue_count} overdue access reviews"
            )

        if len(self.violations) == 0:
            recommendations.append(
                "RBAC configuration appears compliant"
            )

        recommendations.extend([
            "Implement automated RBAC monitoring",
            "Schedule quarterly access reviews",
            "Document all service account justifications"
        ])

        return recommendations

    def save_report(self, report: Dict[str, Any], output_file: str = None):
        """Save compliance report to file"""
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"rbac_compliance_report_{timestamp}.json"

        output_path = Path(output_file)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"Report saved to: {output_path.absolute()}")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='RBAC Audit Tool for PMS')
    parser.add_argument('--namespace', '-n', default='pms')
    parser.add_argument('--output', '-o', help='Output file path')

    args = parser.parse_args()

    auditor = RBACAuditor(namespace=args.namespace)
    report = auditor.generate_compliance_report()

    print("\n" + "="*50)
    print("RBAC COMPLIANCE AUDIT SUMMARY")
    print("="*50)
    print(f"Compliance Score: {report['compliance_score']}/100")
    print(f"Total Violations: {report['summary']['total_violations']}")
    print(f"High Severity: {report['summary']['high_severity_violations']}")
    print(f"Overdue Reviews: {report['summary']['overdue_reviews']}")
    print("="*50)

    auditor.save_report(report, args.output)

    if report['summary']['high_severity_violations'] > 0:
        print("\nERROR: High-severity RBAC violations detected!")
        sys.exit(1)

    print("\nAudit completed successfully.")


if __name__ == '__main__':
    main()
