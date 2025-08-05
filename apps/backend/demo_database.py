#!/usr/bin/env python3
"""Demonstration script for the HIPAA-compliant database infrastructure."""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Set test environment
os.environ["DATABASE_URL"] = "sqlite:///demo.db"
os.environ["ENVIRONMENT"] = "demo"

from models.audit import AuditLog  # noqa: E402

# Import models after setting environment
from models.base import Base  # noqa: E402
from models.client import Client  # noqa: E402
from models.provider import Provider  # noqa: E402


def create_demo_database():
    """Create and populate a demo database."""

    logger.info("🏥 HIPAA-Compliant Mental Health PMS Database Demo")
    logger.info("=" * 55)

    # Create engine and tables
    engine = create_engine("sqlite:///demo.db", echo=False)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        logger.info("📋 Creating demo data")

        # Create a sample client
        client = Client(
            first_name="Demo",
            last_name="Client",
            date_of_birth=datetime(1985, 6, 15).date(),
            email="demo.client@example.com",
            phone="555-0123",
        )

        session.add(client)
        session.flush()  # Get the ID

        logger.info(f"✅ Created client: {client.full_name}")
        logger.info(f"   ID: {client.id}")
        logger.info(f"   Age: {client.get_age()}")
        logger.info(f"   Display: {client.display_name}")

        # Create a sample provider
        provider = Provider(
            first_name="Dr. Sarah",
            last_name="Johnson",
            email="dr.johnson@clinic.com",
            phone="555-0200",
            license_number="PSY12345",
            license_state="CA",
            specialty="Clinical Psychology",
        )

        session.add(provider)
        session.flush()

        logger.info(f"✅ Created provider: {provider.full_name}")
        logger.info(f"   ID: {provider.id}")
        logger.info(f"   Specialty: {provider.specialty}")
        logger.info(f"   License: {provider.license_number}")
        logger.info(f"   Active: {provider.is_active}")

        # Create audit log entry
        audit_log = AuditLog(
            correlation_id="demo-correlation-123",
            user_id=provider.id,
            action="CREATE",
            resource_type="Client",
            resource_id=client.id,
            ip_address="127.0.0.1",
            user_agent="Demo Script",
        )

        session.add(audit_log)
        session.commit()

        logger.info("✅ Created audit log entry")
        logger.info(f"   Action: {audit_log.action}")
        logger.info(f"   Resource: {audit_log.resource_type}")
        logger.info(f"   Correlation ID: {audit_log.correlation_id}")

        # Demonstrate PHI protection
        logger.info("🔒 HIPAA Compliance Demonstration:")
        logger.info(f"   Client repr (PHI protected): {repr(client)}")
        logger.info(f"   Provider repr (PHI protected): {repr(provider)}")

        # Show database queries
        logger.info("📊 Database Queries:")

        # Count records
        client_count = session.query(Client).count()
        provider_count = session.query(Provider).count()
        audit_count = session.query(AuditLog).count()

        logger.info(f"   Clients: {client_count}")
        logger.info(f"   Providers: {provider_count}")
        logger.info(f"   Audit logs: {audit_count}")

        # Show audit trail
        logger.info("📋 Audit Trail:")
        audit_logs = session.query(AuditLog).all()
        for log in audit_logs:
            logger.info(f"   {log.created_at}: {log.action} {log.resource_type}")

        logger.info("✅ Demo completed successfully!")
        logger.info("💡 Key Features Demonstrated:")
        logger.info("   • Database model creation and relationships")
        logger.info("   • HIPAA-compliant audit logging")
        logger.info("   • PHI protection in string representations")
        logger.info("   • Correlation ID tracking for requests")
        logger.info("   • Timestamp tracking for all records")

        return True

    except Exception as e:
        logger.error(f"Error during demo: {e}")
        session.rollback()
        return False

    finally:
        session.close()


def cleanup_demo():
    """Clean up demo database."""
    demo_db = Path("demo.db")
    if demo_db.exists():
        demo_db.unlink()
        logger.info("🧹 Demo database cleaned up")


if __name__ == "__main__":
    try:
        success = create_demo_database()

        if success:
            logger.info("🎉 Database infrastructure is working correctly!")
            logger.info("📁 Demo database saved as 'demo.db'")
            logger.info("   You can inspect it with: sqlite3 demo.db")

            # Ask if user wants to keep the demo database
            response = input("\nKeep demo database? (y/N): ").lower().strip()
            if response != "y":
                cleanup_demo()
        else:
            logger.error("Demo failed - check error messages above")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
        cleanup_demo()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        cleanup_demo()
        sys.exit(1)
