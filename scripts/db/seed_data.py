#!/usr/bin/env python3
"""Seed script for local development data."""

import asyncio
import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../apps/backend'))

from database import AsyncSessionLocal, create_tables
from models.client import Client
from models.provider import Provider
from models.appointment import Appointment, AppointmentStatus, AppointmentType
from models.note import Note, NoteType
from models.ledger import LedgerEntry, TransactionType, PaymentMethod


async def create_seed_data():
    """Create seed data for local development."""
    
    # Create tables first
    await create_tables()
    
    async with AsyncSessionLocal() as session:
        try:
            # Create providers
            provider1 = Provider(
                first_name="Dr. Sarah",
                last_name="Johnson",
                title="Dr.",
                credentials="MD, Psychiatrist",
                specialty="Adult Psychiatry",
                email="sarah.johnson@pms.local",
                phone="555-0101",
                license_number="MD12345",
                license_state="CA",
                npi_number="1234567890",
                office_address_line1="123 Medical Plaza",
                office_city="San Francisco",
                office_state="CA",
                office_zip_code="94102",
                bio="Experienced psychiatrist specializing in anxiety and depression."
            )
            
            provider2 = Provider(
                first_name="Lisa",
                last_name="Chen",
                credentials="LCSW",
                specialty="Clinical Social Work",
                email="lisa.chen@pms.local",
                phone="555-0102",
                license_number="LCSW67890",
                license_state="CA",
                office_address_line1="456 Therapy Center",
                office_city="San Francisco",
                office_state="CA",
                office_zip_code="94103",
                bio="Licensed clinical social worker with expertise in trauma therapy."
            )
            
            session.add_all([provider1, provider2])
            await session.commit()
            
            # Create clients (anonymized data)
            client1 = Client(
                first_name="John",
                last_name="Smith",
                email="john.smith@example.com",
                phone="555-1001",
                date_of_birth=date(1985, 3, 15),
                gender="Male",
                address_line1="789 Main St",
                city="San Francisco",
                state="CA",
                zip_code="94104",
                insurance_provider="Blue Cross",
                insurance_id="BC123456789",
                preferred_language="English",
                primary_diagnosis="Generalized Anxiety Disorder"
            )
            
            client2 = Client(
                first_name="Jane",
                last_name="Doe",
                email="jane.doe@example.com",
                phone="555-1002",
                date_of_birth=date(1990, 7, 22),
                gender="Female",
                address_line1="321 Oak Ave",
                city="San Francisco",
                state="CA",
                zip_code="94105",
                insurance_provider="Aetna",
                insurance_id="AET987654321",
                preferred_language="English",
                primary_diagnosis="Major Depressive Disorder"
            )
            
            session.add_all([client1, client2])
            await session.commit()
            
            # Create appointments
            tomorrow = datetime.now() + timedelta(days=1)
            appointment1 = Appointment(
                client_id=client1.id,
                provider_id=provider1.id,
                scheduled_start=tomorrow.replace(hour=10, minute=0, second=0, microsecond=0),
                scheduled_end=tomorrow.replace(hour=10, minute=50, second=0, microsecond=0),
                appointment_type=AppointmentType.INITIAL_CONSULTATION,
                status=AppointmentStatus.SCHEDULED,
                duration_minutes=50,
                reason_for_visit="Initial psychiatric evaluation",
                copay_amount="25.00"
            )
            
            next_week = datetime.now() + timedelta(days=7)
            appointment2 = Appointment(
                client_id=client2.id,
                provider_id=provider2.id,
                scheduled_start=next_week.replace(hour=14, minute=0, second=0, microsecond=0),
                scheduled_end=next_week.replace(hour=14, minute=50, second=0, microsecond=0),
                appointment_type=AppointmentType.THERAPY_SESSION,
                status=AppointmentStatus.CONFIRMED,
                duration_minutes=50,
                reason_for_visit="Weekly therapy session",
                copay_amount="30.00"
            )
            
            session.add_all([appointment1, appointment2])
            await session.commit()
            
            # Create sample notes
            note1 = Note(
                client_id=client1.id,
                provider_id=provider1.id,
                note_type=NoteType.INTAKE_NOTE,
                title="Initial Assessment",
                content="Patient presents with symptoms of generalized anxiety. "
                       "Reports difficulty sleeping and concentration issues. "
                       "No current medications. Discussed treatment options.",
                diagnosis_codes="F41.1",
                treatment_goals="Reduce anxiety symptoms, improve sleep quality",
                interventions="Cognitive behavioral therapy, relaxation techniques",
                plan="Weekly therapy sessions, consider medication evaluation"
            )
            
            session.add(note1)
            await session.commit()
            
            # Create ledger entries
            charge1 = LedgerEntry(
                client_id=client1.id,
                transaction_type=TransactionType.CHARGE,
                amount=Decimal('150.00'),
                description="Initial psychiatric consultation",
                service_date=date.today(),
                billing_code="90791",
                diagnosis_code="F41.1"
            )
            
            payment1 = LedgerEntry(
                client_id=client1.id,
                transaction_type=TransactionType.COPAY,
                amount=Decimal('25.00'),
                description="Copay for initial consultation",
                service_date=date.today(),
                payment_method=PaymentMethod.CREDIT_CARD,
                reference_number="CC123456"
            )
            
            session.add_all([charge1, payment1])
            await session.commit()
            
            print("✅ Seed data created successfully!")
            print(f"Created {len([provider1, provider2])} providers")
            print(f"Created {len([client1, client2])} clients")
            print(f"Created {len([appointment1, appointment2])} appointments")
            print(f"Created 1 note")
            print(f"Created {len([charge1, payment1])} ledger entries")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating seed data: {e}")
            raise


if __name__ == "__main__":
    print("🌱 Creating seed data for local development...")
    asyncio.run(create_seed_data())