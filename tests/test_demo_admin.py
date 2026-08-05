"""The create_demo_admin management command (TASK 1)."""

import pytest
from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command

from accounts.management.commands.create_demo_admin import (
    DEMO_EMAIL,
    DEMO_PASSWORD,
)

User = get_user_model()


@pytest.mark.django_db
def test_creates_active_admin_that_can_log_in():
    call_command("create_demo_admin")
    user = User.objects.get(email=DEMO_EMAIL)
    assert user.is_admin
    assert user.is_active
    # Password is usable and authenticates.
    assert authenticate(username=DEMO_EMAIL, password=DEMO_PASSWORD) == user


@pytest.mark.django_db
def test_is_idempotent_and_resets_password():
    call_command("create_demo_admin")
    first = User.objects.get(email=DEMO_EMAIL)
    # A drifted password/flag is repaired on re-run without creating a duplicate.
    first.set_password("something-else")
    first.is_active = False
    first.save()

    call_command("create_demo_admin")
    assert User.objects.filter(email=DEMO_EMAIL).count() == 1
    refreshed = User.objects.get(email=DEMO_EMAIL)
    assert refreshed.pk == first.pk
    assert refreshed.is_active
    assert authenticate(username=DEMO_EMAIL, password=DEMO_PASSWORD) == refreshed


@pytest.mark.django_db
def test_never_touches_other_users(admin_user, faculty_user):
    admin_pw_hash = admin_user.password
    faculty_pw_hash = faculty_user.password

    call_command("create_demo_admin")

    admin_user.refresh_from_db()
    faculty_user.refresh_from_db()
    # The real admin and faculty are left exactly as they were.
    assert admin_user.password == admin_pw_hash
    assert faculty_user.password == faculty_pw_hash
    assert admin_user.email != DEMO_EMAIL
