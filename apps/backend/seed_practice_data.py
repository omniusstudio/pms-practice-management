#!/usr/bin/env python3
"""Seed script for practice profiles and locations data."""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from models.location import Location  # noqa: E402
from models.practice_profile import PracticeProfile  # noqa: E402

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://omniusstudio:8Z3Rx04LMNw3@localhost:5432/pmsdb"
)

# Create engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_practice_data():
    """Seed the database with sample practice profiles and locations."""
    session = SessionLocal()

    try:
        # Check if data already exists
        existing_practices = session.query(PracticeProfile).count()
        if existing_practices > 0:
            print(
                f"Database already contains {existing_practices} "
                f"practice profiles. Skipping seed."
            )
            return

        # Create sample practice profiles
        practices = [
            PracticeProfile(
                name="Mindful Wellness Center",
                legal_name="Mindful Wellness Center LLC",
                tax_id="12-3456789",
                npi_number="1234567890",
                email="contact@mindfulwellness.com",
                phone="(555) 123-4567",
                fax="(555) 123-4568",
                website="https://mindfulwellness.com",
                address_line1="123 Therapy Lane",
                address_line2="Suite 200",
                city="San Francisco",
                state="CA",
                zip_code="94102",
                country="United States",
                timezone="America/Los_Angeles",
                default_appointment_duration="50",
                accepts_new_patients=True,
                is_active=True,
                billing_provider_name="Mindful Billing Services",
                billing_contact_email="billing@mindfulwellness.com",
                billing_contact_phone="(555) 123-4569",
                description=(
                    "A comprehensive mental health practice focused on "
                    "mindfulness-based therapy and holistic wellness "
                    "approaches."
                ),
                administrative_notes=("Primary practice location established 2020"),
                tenant_id="tenant_mindful_001",
            ),
            PracticeProfile(
                name="Harbor Counseling Associates",
                legal_name="Harbor Counseling Associates Inc",
                tax_id="98-7654321",
                npi_number="0987654321",
                email="info@harborcounseling.org",
                phone="(555) 987-6543",
                fax="(555) 987-6544",
                website="https://harborcounseling.org",
                address_line1="456 Harbor View Drive",
                city="Seattle",
                state="WA",
                zip_code="98101",
                country="United States",
                timezone="America/Los_Angeles",
                default_appointment_duration="45",
                accepts_new_patients=True,
                is_active=True,
                billing_provider_name="Northwest Medical Billing",
                billing_contact_email="billing@harborcounseling.org",
                billing_contact_phone="(555) 987-6545",
                description=(
                    "Specialized in trauma-informed care and family "
                    "therapy services."
                ),
                administrative_notes=(
                    "Established 2018, expanded to multiple locations"
                ),
                tenant_id="tenant_harbor_002",
            ),
            PracticeProfile(
                name="Serenity Mental Health Group",
                legal_name="Serenity Mental Health Group PLLC",
                tax_id="55-1122334",
                npi_number="5551122334",
                email="contact@serenitymh.com",
                phone="(555) 555-1234",
                fax="(555) 555-1235",
                website="https://serenitymh.com",
                address_line1="789 Peaceful Way",
                address_line2="Building A",
                city="Austin",
                state="TX",
                zip_code="78701",
                country="United States",
                timezone="America/Chicago",
                default_appointment_duration="60",
                accepts_new_patients=False,
                is_active=True,
                billing_provider_name="Texas Healthcare Billing",
                billing_contact_email="billing@serenitymh.com",
                billing_contact_phone="(555) 555-1236",
                description=(
                    "Comprehensive mental health services with a focus on "
                    "anxiety and depression treatment."
                ),
                administrative_notes=("Currently at capacity, waitlist available"),
                tenant_id="tenant_serenity_003",
            ),
        ]

        # Add practices to session
        for practice in practices:
            session.add(practice)

        # Flush to get IDs
        session.flush()

        # Create sample locations for each practice
        locations = []

        # Locations for Mindful Wellness Center
        mindful_practice = practices[0]
        locations.extend(
            [
                Location(
                    practice_profile_id=mindful_practice.id,
                    name="Main Office",
                    location_type="office",
                    phone="(555) 123-4567",
                    email="mainoffice@mindfulwellness.com",
                    address_line1="123 Therapy Lane",
                    address_line2="Suite 200",
                    city="San Francisco",
                    state="CA",
                    zip_code="94102",
                    country="United States",
                    timezone="America/Los_Angeles",
                    is_primary=True,
                    is_active=True,
                    accepts_appointments=True,
                    wheelchair_accessible=True,
                    parking_available=True,
                    public_transport_accessible=True,
                    operating_hours=(
                        "Monday-Friday: 8:00 AM - 6:00 PM, "
                        "Saturday: 9:00 AM - 3:00 PM"
                    ),
                    description=(
                        "Primary location with full-service therapy rooms "
                        "and group meeting spaces"
                    ),
                    tenant_id="tenant_mindful_001",
                ),
                Location(
                    practice_profile_id=mindful_practice.id,
                    name="Telehealth Services",
                    location_type="telehealth",
                    phone="(555) 123-4567",
                    email="telehealth@mindfulwellness.com",
                    address_line1="Virtual Location",
                    city="San Francisco",
                    state="CA",
                    zip_code="94102",
                    country="United States",
                    timezone="America/Los_Angeles",
                    is_primary=False,
                    is_active=True,
                    accepts_appointments=True,
                    wheelchair_accessible=True,
                    parking_available=False,
                    public_transport_accessible=True,
                    operating_hours="Monday-Sunday: 7:00 AM - 9:00 PM",
                    description=(
                        "Secure video conferencing platform for remote "
                        "therapy sessions"
                    ),
                    tenant_id="tenant_mindful_001",
                ),
            ]
        )

        # Locations for Harbor Counseling Associates
        harbor_practice = practices[1]
        locations.extend(
            [
                Location(
                    practice_profile_id=harbor_practice.id,
                    name="Harbor View Main Campus",
                    location_type="clinic",
                    phone="(555) 987-6543",
                    email="maincamp@harborcounseling.org",
                    address_line1="456 Harbor View Drive",
                    city="Seattle",
                    state="WA",
                    zip_code="98101",
                    country="United States",
                    timezone="America/Los_Angeles",
                    is_primary=True,
                    is_active=True,
                    accepts_appointments=True,
                    wheelchair_accessible=True,
                    parking_available=True,
                    public_transport_accessible=True,
                    operating_hours=(
                        "Monday-Friday: 7:00 AM - 7:00 PM, "
                        "Saturday: 8:00 AM - 4:00 PM"
                    ),
                    special_instructions=(
                        "Enter through main lobby, check in at reception desk"
                    ),
                    description=(
                        "Main campus with individual and group therapy rooms, "
                        "family counseling suites"
                    ),
                    tenant_id="tenant_harbor_002",
                ),
                Location(
                    practice_profile_id=harbor_practice.id,
                    name="Eastside Branch",
                    location_type="office",
                    phone="(555) 987-6546",
                    email="eastside@harborcounseling.org",
                    address_line1="789 Eastside Boulevard",
                    address_line2="Floor 3",
                    city="Bellevue",
                    state="WA",
                    zip_code="98004",
                    country="United States",
                    timezone="America/Los_Angeles",
                    is_primary=False,
                    is_active=True,
                    accepts_appointments=True,
                    wheelchair_accessible=True,
                    parking_available=True,
                    public_transport_accessible=False,
                    operating_hours="Monday, Wednesday, Friday: 9:00 AM - 5:00 PM",
                    special_instructions=("Parking validation available at front desk"),
                    description="Satellite office serving eastside communities",
                    tenant_id="tenant_harbor_002",
                ),
            ]
        )

        # Locations for Serenity Mental Health Group
        serenity_practice = practices[2]
        locations.extend(
            [
                Location(
                    practice_profile_id=serenity_practice.id,
                    name="Serenity Main Center",
                    location_type="clinic",
                    phone="(555) 555-1234",
                    email="main@serenitymh.com",
                    address_line1="789 Peaceful Way",
                    address_line2="Building A",
                    city="Austin",
                    state="TX",
                    zip_code="78701",
                    country="United States",
                    timezone="America/Chicago",
                    is_primary=True,
                    is_active=True,
                    accepts_appointments=True,
                    wheelchair_accessible=True,
                    parking_available=True,
                    public_transport_accessible=True,
                    operating_hours=(
                        "Monday-Thursday: 8:00 AM - 8:00 PM, "
                        "Friday: 8:00 AM - 5:00 PM"
                    ),
                    special_instructions=(
                        "Please arrive 15 minutes early for first appointment"
                    ),
                    description=(
                        "Full-service mental health facility with specialized "
                        "treatment rooms"
                    ),
                    tenant_id="tenant_serenity_003",
                ),
                Location(
                    practice_profile_id=serenity_practice.id,
                    name="North Austin Outreach",
                    location_type="office",
                    phone="(555) 555-1237",
                    email="north@serenitymh.com",
                    address_line1="1010 North Loop Road",
                    address_line2="Suite 150",
                    city="Austin",
                    state="TX",
                    zip_code="78756",
                    country="United States",
                    timezone="America/Chicago",
                    is_primary=False,
                    is_active=True,
                    accepts_appointments=True,
                    wheelchair_accessible=False,
                    parking_available=True,
                    public_transport_accessible=True,
                    operating_hours=(
                        "Tuesday, Thursday: 10:00 AM - 6:00 PM, "
                        "Saturday: 9:00 AM - 1:00 PM"
                    ),
                    description=(
                        "Community outreach location focusing on accessible "
                        "mental health services"
                    ),
                    tenant_id="tenant_serenity_003",
                ),
            ]
        )

        # Add locations to session
        for location in locations:
            session.add(location)

        # Commit all changes
        session.commit()

        print("Successfully seeded database with:")
        print(f"  - {len(practices)} practice profiles")
        print(f"  - {len(locations)} locations")

        # Print summary
        for i, practice in enumerate(practices):
            practice_locations = [
                loc for loc in locations if loc.practice_profile_id == practice.id
            ]
            print(f"\n{practice.name}:")
            print(f"  - Tenant ID: {practice.tenant_id}")
            print(f"  - NPI: {practice.npi_number}")
            print(f"  - Locations: {len(practice_locations)}")
            for loc in practice_locations:
                print(
                    f"    * {loc.name} ({loc.location_type}) - "
                    f"{loc.city}, {loc.state}"
                )

    except Exception as e:
        session.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("Seeding practice profiles and locations data...")
    seed_practice_data()
    print("Seeding completed successfully!")
