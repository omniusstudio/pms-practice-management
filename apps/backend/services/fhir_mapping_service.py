"""FHIR mapping service for managing internal-to-FHIR resource mappings."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from models.fhir_mapping import FHIRMapping, FHIRMappingStatus, FHIRResourceType


class FHIRMappingService:
    """Service for managing FHIR resource mappings.

    This service provides methods for creating, reading, updating, and deleting
    FHIR resource mappings between internal system IDs and external FHIR IDs.
    """

    def __init__(self, session: Session):
        """Initialize the FHIR mapping service.

        Args:
            session: Database session for operations
        """
        self.session = session

    def create_mapping(
        self,
        internal_id: UUID,
        fhir_resource_type: FHIRResourceType,
        fhir_resource_id: str,
        tenant_id: Optional[str] = None,
        fhir_server_url: Optional[str] = None,
        correlation_id: Optional[str] = None,
        created_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> FHIRMapping:
        """Create a new FHIR resource mapping.

        Args:
            internal_id: Internal system resource ID
            fhir_resource_type: Type of FHIR resource
            fhir_resource_id: FHIR resource ID
            tenant_id: Tenant ID for multi-tenancy
            fhir_server_url: Base URL of FHIR server
            correlation_id: Request correlation ID for audit
            created_by: User or system creating the mapping
            notes: Additional notes

        Returns:
            Created FHIR mapping

        Raises:
            ValueError: If mapping already exists
        """
        # Check if mapping already exists
        existing = self.get_mapping_by_internal_id(
            internal_id, fhir_resource_type, tenant_id
        )
        if existing:
            raise ValueError(
                f"Mapping already exists for internal_id {internal_id} "
                f"and resource type {fhir_resource_type.value}"
            )

        mapping = FHIRMapping(
            internal_id=internal_id,
            fhir_resource_type=fhir_resource_type,
            fhir_resource_id=fhir_resource_id,
            fhir_server_url=fhir_server_url,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            created_by=created_by,
            notes=notes,
            status=FHIRMappingStatus.ACTIVE,
            is_active=True,
            error_count="0",
        )

        self.session.add(mapping)
        self.session.commit()
        self.session.refresh(mapping)

        return mapping

    def get_mapping_by_internal_id(
        self,
        internal_id: UUID,
        fhir_resource_type: FHIRResourceType,
        tenant_id: Optional[str] = None,
    ) -> Optional[FHIRMapping]:
        """Get FHIR mapping by internal ID and resource type.

        Args:
            internal_id: Internal system resource ID
            fhir_resource_type: Type of FHIR resource
            tenant_id: Tenant ID for filtering

        Returns:
            FHIR mapping if found, None otherwise
        """
        query = select(FHIRMapping).where(
            and_(
                FHIRMapping.internal_id == internal_id,
                FHIRMapping.fhir_resource_type == fhir_resource_type,
                FHIRMapping.is_active == True,  # noqa: E712
            )
        )

        if tenant_id:
            query = query.where(FHIRMapping.tenant_id == tenant_id)

        return self.session.execute(query).scalar_one_or_none()

    def get_mapping_by_fhir_id(
        self,
        fhir_resource_id: str,
        fhir_resource_type: FHIRResourceType,
        tenant_id: Optional[str] = None,
        fhir_server_url: Optional[str] = None,
    ) -> Optional[FHIRMapping]:
        """Get FHIR mapping by FHIR resource ID and type.

        Args:
            fhir_resource_id: FHIR resource ID
            fhir_resource_type: Type of FHIR resource
            tenant_id: Tenant ID for filtering
            fhir_server_url: FHIR server URL for filtering

        Returns:
            FHIR mapping if found, None otherwise
        """
        query = select(FHIRMapping).where(
            and_(
                FHIRMapping.fhir_resource_id == fhir_resource_id,
                FHIRMapping.fhir_resource_type == fhir_resource_type,
                FHIRMapping.is_active == True,  # noqa: E712
            )
        )

        if tenant_id:
            query = query.where(FHIRMapping.tenant_id == tenant_id)

        if fhir_server_url:
            query = query.where(FHIRMapping.fhir_server_url == fhir_server_url)

        return self.session.execute(query).scalar_one_or_none()

    def get_mappings_by_resource_type(
        self,
        fhir_resource_type: FHIRResourceType,
        tenant_id: Optional[str] = None,
        status: Optional[FHIRMappingStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FHIRMapping]:
        """Get FHIR mappings by resource type.

        Args:
            fhir_resource_type: Type of FHIR resource
            tenant_id: Tenant ID for filtering
            status: Mapping status for filtering
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of FHIR mappings
        """
        query = select(FHIRMapping).where(
            FHIRMapping.fhir_resource_type == fhir_resource_type
        )

        if tenant_id:
            query = query.where(FHIRMapping.tenant_id == tenant_id)

        if status:
            query = query.where(FHIRMapping.status == status)

        query = query.order_by(FHIRMapping.created_at.desc())
        query = query.limit(limit).offset(offset)

        return list(self.session.execute(query).scalars().all())

    def get_mappings_needing_sync(
        self,
        threshold_minutes: int = 60,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[FHIRMapping]:
        """Get mappings that need synchronization.

        Args:
            threshold_minutes: Minutes since last sync to consider sync needed
            tenant_id: Tenant ID for filtering
            limit: Maximum number of results

        Returns:
            List of mappings needing sync
        """
        from datetime import timedelta

        threshold_time = datetime.utcnow() - timedelta(minutes=threshold_minutes)

        query = select(FHIRMapping).where(
            and_(
                FHIRMapping.is_active == True,  # noqa: E712
                FHIRMapping.status == FHIRMappingStatus.ACTIVE,
                or_(
                    FHIRMapping.last_sync_at.is_(None),
                    FHIRMapping.last_sync_at < threshold_time,
                ),
            )
        )

        if tenant_id:
            query = query.where(FHIRMapping.tenant_id == tenant_id)

        query = query.order_by(FHIRMapping.last_sync_at.asc().nullsfirst())
        query = query.limit(limit)

        return list(self.session.execute(query).scalars().all())

    def get_mappings_with_errors(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[FHIRMapping]:
        """Get mappings that have errors.

        Args:
            tenant_id: Tenant ID for filtering
            limit: Maximum number of results

        Returns:
            List of mappings with errors
        """
        query = select(FHIRMapping).where(
            and_(
                FHIRMapping.is_active == True,  # noqa: E712
                or_(
                    FHIRMapping.status == FHIRMappingStatus.ERROR,
                    FHIRMapping.error_count != "0",
                ),
            )
        )

        if tenant_id:
            query = query.where(FHIRMapping.tenant_id == tenant_id)

        query = query.order_by(FHIRMapping.last_error_at.desc())
        query = query.limit(limit)

        return list(self.session.execute(query).scalars().all())

    def update_mapping(
        self,
        mapping_id: UUID,
        fhir_resource_id: Optional[str] = None,
        fhir_server_url: Optional[str] = None,
        status: Optional[FHIRMappingStatus] = None,
        version: Optional[str] = None,
        updated_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[FHIRMapping]:
        """Update an existing FHIR mapping.

        Args:
            mapping_id: ID of mapping to update
            fhir_resource_id: New FHIR resource ID
            fhir_server_url: New FHIR server URL
            status: New status
            version: New version/etag
            updated_by: User or system updating the mapping
            notes: Additional notes

        Returns:
            Updated mapping if found, None otherwise
        """
        mapping = self.session.get(FHIRMapping, mapping_id)
        if not mapping:
            return None

        if fhir_resource_id is not None:
            mapping.fhir_resource_id = fhir_resource_id

        if fhir_server_url is not None:
            mapping.fhir_server_url = fhir_server_url

        if status is not None:
            mapping.status = status

        if version is not None:
            mapping.version = version

        if updated_by is not None:
            mapping.updated_by = updated_by

        if notes is not None:
            mapping.notes = notes

        self.session.commit()
        self.session.refresh(mapping)

        return mapping

    def mark_mapping_synced(
        self,
        mapping_id: UUID,
        version: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> Optional[FHIRMapping]:
        """Mark a mapping as successfully synced.

        Args:
            mapping_id: ID of mapping to update
            version: FHIR resource version/etag
            updated_by: User or system updating the mapping

        Returns:
            Updated mapping if found, None otherwise
        """
        mapping = self.session.get(FHIRMapping, mapping_id)
        if not mapping:
            return None

        mapping.mark_synced(version)
        if updated_by:
            mapping.updated_by = updated_by

        self.session.commit()
        self.session.refresh(mapping)

        return mapping

    def record_mapping_error(
        self,
        mapping_id: UUID,
        error_message: str,
        updated_by: Optional[str] = None,
    ) -> Optional[FHIRMapping]:
        """Record an error for a mapping.

        Args:
            mapping_id: ID of mapping to update
            error_message: Error message to record
            updated_by: User or system updating the mapping

        Returns:
            Updated mapping if found, None otherwise
        """
        mapping = self.session.get(FHIRMapping, mapping_id)
        if not mapping:
            return None

        mapping.increment_error_count(error_message)
        if updated_by:
            mapping.updated_by = updated_by

        self.session.commit()
        self.session.refresh(mapping)

        return mapping

    def deactivate_mapping(
        self,
        mapping_id: UUID,
        reason: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> Optional[FHIRMapping]:
        """Deactivate a FHIR mapping.

        Args:
            mapping_id: ID of mapping to deactivate
            reason: Reason for deactivation
            updated_by: User or system updating the mapping

        Returns:
            Updated mapping if found, None otherwise
        """
        mapping = self.session.get(FHIRMapping, mapping_id)
        if not mapping:
            return None

        mapping.deactivate(reason)
        if updated_by:
            mapping.updated_by = updated_by

        self.session.commit()
        self.session.refresh(mapping)

        return mapping

    def get_mapping_stats(self, tenant_id: Optional[str] = None) -> Dict[str, int]:
        """Get statistics about FHIR mappings.

        Args:
            tenant_id: Tenant ID for filtering

        Returns:
            Dictionary with mapping statistics
        """
        base_query = select(FHIRMapping)
        if tenant_id:
            base_query = base_query.where(FHIRMapping.tenant_id == tenant_id)

        # Total mappings
        total_query = select(func.count(FHIRMapping.id))
        if tenant_id:
            total_query = total_query.where(FHIRMapping.tenant_id == tenant_id)
        total = self.session.execute(total_query).scalar() or 0

        # Active mappings
        active_query = select(func.count(FHIRMapping.id)).where(
            FHIRMapping.is_active == True  # noqa: E712
        )
        if tenant_id:
            active_query = active_query.where(FHIRMapping.tenant_id == tenant_id)
        active = self.session.execute(active_query).scalar() or 0

        # Mappings with errors
        errors_query = select(func.count(FHIRMapping.id)).where(
            or_(
                FHIRMapping.status == FHIRMappingStatus.ERROR,
                FHIRMapping.error_count != "0",
            )
        )
        if tenant_id:
            errors_query = errors_query.where(FHIRMapping.tenant_id == tenant_id)
        with_errors = self.session.execute(errors_query).scalar() or 0

        # Mappings needing sync (last sync > 1 hour ago or never synced)
        from datetime import timedelta

        threshold_time = datetime.utcnow() - timedelta(hours=1)
        sync_query = select(func.count(FHIRMapping.id)).where(
            and_(
                FHIRMapping.is_active == True,  # noqa: E712
                FHIRMapping.status == FHIRMappingStatus.ACTIVE,
                or_(
                    FHIRMapping.last_sync_at.is_(None),
                    FHIRMapping.last_sync_at < threshold_time,
                ),
            )
        )
        if tenant_id:
            sync_query = sync_query.where(FHIRMapping.tenant_id == tenant_id)
        needing_sync = self.session.execute(sync_query).scalar() or 0

        return {
            "total": total,
            "active": active,
            "with_errors": with_errors,
            "needing_sync": needing_sync,
        }

    def bulk_create_mappings(
        self,
        mappings_data: List[Dict],
        tenant_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Tuple[List[FHIRMapping], List[str]]:
        """Create multiple FHIR mappings in bulk.

        Args:
            mappings_data: List of mapping data dictionaries
            tenant_id: Tenant ID for all mappings
            created_by: User or system creating the mappings

        Returns:
            Tuple of (created_mappings, error_messages)
        """
        created_mappings = []
        error_messages = []

        for data in mappings_data:
            try:
                mapping = FHIRMapping(
                    internal_id=data["internal_id"],
                    fhir_resource_type=data["fhir_resource_type"],
                    fhir_resource_id=data["fhir_resource_id"],
                    fhir_server_url=data.get("fhir_server_url"),
                    tenant_id=tenant_id,
                    created_by=created_by,
                    notes=data.get("notes"),
                    status=FHIRMappingStatus.ACTIVE,
                    is_active=True,
                    error_count="0",
                )

                self.session.add(mapping)
                created_mappings.append(mapping)

            except Exception as e:
                error_messages.append(
                    f"Failed to create mapping for {data.get('internal_id')}: "
                    f"{str(e)}"
                )

        try:
            self.session.commit()
            for mapping in created_mappings:
                self.session.refresh(mapping)
        except Exception as e:
            self.session.rollback()
            error_messages.append(f"Failed to commit bulk mappings: {str(e)}")
            created_mappings = []

        return created_mappings, error_messages
