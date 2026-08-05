"""Create or refresh a demo admin (focal-person) account for evaluation.

Idempotent: matched by a fixed email, so re-running only ever touches the demo
account and never affects any other user — the real focal-person admin included.
Backend-only; this changes no templates or UI.

Usage:
    python manage.py create_demo_admin
    docker compose -f docker-compose.prod.yml exec web python manage.py create_demo_admin
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User

DEMO_EMAIL = "tester@gmail.com"
DEMO_NAME = "Demo Admin (Tester)"
DEMO_PASSWORD = "tester@123"


class Command(BaseCommand):
    help = "Create or refresh the demo admin account (tester@gmail.com)."

    @transaction.atomic
    def handle(self, *args, **options):
        user, created = User.objects.update_or_create(
            email=DEMO_EMAIL,
            defaults={
                "name": DEMO_NAME,
                "role": User.Role.ADMIN,
                "is_active": True,
                # App-level focal person only. Deliberately NOT is_staff /
                # is_superuser: this is a well-known-credential demo account, so
                # it must not carry a Django-admin (/admin/) backdoor.
                "is_staff": False,
                "is_superuser": False,
            },
        )
        # update_or_create can't hash the password, so set it explicitly. This
        # always resets it, keeping the demo credentials predictable.
        user.set_password(DEMO_PASSWORD)
        user.save(update_fields=["password"])

        verb = "Created" if created else "Refreshed"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} demo admin {DEMO_EMAIL} (role=ADMIN, active, password reset)."
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "This account uses a well-known password and grants full focal-person "
                "access. Remove it after evaluation (Faculty screen or Django admin) "
                "and never leave it on a real production deployment."
            )
        )
