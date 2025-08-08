"""Data retention service for automated data lifecycle management."""

from typing import Any, Dict, List

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.appointment import Appointment
from models.audit import AuditLog
from models.auth_token import AuthToken
from models.data_retention_policy import DataRetentionPolicy, DataType, PolicyStatus
from models.encryption_key import EncryptionKey
from models.fhir_mapping import FHIRMapping
from models.ledger import LedgerEntry
from models.legal_hold import HoldStatus, LegalHold
from models.note import Note
from services.feature_flags_service import get_feature_flags_service


class DataRetentionService:
    """Service for managing data retention and purge operations.

    This service handles automated data lifecycle management,
    ensuring HIPAA compliance and legal hold requirements.
    """

    def __init__(self, session: AsyncSession):
        """Initialize the data retention service.

        Args:
            session: Database session
        """
        self.session = session
        self.feature_flags = get_feature_flags_service()

        # Map data types to their corresponding models
        self.data_type_models = {
            DataType.APPOINTMENTS: Appointment,
            DataType.NOTES: Note,
            DataType.AUDIT_LOGS: AuditLog,
            DataType.AUTH_TOKENS: AuthToken,
            DataType.ENCRYPTION_KEYS: EncryptionKey,
            DataType.FHIR_MAPPINGS: FHIRMapping,
            DataType.LEDGER_ENTRIES: LedgerEntry,
        }

    async def get_active_policies(self, tenant_id: str) -> List[DataRetentionPolicy]:
        """Get all active retention policies for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of active retention policies
        """
        query = select(DataRetentionPolicy).where(
            and_(
                DataRetentionPolicy.tenant_id == tenant_id,
                DataRetentionPolicy.status == PolicyStatus.ACTIVE,
            )
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_legal_holds(
        self, tenant_id: str, resource_type: str, resource_id: str = None
    ) -> List[LegalHold]:
        """Get active legal holds for a resource.

        Args:
            tenant_id: Tenant identifier
            resource_type: Type of resource
            resource_id: Specific resource ID (optional)

        Returns:
            List of active legal holds
        """
        conditions = [
            LegalHold.tenant_id == tenant_id,
            LegalHold.status == HoldStatus.ACTIVE,
            LegalHold.resource_type == resource_type,
        ]

        if resource_id:
            conditions.append(
                or_(
                    LegalHold.resource_id == resource_id,
                    LegalHold.resource_id.is_(None),
                )
            )

        query = select(LegalHold).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalars().all()

    async def is_resource_on_legal_hold(
        self, tenant_id: str, resource_type: str, resource_id: str
    ) -> bool:
        """Check if a resource is under legal hold.

        Args:
            tenant_id: Tenant identifier
            resource_type: Type of resource
            resource_id: Resource identifier

        Returns:
            bool: True if resource is on legal hold
        """
        holds = await self.get_legal_holds(tenant_id, resource_type, resource_id)

        return any(hold.is_active() for hold in holds)

    async def count_eligible_records(self, policy: DataRetentionPolicy) -> int:
        """Count records eligible for purging under a policy.

        Args:
            policy: Data retention policy

        Returns:
            Number of eligible records
        """
        model = self.data_type_models.get(policy.data_type)
        if not model:
            return 0

        cutoff_date = policy.calculate_retention_cutoff()

        # Base query for records older than cutoff
        query = (
            select(func.count())
            .select_from(model)
            .where(
                and_(
                    model.tenant_id == policy.tenant_id,
                    model.created_at < cutoff_date,
                )
            )
        )

        # Exclude records with legal holds if policy is not exempt
        if not policy.legal_hold_exempt:
            # This is a simplified check - in practice, you'd need
            # to join with legal holds or check each record individually
            pass

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def purge_records(
        self, policy: DataRetentionPolicy, dry_run: bool = None
    ) -> Dict[str, Any]:
        """Purge records according to a retention policy.

        Args:
            policy: Data retention policy
            dry_run: Whether to perform a dry run (defaults to policy setting)

        Returns:
            Dictionary with purge results
        """
        if dry_run is None:
            dry_run = policy.dry_run_only

        model = self.data_type_models.get(policy.data_type)
        if not model:
            return {
                "success": False,
                "error": f"Unknown data type: {policy.data_type}",
                "records_purged": 0,
            }

        cutoff_date = policy.calculate_retention_cutoff()
        records_purged = 0
        records_skipped = 0
        errors = []

        try:
            # Get records eligible for purging in batches
            offset = 0
            batch_size = policy.batch_size

            while True:
                # Query for records to purge
                query = (
                    select(model)
                    .where(
                        and_(
                            model.tenant_id == policy.tenant_id,
                            model.created_at < cutoff_date,
                        )
                    )
                    .offset(offset)
                    .limit(batch_size)
                )

                result = await self.session.execute(query)
                records = result.scalars().all()

                if not records:
                    break

                # Check each record for legal holds
                for record in records:
                    try:
                        # Skip if on legal hold (unless policy is exempt)
                        if not policy.legal_hold_exempt:
                            on_hold = await self.is_resource_on_legal_hold(
                                policy.tenant_id,
                                policy.data_type.value,
                                str(record.id),
                            )
                            if on_hold:
                                records_skipped += 1
                                continue

                        # Perform the purge (or simulate in dry run)
                        if not dry_run:
                            await self.session.delete(record)

                            # Log the purge action
                            await self._log_purge_action(policy, record, "purged")
                        else:
                            # Log the dry run action
                            await self._log_purge_action(
                                policy, record, "dry_run_purge"
                            )

                        records_purged += 1

                    except Exception as e:
                        errors.append(f"Error processing record {record.id}: {str(e)}")

                # Commit batch if not dry run
                if not dry_run:
                    await self.session.commit()

                offset += batch_size

                # Prevent infinite loops
                if offset > 100000:  # Safety limit
                    errors.append("Safety limit reached, stopping purge")
                    break

        except Exception as e:
            errors.append(f"Purge operation failed: {str(e)}")
            if not dry_run:
                await self.session.rollback()

        return {
            "success": len(errors) == 0,
            "records_purged": records_purged,
            "records_skipped": records_skipped,
            "errors": errors,
            "dry_run": dry_run,
            "policy_id": str(policy.id),
            "cutoff_date": cutoff_date.isoformat(),
        }

    async def _log_purge_action(
        self, policy: DataRetentionPolicy, record: Any, action: str
    ) -> None:
        """Log a purge action for audit purposes.

        Args:
            policy: Data retention policy
            record: Record being purged
            action: Action being performed
        """
        audit_log = AuditLog(
            tenant_id=policy.tenant_id,
            correlation_id=f"retention_purge_{policy.id}",
            user_id="system",
            action=action,
            resource_type=policy.data_type.value,
            resource_id=str(record.id),
            old_values={
                "retention_policy_id": str(policy.id),
                "retention_cutoff": (policy.calculate_retention_cutoff().isoformat()),
                "record_created_at": record.created_at.isoformat(),
            },
            new_values=None,
            ip_address="127.0.0.1",  # System action
            user_agent="DataRetentionService",
        )

        self.session.add(audit_log)

    async def execute_retention_policies(
        self, tenant_id: str, dry_run: bool = True
    ) -> Dict[str, Any]:
        """Execute all active retention policies for a tenant.

        Args:
            tenant_id: Tenant identifier
            dry_run: Whether to perform dry runs only

        Returns:
            Dictionary with execution results
        """
        # Check if data retention feature is enabled
        if not self.feature_flags.is_enabled("data_retention"):
            return {
                "success": False,
                "error": "Data retention feature is disabled",
                "policies_executed": 0,
            }

        policies = await self.get_active_policies(tenant_id)
        results = []

        for policy in policies:
            if not policy.should_execute_now():
                continue

            try:
                # Execute the policy
                result = await self.purge_records(policy, dry_run)
                result["policy_name"] = policy.policy_name
                results.append(result)

                # Update execution schedule
                if not dry_run:
                    policy.update_execution_schedule()
                    await self.session.commit()

            except Exception as e:
                results.append(
                    {
                        "success": False,
                        "policy_name": policy.policy_name,
                        "error": str(e),
                        "records_purged": 0,
                    }
                )

        return {
            "success": all(r["success"] for r in results),
            "policies_executed": len(results),
            "results": results,
            "dry_run": dry_run,
        }

    async def release_expired_legal_holds(self, tenant_id: str) -> Dict[str, Any]:
        """Release legal holds that have expired.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dictionary with release results
        """
        query = select(LegalHold).where(
            and_(
                LegalHold.tenant_id == tenant_id,
                LegalHold.status == HoldStatus.ACTIVE,
                LegalHold.auto_release.is_(True),
            )
        )

        result = await self.session.execute(query)
        holds = result.scalars().all()

        released_count = 0

        for hold in holds:
            if hold.should_auto_release():
                hold.release_hold("system")
                released_count += 1

        if released_count > 0:
            await self.session.commit()

        return {
            "success": True,
            "holds_released": released_count,
        }
