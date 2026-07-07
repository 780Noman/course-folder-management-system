"""Admin creates users with an initial password (offline deployment: no email).

The admin sets a starting password and shares it with the user, who can change
it from their account afterwards. Admins can also reset a user's password. The
raw password is validated against the password policy but never emailed.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from audit.models import AuditLog

User = get_user_model()


def test_invite_page_is_admin_only(faculty_client):
    assert faculty_client.get(reverse("invite_user")).status_code == 403


def test_admin_creates_user_with_password(admin_client):
    resp = admin_client.post(
        reverse("invite_user"),
        {
            "name": "New Teacher",
            "email": "new@uiit.edu.pk",
            "role": "FACULTY",
            "password": "StartPass123!",
        },
        follow=True,
    )
    assert resp.status_code == 200

    user = User.objects.get(email="new@uiit.edu.pk")
    assert user.role == User.Role.FACULTY
    # The account is immediately usable with the password the admin set.
    assert user.has_usable_password()
    assert user.check_password("StartPass123!")
    assert AuditLog.objects.filter(action="user_invite").exists()


def test_created_user_can_log_in(admin_client, client):
    admin_client.post(
        reverse("invite_user"),
        {
            "name": "New Teacher",
            "email": "new@uiit.edu.pk",
            "role": "FACULTY",
            "password": "StartPass123!",
        },
    )
    ok = client.login(username="new@uiit.edu.pk", password="StartPass123!")
    assert ok


def test_weak_password_is_rejected(admin_client):
    resp = admin_client.post(
        reverse("invite_user"),
        {
            "name": "New Teacher",
            "email": "new@uiit.edu.pk",
            "role": "FACULTY",
            "password": "123",  # too short / too common / all numeric
        },
    )
    assert resp.status_code == 200  # re-render with errors, no redirect
    assert not User.objects.filter(email="new@uiit.edu.pk").exists()


def test_duplicate_email_is_rejected(admin_client, faculty_user):
    resp = admin_client.post(
        reverse("invite_user"),
        {
            "name": "Dupe",
            "email": faculty_user.email,
            "role": "FACULTY",
            "password": "StartPass123!",
        },
    )
    assert resp.status_code == 200  # re-render with error, no redirect
    assert b"already exists" in resp.content


def test_email_is_stored_lowercased(admin_client):
    admin_client.post(
        reverse("invite_user"),
        {
            "name": "Mixed Case",
            "email": "Mixed@UIIT.edu.pk",
            "role": "FACULTY",
            "password": "StartPass123!",
        },
    )
    assert User.objects.filter(email="mixed@uiit.edu.pk").exists()


# --- Admin resets an existing user's password ------------------------------


def test_reset_password_page_is_admin_only(faculty_client, faculty_user):
    url = reverse("faculty_set_password", args=[faculty_user.pk])
    assert faculty_client.get(url).status_code == 403


def test_admin_resets_user_password(admin_client, faculty_user, client):
    url = reverse("faculty_set_password", args=[faculty_user.pk])
    resp = admin_client.post(url, {"password": "ResetPass456!"}, follow=True)
    assert resp.status_code == 200

    faculty_user.refresh_from_db()
    assert faculty_user.check_password("ResetPass456!")
    assert client.login(username=faculty_user.email, password="ResetPass456!")
    assert AuditLog.objects.filter(action="user_set_password").exists()


def test_reset_password_rejects_weak_password(admin_client, faculty_user):
    url = reverse("faculty_set_password", args=[faculty_user.pk])
    resp = admin_client.post(url, {"password": "123"})
    assert resp.status_code == 200  # re-render with errors
    faculty_user.refresh_from_db()
    assert not faculty_user.check_password("123")
