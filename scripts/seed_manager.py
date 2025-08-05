#!/usr/bin/env python3
"""Centralized seed data management for HIPAA-compliant test data.

This script provides a unified interface for generating, managing, and
cleaning seed data across all core domain models while ensuring HIPAA
compliance and data consistency.

Usage:
    python seed_manager.py --help
    python seed_manager.py generate --count 10
    python seed_manager.py clean --confirm
    python seed_manager.py reset --environment test
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))

from database import SessionLocal
from models import (
    PracticeProfile, Location, Client, Provider,
    Appointment, Note, LedgerEntry, AuthToken,
    EncryptionKey, FHIRMapping
)

# Import all factories
from factories import (
    PracticeProfileFactory, LocationFactory, ClientFactory,
    ProviderFactory, AppointmentFactory, NoteFactory,
    LedgerEntryFactory, AuthTokenFactory,
    EncryptionKeyFactory, FHIRMappingFactory,
    PatientMappingFactory, PractitionerMappingFactory,
    AppointmentMappingFactory
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SeedManager:
    """Centralized seed data management system."""
    
    def __init__(self, session=None):
        """Initialize the seed manager."""
        self.session = session or SessionLocal()
        self.factories = {
            'practice_profiles': PracticeProfileFactory,
            'locations': LocationFactory,
            'clients': ClientFactory,
            'providers': ProviderFactory,
            'appointments': AppointmentFactory,
            'notes': NoteFactory,
            'ledger_entries': LedgerEntryFactory,
            'auth_tokens': AuthTokenFactory,
            'encryption_keys': EncryptionKeyFactory,
            'fhir_mappings': FHIRMappingFactory
        }
        self.models = {
            'practice_profiles': PracticeProfile,
            'locations': Location,
            'clients': Client,
            'providers': Provider,
            'appointments': Appointment,
            'notes': Note,
            'ledger_entries': LedgerEntry,
            'auth_tokens': AuthToken,
            'encryption_keys': EncryptionKey,
            'fhir_mappings': FHIRMapping
        }
    
    def generate_seed_data(
        self,
        counts: Optional[Dict[str, int]] = None,
        tenant_ids: Optional[List[str]] = None
    ) -> Dict[str, List]:
        """Generate seed data for all models.
        
        Args:
            counts: Dictionary specifying count for each model type
            tenant_ids: List of tenant IDs for multi-tenant data
            
        Returns:
            Dictionary containing generated objects by model type
        """
        if counts is None:
            counts = {
                'practice_profiles': 3,
                'locations': 6,
                'clients': 25,
                'providers': 8,
                'appointments': 50,
                'notes': 75,
                'ledger_entries': 100,
                'auth_tokens': 15,
                'encryption_keys': 10,
                'fhir_mappings': 80
            }
        
        if tenant_ids is None:
            tenant_ids = ['tenant_001', 'tenant_002', 'tenant_003']
        
        # Configure all factories with the session
        for factory_class in self.factories.values():
            factory_class._meta.sqlalchemy_session = self.session
        
        # Configure FHIR mapping factories with the session
        PatientMappingFactory._meta.sqlalchemy_session = self.session
        PractitionerMappingFactory._meta.sqlalchemy_session = self.session
        AppointmentMappingFactory._meta.sqlalchemy_session = self.session
        
        generated_data = {}
        
        try:
            # Generate practice profiles first (foundational)
            logger.info("Generating practice profiles...")
            practice_profiles = []
            for i, tenant_id in enumerate(tenant_ids):
                profile = PracticeProfileFactory.create(
                    tenant_id=tenant_id
                )
                practice_profiles.append(profile)
                logger.info(f"Created practice profile: {profile.name}")
            
            generated_data['practice_profiles'] = practice_profiles
            
            # Generate locations for each practice
            logger.info("Generating locations...")
            locations = []
            for profile in practice_profiles:
                for _ in range(counts['locations'] // len(practice_profiles)):
                    location = LocationFactory.create(
                        practice_profile=profile,
                        tenant_id=profile.tenant_id
                    )
                    locations.append(location)
            
            generated_data['locations'] = locations
            
            # Generate clients
            logger.info("Generating clients...")
            clients = []
            for i in range(counts['clients']):
                tenant_id = tenant_ids[i % len(tenant_ids)]
                client = ClientFactory.create(
                    tenant_id=tenant_id
                )
                clients.append(client)
            
            generated_data['clients'] = clients
            
            # Generate providers
            logger.info("Generating providers...")
            providers = []
            for i in range(counts['providers']):
                tenant_id = tenant_ids[i % len(tenant_ids)]
                provider = ProviderFactory.create(
                    tenant_id=tenant_id
                )
                providers.append(provider)
            
            generated_data['providers'] = providers
            
            # Generate appointments
            logger.info("Generating appointments...")
            appointments = []
            for i in range(counts['appointments']):
                client = clients[i % len(clients)]
                provider = providers[i % len(providers)]
                
                # Ensure client and provider are from same tenant
                if client.tenant_id != provider.tenant_id:
                    provider = next(
                        (
                            p for p in providers
                            if p.tenant_id == client.tenant_id
                        ),
                        providers[0]
                    )
                
                appointment = AppointmentFactory.create(
                    client=client,
                    provider=provider,
                    tenant_id=client.tenant_id
                )
                appointments.append(appointment)
            
            generated_data['appointments'] = appointments
            
            # Generate notes
            logger.info("Generating notes...")
            notes = []
            for i in range(counts['notes']):
                appointment = appointments[i % len(appointments)]
                note = NoteFactory.create(
                    client=appointment.client,
                    provider=appointment.provider,
                    appointment=appointment,
                    tenant_id=appointment.tenant_id
                )
                notes.append(note)
            
            generated_data['notes'] = notes
            
            # Generate ledger entries
            logger.info("Generating ledger entries...")
            ledger_entries = []
            for i in range(counts['ledger_entries']):
                client = clients[i % len(clients)]
                ledger_entry = LedgerEntryFactory.create(
                    client=client,
                    tenant_id=client.tenant_id
                )
                ledger_entries.append(ledger_entry)
            
            generated_data['ledger_entries'] = ledger_entries
            
            # Generate auth tokens
            logger.info("Generating auth tokens...")
            auth_tokens = []
            for i in range(counts['auth_tokens']):
                tenant_id = tenant_ids[i % len(tenant_ids)]
                auth_token = AuthTokenFactory.create(
                    tenant_id=tenant_id
                )
                auth_tokens.append(auth_token)
            
            generated_data['auth_tokens'] = auth_tokens
            
            # Generate encryption keys
            logger.info("Generating encryption keys...")
            encryption_keys = []
            for i in range(counts['encryption_keys']):
                tenant_id = tenant_ids[i % len(tenant_ids)]
                encryption_key = EncryptionKeyFactory.create(
                    tenant_id=tenant_id
                )
                encryption_keys.append(encryption_key)
            
            generated_data['encryption_keys'] = encryption_keys
            
            # Generate FHIR mappings
            logger.info("Generating FHIR mappings...")
            fhir_mappings = []
            
            # Create mappings for clients (Patient resources)
            client_count = min(len(clients), counts['fhir_mappings'] // 3)
            for client in clients[:client_count]:
                mapping = PatientMappingFactory.create(
                    internal_id=client.id,
                    tenant_id=client.tenant_id
                )
                fhir_mappings.append(mapping)
            
            # Create mappings for providers (Practitioner resources)
            provider_count = min(len(providers), counts['fhir_mappings'] // 3)
            for provider in providers[:provider_count]:
                mapping = PractitionerMappingFactory.create(
                    internal_id=provider.id,
                    tenant_id=provider.tenant_id
                )
                fhir_mappings.append(mapping)
            
            # Create mappings for appointments
            appointment_count = min(
                len(appointments), counts['fhir_mappings'] // 3
            )
            for appointment in appointments[:appointment_count]:
                mapping = AppointmentMappingFactory.create(
                    internal_id=appointment.id,
                    tenant_id=appointment.tenant_id
                )
                fhir_mappings.append(mapping)
            
            generated_data['fhir_mappings'] = fhir_mappings
            
            # Commit all changes
            self.session.commit()
            logger.info("Successfully generated all seed data")
            
            # Log summary
            for model_type, objects in generated_data.items():
                logger.info(f"Generated {len(objects)} {model_type}")
            
            return generated_data
            
        except Exception as e:
            logger.error(f"Error generating seed data: {e}")
            self.session.rollback()
            raise
    
    def clean_seed_data(self, confirm: bool = False) -> None:
        """Clean all seed data from the database.
        
        Args:
            confirm: If True, proceed with deletion without prompt
        """
        if not confirm:
            response = input(
                "This will delete ALL data from the database. "
                "Are you sure? (yes/no): "
            )
            if response.lower() != 'yes':
                logger.info("Operation cancelled")
                return
        
        try:
            # Delete in reverse dependency order
            delete_order = [
                'fhir_mappings', 'ledger_entries', 'notes', 'appointments',
                'providers', 'clients', 'locations', 'practice_profiles',
                'auth_tokens', 'encryption_keys'
            ]
            
            for model_type in delete_order:
                model_class = self.models[model_type]
                count = self.session.query(model_class).count()
                if count > 0:
                    self.session.query(model_class).delete()
                    logger.info(f"Deleted {count} {model_type}")
            
            self.session.commit()
            logger.info("Successfully cleaned all seed data")
            
        except Exception as e:
            logger.error(f"Error cleaning seed data: {e}")
            self.session.rollback()
            raise
    
    def reset_database(self, environment: str = "development") -> None:
        """Reset database with fresh seed data.
        
        Args:
            environment: Target environment (development, test, staging)
        """
        if environment == "production":
            raise ValueError("Cannot reset production database")
        
        logger.info(f"Resetting {environment} database...")
        
        # Clean existing data
        self.clean_seed_data(confirm=True)
        
        # Generate new seed data
        counts = {
            "development": {
                'practice_profiles': 3,
                'locations': 6,
                'clients': 25,
                'providers': 8,
                'appointments': 50,
                'notes': 75,
                'ledger_entries': 100,
                'auth_tokens': 15,
                'encryption_keys': 10,
                'fhir_mappings': 80
            },
            "test": {
                'practice_profiles': 2,
                'locations': 4,
                'clients': 10,
                'providers': 4,
                'appointments': 20,
                'notes': 30,
                'ledger_entries': 40,
                'auth_tokens': 8,
                'encryption_keys': 5,
                'fhir_mappings': 30
            },
            "staging": {
                'practice_profiles': 5,
                'locations': 10,
                'clients': 50,
                'providers': 15,
                'appointments': 100,
                'notes': 150,
                'ledger_entries': 200,
                'auth_tokens': 25,
                'encryption_keys': 15,
                'fhir_mappings': 150
            }
        }
        
        self.generate_seed_data(counts=counts.get(environment))
        logger.info(f"Successfully reset {environment} database")
    
    def validate_data_integrity(self) -> Dict[str, bool]:
        """Validate data integrity and relationships.
        
        Returns:
            Dictionary of validation results by check type
        """
        results = {}
        
        try:
            # Check tenant isolation
            logger.info("Validating tenant isolation...")
            tenant_violations = []
            
            # Check appointments have matching client/provider tenants
            appointments = self.session.query(Appointment).all()
            for apt in appointments:
                if (apt.client.tenant_id != apt.provider.tenant_id or
                        apt.tenant_id != apt.client.tenant_id):
                    tenant_violations.append(f"Appointment {apt.id}")
            
            results['tenant_isolation'] = len(tenant_violations) == 0
            if tenant_violations:
                logger.warning(
                    f"Tenant violations found: {tenant_violations[:5]}"
                )
            
            # Check required relationships
            logger.info("Validating relationships...")
            
            # Check notes have valid appointments
            notes_without_appointments = self.session.query(Note).filter(
                Note.appointment_id.is_(None)
            ).count()
            
            results['relationships'] = notes_without_appointments == 0
            
            # Check HIPAA compliance markers
            logger.info("Validating HIPAA compliance...")
            
            # Check for potentially real data patterns
            suspicious_emails = self.session.query(Client).filter(
                ~Client.email.like('%.local')
            ).count()
            
            results['hipaa_compliance'] = suspicious_emails == 0
            
            logger.info(f"Validation results: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error during validation: {e}")
            return {'error': False}
    
    def close(self):
        """Close the database session."""
        if self.session:
            self.session.close()


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="HIPAA-compliant seed data management"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate command
    generate_parser = subparsers.add_parser(
        'generate', help='Generate seed data'
    )
    generate_parser.add_argument(
        '--count', type=int, default=10,
        help='Base count for generated records'
    )
    generate_parser.add_argument(
        '--tenants', nargs='+', default=['tenant_001', 'tenant_002'],
        help='Tenant IDs to generate data for'
    )
    
    # Clean command
    clean_parser = subparsers.add_parser(
        'clean', help='Clean all seed data'
    )
    clean_parser.add_argument(
        '--confirm', action='store_true',
        help='Skip confirmation prompt'
    )
    
    # Reset command
    reset_parser = subparsers.add_parser(
        'reset', help='Reset database with fresh data'
    )
    reset_parser.add_argument(
        '--environment', choices=['development', 'test', 'staging'],
        default='development', help='Target environment'
    )
    
    # Validate command
    subparsers.add_parser(
        'validate', help='Validate data integrity'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize seed manager
    seed_manager = SeedManager()
    
    try:
        if args.command == 'generate':
            base_count = args.count
            counts = {
                'practice_profiles': max(1, base_count // 10),
                'locations': max(2, base_count // 5),
                'clients': base_count,
                'providers': max(2, base_count // 3),
                'appointments': base_count * 2,
                'notes': base_count * 3,
                'ledger_entries': base_count * 4,
                'auth_tokens': max(5, base_count // 2),
                'encryption_keys': max(3, base_count // 3),
                'fhir_mappings': base_count * 3
            }
            seed_manager.generate_seed_data(
                counts=counts,
                tenant_ids=args.tenants
            )
            
        elif args.command == 'clean':
            seed_manager.clean_seed_data(confirm=args.confirm)
            
        elif args.command == 'reset':
            seed_manager.reset_database(environment=args.environment)
            
        elif args.command == 'validate':
            results = seed_manager.validate_data_integrity()
            for check, passed in results.items():
                status = "PASS" if passed else "FAIL"
                print(f"{check}: {status}")
            
            if not all(results.values()):
                sys.exit(1)
    
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)
    
    finally:
        seed_manager.close()


if __name__ == '__main__':
    main()