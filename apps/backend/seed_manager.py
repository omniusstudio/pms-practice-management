#!/usr/bin/env python3
"""Base seed manager for database seeding operations."""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from database import SessionLocal
from factories import (
    AppointmentFactory,
    ClientFactory,
    LedgerEntryFactory,
    LocationFactory,
    NoteFactory,
    PracticeProfileFactory,
    ProviderFactory,
)

logger = logging.getLogger(__name__)


class SeedManager:
    """Base seed manager for database operations."""

    def __init__(self, session: Optional[Session] = None):
        """Initialize seed manager with database session."""
        self.session = session or SessionLocal()
        self.factories = {
            "Client": ClientFactory,
            "Provider": ProviderFactory,
            "Appointment": AppointmentFactory,
            "Note": NoteFactory,
            "Location": LocationFactory,
            "PracticeProfile": PracticeProfileFactory,
            "LedgerEntry": LedgerEntryFactory,
        }
        self.performance_metrics = {
            "start_time": None,
            "end_time": None,
            "total_records_created": 0,
            "records_per_second": 0,
            "validation_time": 0,
            "errors": [],
        }

    def generate_seed_data(self, reset_db: bool = False) -> Dict[str, Any]:
        """Generate seed data - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement generate_seed_data")

    def _create_model_records(
        self, model_name: str, count: int, tenant_ids: List[str]
    ) -> int:
        """Create records for a specific model."""
        if model_name not in self.factories:
            logger.warning(f"No factory found for model: {model_name}")
            return 0

        factory = self.factories[model_name]
        created_count = 0

        try:
            for i in range(count):
                tenant_id = tenant_ids[i % len(tenant_ids)]
                record = factory.create(tenant_id=tenant_id)
                self.session.add(record)
                created_count += 1

            self.session.commit()
            logger.info(f"Created {created_count} {model_name} records")
            return created_count

        except Exception as e:
            self.session.rollback()
            error_msg = f"Failed to create {model_name} records: {str(e)}"
            logger.error(error_msg)
            self.performance_metrics["errors"].append(error_msg)
            return 0

    def close(self):
        """Close database session."""
        if self.session:
            self.session.close()
