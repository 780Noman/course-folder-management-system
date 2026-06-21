"""Tests for the custom User model and manager."""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_create_user_defaults_to_faculty_with_unusable_password():
    user = User.objects.create_user(email="fac@uiit.edu.pk", name="Dr Faculty")
    assert user.role == User.Role.FACULTY
    assert user.is_faculty and not user.is_admin
    assert user.is_staff is False
    assert user.has_usable_password() is False  # invited users set it later


@pytest.mark.django_db
def test_create_user_with_password_is_usable():
    user = User.objects.create_user(
        email="p@uiit.edu.pk", name="P", password="StrongPass123"
    )
    assert user.has_usable_password()
    assert user.check_password("StrongPass123")


@pytest.mark.django_db
def test_create_superuser_is_admin():
    admin = User.objects.create_superuser(
        email="admin@uiit.edu.pk", name="Focal", password="StrongPass123"
    )
    assert admin.role == User.Role.ADMIN
    assert admin.is_admin
    assert admin.is_staff and admin.is_superuser


@pytest.mark.django_db
def test_email_is_normalised_and_required():
    user = User.objects.create_user(email="Mixed@UIIT.edu.pk", name="X")
    assert user.email == "Mixed@uiit.edu.pk"  # domain lowercased
    with pytest.raises(ValueError):
        User.objects.create_user(email="", name="No Email")
    with pytest.raises(ValueError):
        User.objects.create_user(email="noname@uiit.edu.pk", name="")
