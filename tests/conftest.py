"""Shared pytest fixtures."""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

PASSWORD = "StrongPass123!"


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="admin@uiit.edu.pk", name="Focal Person", password=PASSWORD
    )


@pytest.fixture
def faculty_user(db):
    return User.objects.create_user(
        email="faculty@uiit.edu.pk", name="Dr Faculty", password=PASSWORD
    )


@pytest.fixture
def admin_client(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture
def faculty_client(client, faculty_user):
    client.force_login(faculty_user)
    return client
