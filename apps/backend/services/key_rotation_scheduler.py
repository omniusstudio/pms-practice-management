"""Key rotation scheduler service for automated encryption key management."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from models.encryption_key import EncryptionKey, KeyStatus
from models.key_rotation_policy import KeyRotationPolicy, PolicyStatus, RotationTrigger
from services.encryption_key_service import EncryptionKeyService

logger = logging.getLogger(__name__)


class KeyRotationScheduler:
    """Service for automated key rotation based on policies.

    This service provides:
    - Scheduled key rotation based on time policies
    - Usage-based rotation monitoring
    - Event-driven rotation triggers
    - Comprehensive audit logging
    - Error handling and retry logic
    """

    def __init__(self, db_session: Session):
        """Initialize the key rotation scheduler.

        Args:
            db_session: Database session for operations
        """
        self.db = db_session
        self.correlation_id = str(uuid4())
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None

    async def start_scheduler(self, check_interval_minutes: int = 15) -> None:
        """Start the automated key rotation scheduler.

        Args:
            check_interval_minutes: How often to check for rotations
        """
        if self._running:
            logger.warning("Scheduler is already running")
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(
            self._scheduler_loop(check_interval_minutes)
        )
        logger.info(
            f"Key rotation scheduler started " f"(interval: {check_interval_minutes}m)"
        )

    async def stop_scheduler(self) -> None:
        """Stop the automated key rotation scheduler."""
        if not self._running:
            return

        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        logger.info("Key rotation scheduler stopped")

    async def _scheduler_loop(self, check_interval_minutes: int) -> None:
        """Main scheduler loop that checks for rotation needs.

        Args:
            check_interval_minutes: Check interval in minutes
        """
        interval_seconds = check_interval_minutes * 60

        while self._running:
            try:
                await self.check_and_rotate_keys()
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                # Continue running even if there's an error
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def check_and_rotate_keys(self) -> List[dict]:
        """Check all active policies and rotate keys as needed.

        Returns:
            List of rotation results
        """
        rotation_results = []

        try:
            # Get all active rotation policies
            active_policies = await self._get_active_policies()

            for policy in active_policies:
                try:
                    result = await self._process_policy(policy)
                    if result:
                        rotation_results.append(result)
                except Exception as e:
                    logger.error(
                        f"Error processing policy {policy.id}: {e}", exc_info=True
                    )
                    rotation_results.append(
                        {
                            "policy_id": str(policy.id),
                            "status": "error",
                            "error": str(e),
                        }
                    )

        except Exception as e:
            logger.error(f"Error checking rotation policies: {e}", exc_info=True)

        return rotation_results

    async def _get_active_policies(self) -> List[KeyRotationPolicy]:
        """Get all active rotation policies.

        Returns:
            List of active policies
        """
        stmt = select(KeyRotationPolicy).where(
            KeyRotationPolicy.status == PolicyStatus.ACTIVE
        )
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def _process_policy(self, policy: KeyRotationPolicy) -> Optional[dict]:
        """Process a single rotation policy.

        Args:
            policy: The rotation policy to process

        Returns:
            Rotation result if rotation occurred, None otherwise
        """
        # Check if rotation is needed
        if not policy.should_rotate_now():
            return None

        # Get keys associated with this policy
        keys_to_rotate = await self._get_keys_for_policy(policy)

        if not keys_to_rotate:
            logger.info(f"No keys found for policy {policy.policy_name}")
            return None

        rotation_results = []

        for key in keys_to_rotate:
            try:
                result = await self._rotate_key(key, policy)
                rotation_results.append(result)
            except Exception as e:
                logger.error(f"Failed to rotate key {key.id}: {e}", exc_info=True)
                rotation_results.append(
                    {"key_id": str(key.id), "status": "error", "error": str(e)}
                )

        # Update policy's last rotation time
        if hasattr(policy, "last_rotation_at"):
            policy.last_rotation_at = datetime.now(timezone.utc)
        policy.update_rotation_schedule()
        self.db.commit()

        success_results = [r for r in rotation_results if r["status"] == "success"]
        error_results = [r for r in rotation_results if r["status"] == "error"]
        success_count = len(success_results)
        error_count = len(error_results)

        return {
            "policy_id": str(policy.id),
            "policy_name": policy.policy_name,
            "status": "completed",
            "rotated_keys": success_count,
            "failed_keys": error_count,
            "results": rotation_results,
        }

    async def _get_keys_for_policy(
        self, policy: KeyRotationPolicy
    ) -> List[EncryptionKey]:
        """Get encryption keys that should be rotated for a policy.

        Args:
            policy: The rotation policy

        Returns:
            List of keys to rotate
        """
        stmt = select(EncryptionKey).where(
            and_(
                EncryptionKey.tenant_id == policy.tenant_id,
                EncryptionKey.key_type == policy.key_type,
                EncryptionKey.kms_provider == policy.kms_provider,
                EncryptionKey.status == KeyStatus.ACTIVE,
                EncryptionKey.rotation_policy_id == policy.id,
            )
        )
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def _rotate_key(self, key: EncryptionKey, policy: KeyRotationPolicy) -> dict:
        """Rotate a single encryption key.

        Args:
            key: The key to rotate
            policy: The rotation policy

        Returns:
            Rotation result
        """
        try:
            # Create encryption key service for this operation
            key_service = EncryptionKeyService(
                self.db, correlation_id=self.correlation_id
            )

            # Perform the rotation - generate new KMS key ID
            timestamp = int(datetime.now().timestamp())
            new_kms_key_id = f"{key.kms_key_id}_rotated_{timestamp}"
            old_key, new_key = await key_service.rotate_key(
                key.id, new_kms_key_id, rotated_by_token_id=None  # System rotation
            )

            logger.info(
                f"Successfully rotated key {key.id} -> {new_key.id} "
                f"for policy {policy.policy_name}"
            )

            return {
                "key_id": str(key.id),
                "new_key_id": str(new_key.id),
                "status": "success",
                "rotated_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Key rotation failed for {key.id}: {e}", exc_info=True)
            return {"key_id": str(key.id), "status": "error", "error": str(e)}

    async def create_rotation_policy(
        self,
        tenant_id: str,
        policy_name: str,
        key_type: str,
        kms_provider: str,
        rotation_trigger: RotationTrigger,
        rotation_interval_days: Optional[int] = None,
        created_by_token_id: Optional[UUID] = None,
        **kwargs,
    ) -> KeyRotationPolicy:
        """Create a new key rotation policy.

        Args:
            tenant_id: Tenant identifier
            policy_name: Name of the policy
            key_type: Type of keys to rotate
            kms_provider: KMS provider for keys
            rotation_trigger: What triggers rotation
            rotation_interval_days: Days between rotations (for time-based)
            created_by_token_id: Token ID of creator
            **kwargs: Additional policy parameters

        Returns:
            Created rotation policy
        """
        policy = KeyRotationPolicy(
            tenant_id=tenant_id,
            policy_name=policy_name,
            key_type=key_type,
            kms_provider=kms_provider,
            rotation_trigger=rotation_trigger,
            rotation_interval_days=rotation_interval_days,
            created_by_token_id=created_by_token_id,
            last_modified_by_token_id=created_by_token_id,
            correlation_id=self.correlation_id,
            **kwargs,
        )

        # Calculate initial rotation schedule
        if rotation_trigger == RotationTrigger.TIME_BASED and rotation_interval_days:
            policy.update_rotation_schedule()

        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)

        logger.info(f"Created rotation policy: {policy_name} for tenant {tenant_id}")
        return policy

    async def update_policy_status(
        self, policy_id: UUID, status: PolicyStatus
    ) -> KeyRotationPolicy:
        """Update the status of a rotation policy.

        Args:
            policy_id: Policy ID to update
            status: New status

        Returns:
            Updated policy
        """
        stmt = select(KeyRotationPolicy).where(KeyRotationPolicy.id == policy_id)
        result = self.db.execute(stmt)
        policy = result.scalar_one_or_none()

        if not policy:
            raise ValueError(f"Policy {policy_id} not found")

        if hasattr(policy, "status"):
            policy.status = status
        self.db.commit()
        self.db.refresh(policy)

        logger.info(f"Updated policy {policy_id} status to {status}")
        return policy

    async def get_rotation_history(
        self, tenant_id: str, limit: int = 100
    ) -> List[dict]:
        """Get rotation history for a tenant.

        Args:
            tenant_id: Tenant identifier
            limit: Maximum number of records

        Returns:
            List of rotation history records
        """
        stmt = (
            select(EncryptionKey)
            .where(
                and_(
                    EncryptionKey.tenant_id == tenant_id,
                    EncryptionKey.rotated_at.isnot(None),
                )
            )
            .order_by(EncryptionKey.rotated_at.desc())
            .limit(limit)
        )

        result = self.db.execute(stmt)
        rotated_keys = result.scalars().all()

        return [
            {
                "key_id": str(key.id),
                "key_name": key.key_name,
                "key_type": key.key_type,
                "rotated_at": (key.rotated_at.isoformat() if key.rotated_at else None),
                "parent_key_id": (
                    str(key.parent_key_id) if key.parent_key_id else None
                ),
                "status": key.status,
            }
            for key in rotated_keys
        ]
