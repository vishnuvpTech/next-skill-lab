"""
Create the initial Django superuser if one does not already exist.

Configure these environment variables in Docker/runtime:
    DJANGO_SUPERUSER_USERNAME
    DJANGO_SUPERUSER_PASSWORD

For custom user models, also provide each field listed in the model's
REQUIRED_FIELDS using DJANGO_SUPERUSER_<FIELD_NAME>, for example:
    DJANGO_SUPERUSER_EMAIL=admin@example.com
"""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "talentlens.settings")

import django

django.setup()

from django.contrib.auth import get_user_model


def main():
    User = get_user_model()
    username_field = User.USERNAME_FIELD

    username = os.getenv("DJANGO_SUPERUSER_USERNAME")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

    if not username or not password:
        print(
            "Superuser creation skipped: set DJANGO_SUPERUSER_USERNAME "
            "and DJANGO_SUPERUSER_PASSWORD."
        )
        return

    lookup_value = {username_field: username}

    try:
        user = User._default_manager.get(**lookup_value)
    except User.DoesNotExist:
        user = None

    if user:
        print(f"Superuser already exists for {username_field}={username!r}.")
        return

    user_data = {username_field: username}

    for field_name in User.REQUIRED_FIELDS:
        env_name = f"DJANGO_SUPERUSER_{field_name.upper()}"
        value = os.getenv(env_name)
        if value is None:
            print(
                f"Superuser creation failed: missing required environment "
                f"variable {env_name}.",
                file=sys.stderr,
            )
            sys.exit(1)
        user_data[field_name] = value

    User._default_manager.create_superuser(
        password=password,
        **user_data,
    )
    print(f"Superuser created successfully for {username_field}={username!r}.")


if __name__ == "__main__":
    main()
