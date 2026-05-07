#!/usr/bin/env python
"""Script to create a superadmin user for TalentLens."""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'talentlens.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from interviews.models import AdminUser


def main():
    print("Create TalentLens Admin User")
    print("=" * 30)

    email = input("Email: ").strip()
    if not email:
        print("Error: email is required.")
        sys.exit(1)

    if AdminUser.objects.filter(email=email).exists():
        print(f"Error: user with email '{email}' already exists.")
        sys.exit(1)

    name = input("Name: ").strip()
    if not name:
        print("Error: name is required.")
        sys.exit(1)

    import getpass
    password = getpass.getpass("Password: ")
    if not password:
        print("Error: password is required.")
        sys.exit(1)

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Error: passwords do not match.")
        sys.exit(1)

    print("\nRole options: superadmin, interviewer, viewer")
    role = input("Role [superadmin]: ").strip() or "superadmin"
    valid_roles = {"superadmin", "interviewer", "viewer"}
    if role not in valid_roles:
        print(f"Error: role must be one of {', '.join(valid_roles)}.")
        sys.exit(1)

    user = AdminUser.objects.create_user(
        email=email,
        password=password,
        name=name,
        role=role,
        is_staff=(role == "superadmin"),
        is_superuser=(role == "superadmin"),
    )
    print(f"\nUser '{user.name}' ({user.email}) created with role '{user.role}'.")


if __name__ == "__main__":
    main()
