#!/usr/bin/env python3
"""Script to seed RBAC roles and create test users."""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))

from database import get_db
from models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def get_permissions_for_roles(roles):
    """Get permissions based on roles."""
    role_permissions = {
        "admin": ["read", "write", "delete", "manage_users", "manage_billing"],
        "clinician": ["read", "write", "manage_patients", "manage_appointments"],
        "biller": ["read", "write", "manage_billing", "view_financial_reports"],
        "front_desk": ["read", "write", "manage_appointments", "manage_patients"]
    }
    
    permissions = set()
    for role in roles:
        permissions.update(role_permissions.get(role, []))
    return list(permissions)


async def seed_rbac_roles():
    """Create users with different RBAC roles for testing."""
    
    # Get database session
    async for db in get_db():
        try:
            # Define test users with their roles
            test_users = [
                {
                    "email": "admin@pms.com",
                    "name": "System Administrator",
                    "roles": ["admin"]
                },
                {
                    "email": "clinician@pms.com",
                    "name": "Dr. Jane Smith",
                    "roles": ["clinician"]
                },
                {
                    "email": "biller@pms.com",
                    "name": "John Billing",
                    "roles": ["biller"]
                },
                {
                    "email": "frontdesk@pms.com",
                    "name": "Sarah Reception",
                    "roles": ["front_desk"]
                }
            ]
            
            print("Starting RBAC role seeding...")
            
            for user_data in test_users:
                # Check if user already exists
                result = await db.execute(
                    select(User).where(User.email == user_data["email"])
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    # Update existing user's roles
                    existing_user.roles = user_data["roles"]
                    perms = get_permissions_for_roles(user_data["roles"])
                    existing_user.permissions = perms
                    roles_str = ', '.join(user_data['roles'])
                    print(f"Updated user {user_data['email']} "
                          f"with roles: {roles_str}")
                else:
                    # Create new user
                    perms = get_permissions_for_roles(user_data["roles"])
                    new_user = User(
                        email=user_data["email"],
                        name=user_data["name"],
                        roles=user_data["roles"],
                        permissions=perms,
                        is_active=True
                    )
                    db.add(new_user)
                    roles_str = ', '.join(user_data['roles'])
                    print(f"Created user {user_data['email']} "
                          f"with roles: {roles_str}")
            
            # Commit all changes
            await db.commit()
            
            print("\nRBAC role seeding completed successfully!")
            print("\nCreated/Updated users:")
            for user_data in test_users:
                roles_str = ", ".join(user_data["roles"])
                permissions = get_permissions_for_roles(user_data["roles"])
                permissions_str = ", ".join(permissions)
                email = user_data['email']
                name = user_data['name']
                print(f"  - {email} ({name}):")
                print(f"    Roles: {roles_str}")
                print(f"    Permissions: {permissions_str}\n")
                
        except Exception as e:
            await db.rollback()
            print(f"Error seeding RBAC roles: {e}")
            raise
        finally:
            await db.close()
        break  # Exit the async generator loop


if __name__ == "__main__":
    print("Seeding RBAC roles...")
    asyncio.run(seed_rbac_roles())