#!/usr/bin/env python
"""Seed script: creates the Python department and its topics."""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'talentlens.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from interviews.models import AdminUser, Department, Topic

TOPICS = [
    "Python",
    "FastAPI",
    "Django",
    "Flask",
    "Git",
    "AWS",
    "Docker",
    "Kubernetes",
    "SQL",
    "NoSQL",
]


def main():
    # Resolve the admin user who owns these records
    admin = AdminUser.objects.filter(role="superadmin").first()
    if not admin:
        print("Error: no superadmin user found. Run create_admin.py first.")
        sys.exit(1)

    department, created = Department.objects.get_or_create(
        name="Python",
        defaults={
            "description": "Python and its ecosystem — frameworks, tools, and cloud technologies.",
            "created_by": admin,
        },
    )
    status = "Created" if created else "Already exists"
    print(f"{status}: department '{department.name}'")

    for topic_name in TOPICS:
        topic, created = Topic.objects.get_or_create(
            name=topic_name,
            department=department,
            defaults={"created_by": admin},
        )
        status = "Created" if created else "Already exists"
        print(f"  {status}: topic '{topic.name}'")

    print("\nDone.")


if __name__ == "__main__":
    main()
