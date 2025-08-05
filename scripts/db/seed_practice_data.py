#!/usr/bin/env python3
"""Seed script for practice profiles and locations data."""

import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../apps/backend'))

# Import after path modification
from database import AsyncSessionLocal, create_tables  # noqa: E402
from models.practice_profile import PracticeProfile  # noqa: E402
from models.location import Location  # noqa: E402


async def create_practice_seed_data():
    """Create seed data for practice profiles and locations."""
    
    # Create tables first
    await create_tables()
    
    async with AsyncSessionLocal() as session:
        try:
            # Create sample practice profiles
            practice1 = PracticeProfile(
                name="Mindful Health Practice",
                legal_name="Mindful Health Practice LLC",
                tax_id="12-3456789",
                npi_number="1234567890",
                email="admin@mindfulhealth.local",
                phone="555-0100",
                fax="555-0101",
                website="https://mindfulhealth.local",
                address_line1="123 Wellness Boulevard",
                address_line2="Suite 200",
                city="San Francisco",
                state="CA",
                zip_code="94102",
                country="United States",
                timezone="America/Los_Angeles",
                default_appointment_duration="50",
                accepts_new_patients=True,
                is_active=True,
                billing_provider_name="Mindful Health Billing",
                billing_contact_email="billing@mindfulhealth.local",
                billing_contact_phone="555-0102",
                description="A comprehensive mental health practice "
                           "specializing in anxiety, depression, and trauma.",
                tenant_id="tenant_mindful_health"
            )
            
            practice2 = PracticeProfile(
                name="Bay Area Therapy Center",
                legal_name="Bay Area Therapy Center Inc",
                tax_id="98-7654321",
                npi_number="0987654321",
                email="contact@baytherapy.local",
                phone="555-0200",
                fax="555-0201",
                website="https://baytherapy.local",
                address_line1="456 Therapy Lane",
                city="Oakland",
                state="CA",
                zip_code="94607",
                country="United States",
                timezone="America/Los_Angeles",
                default_appointment_duration="45",
                accepts_new_patients=True,
                is_active=True,
                billing_provider_name="Bay Area Billing Services",
                billing_contact_email="billing@baytherapy.local",
                billing_contact_phone="555-0202",
                description="Community-focused therapy center offering "
                           "individual and group therapy services.",
                tenant_id="tenant_bay_area_therapy"
            )
            
            session.add_all([practice1, practice2])
            await session.commit()
            
            # Create locations for practice1
            location1_main = Location(
                practice_profile_id=practice1.id,
                name="Main Office",
                location_type="office",
                phone="555-0100",
                fax="555-0101",
                email="main@mindfulhealth.local",
                address_line1="123 Wellness Boulevard",
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
                operating_hours="Monday-Friday: 8:00 AM - 6:00 PM",
                description="Main office location with full services",
                tenant_id="tenant_mindful_health"
            )
            
            location1_satellite = Location(
                practice_profile_id=practice1.id,
                name="Downtown Satellite Office",
                location_type="office",
                phone="555-0103",
                email="downtown@mindfulhealth.local",
                address_line1="789 Market Street",
                address_line2="Floor 5",
                city="San Francisco",
                state="CA",
                zip_code="94103",
                country="United States",
                timezone="America/Los_Angeles",
                is_primary=False,
                is_active=True,
                accepts_appointments=True,
                wheelchair_accessible=True,
                parking_available=False,
                public_transport_accessible=True,
                operating_hours="Monday, Wednesday, Friday: 9:00 AM - 5:00 PM",
                description="Convenient downtown location",
                tenant_id="tenant_mindful_health"
            )
            
            # Create locations for practice2
            location2_main = Location(
                practice_profile_id=practice2.id,
                name="Oakland Main Center",
                location_type="clinic",
                phone="555-0200",
                fax="555-0201",
                email="oakland@baytherapy.local",
                address_line1="456 Therapy Lane",
                city="Oakland",
                state="CA",
                zip_code="94607",
                country="United States",
                timezone="America/Los_Angeles",
                is_primary=True,
                is_active=True,
                accepts_appointments=True,
                wheelchair_accessible=True,
                parking_available=True,
                public_transport_accessible=False,
                operating_hours="Monday-Saturday: 7:00 AM - 8:00 PM",
                special_instructions="Please use the side entrance after 6 PM",
                description="Full-service therapy center",
                tenant_id="tenant_bay_area_therapy"
            )
            
            location2_telehealth = Location(
                practice_profile_id=practice2.id,
                name="Telehealth Services",
                location_type="telehealth",
                phone="555-0203",
                email="telehealth@baytherapy.local",
                address_line1="Virtual Location",
                city="Oakland",
                state="CA",
                zip_code="94607",
                country="United States",
                timezone="America/Los_Angeles",
                is_primary=False,
                is_active=True,
                accepts_appointments=True,
                wheelchair_accessible=True,
                parking_available=True,
                public_transport_accessible=True,
                operating_hours="Monday-Sunday: 6:00 AM - 10:00 PM",
                special_instructions="Secure video platform access provided",
                description="Remote therapy services via secure video",
                tenant_id="tenant_bay_area_therapy"
            )
            
            session.add_all([
                location1_main, location1_satellite,
                location2_main, location2_telehealth
            ])
            await session.commit()
            
            print("✅ Practice seed data created successfully!")
            print(f"Created {len([practice1, practice2])} practice profiles")
            locations_count = len([
                location1_main, location1_satellite,
                location2_main, location2_telehealth
            ])
            print(f"Created {locations_count} locations")
            
            # Display created data
            print("\n📋 Practice Profiles:")
            for practice in [practice1, practice2]:
                print(
                    f"  • {practice.display_name} "
                    f"({practice.city}, {practice.state})"
                )
                print(f"    Tenant: {practice.tenant_id}")
                print(f"    Email: {practice.email}")
                print(f"    Phone: {practice.phone}")
                print()
            
            print("📍 Locations:")
            for location in [
                location1_main, location1_satellite,
                location2_main, location2_telehealth
            ]:
                print(
                    f"  • {location.display_name} "
                    f"({location.location_type})"
                )
                print(f"    Address: {location.short_address}")
                print(f"    Primary: {location.is_primary}")
                print(f"    Active: {location.is_active}")
                print()
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating practice seed data: {e}")
            raise


if __name__ == "__main__":
    print("🏥 Creating practice profiles and locations seed data...")
    asyncio.run(create_practice_seed_data())