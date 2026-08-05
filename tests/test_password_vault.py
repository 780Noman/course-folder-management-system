"""Admin-viewable (encrypted) password copies and auto-erase (TASK 4)."""

import pytest
from django.contrib.auth import password_validation
from django.test import Client
from django.urls import reverse

from accounts.models import User
from audit.models import AuditLog
from accounts.password_vault import (
    clear_admin_password,
    generate_password,
    reveal_admin_password,
    set_admin_password,
)

PASSWORD = "StrongPass123!"


# --- Vault unit behaviour ----------------------------------------------------

def test_set_and_reveal_round_trip(faculty_user):
    set_admin_password(faculty_user, "SharedPass456!")
    assert faculty_user.check_password("SharedPass456!")
    assert reveal_admin_password(faculty_user) == "SharedPass456!"
    assert faculty_user.password_status == User.PasswordStatus.SET_BY_ADMIN


def test_ciphertext_is_not_plaintext(faculty_user):
    set_admin_password(faculty_user, "SharedPass456!")
    assert "SharedPass456!" not in faculty_user.admin_password_ciphertext
    assert faculty_user.admin_password_ciphertext  # something is stored


def test_clear_erases_copy_and_flips_status(faculty_user):
    set_admin_password(faculty_user, "SharedPass456!")
    clear_admin_password(faculty_user)
    assert reveal_admin_password(faculty_user) is None
    assert faculty_user.admin_password_ciphertext == ""
    assert faculty_user.password_status == User.PasswordStatus.CHANGED_BY_FACULTY


def test_generated_password_meets_policy():
    for _ in range(5):
        pw = generate_password()
        password_validation.validate_password(pw)  # must not raise


# --- Admin flows via the views ----------------------------------------------

def test_admin_can_view_set_password_on_page(admin_client, faculty_user):
    admin_client.post(
        reverse("faculty_set_password", args=[faculty_user.pk]),
        {"password": "ResetPass456!"},
    )
    resp = admin_client.get(reverse("faculty_set_password", args=[faculty_user.pk]))
    assert resp.status_code == 200
    assert b"ResetPass456!" in resp.content  # revealed to the admin


def test_generate_sets_viewable_password(admin_client, faculty_user):
    admin_client.post(reverse("faculty_generate_password", args=[faculty_user.pk]))
    faculty_user.refresh_from_db()
    assert faculty_user.password_status == User.PasswordStatus.SET_BY_ADMIN
    generated = reveal_admin_password(faculty_user)
    assert generated and faculty_user.check_password(generated)


def test_generate_is_admin_only(faculty_client, faculty_user):
    assert faculty_client.post(
        reverse("faculty_generate_password", args=[faculty_user.pk])
    ).status_code == 403


def test_cannot_target_another_admin(admin_client, admin_user):
    # The vault endpoints are scoped to faculty; they must not act on an admin
    # (no admin-to-admin password takeover).
    assert admin_client.get(
        reverse("faculty_set_password", args=[admin_user.pk])
    ).status_code == 404
    assert admin_client.post(
        reverse("faculty_set_password", args=[admin_user.pk]),
        {"password": "Whatever123!"},
    ).status_code == 404
    assert admin_client.post(
        reverse("faculty_generate_password", args=[admin_user.pk])
    ).status_code == 404


def test_reveal_is_audited(admin_client, faculty_user):
    set_admin_password(faculty_user, "Visible123!")
    admin_client.get(reverse("faculty_set_password", args=[faculty_user.pk]))
    assert AuditLog.objects.filter(
        action="user_reveal_password", target_id=str(faculty_user.pk)
    ).exists()


def test_invite_stores_viewable_password(admin_client):
    admin_client.post(
        reverse("invite_user"),
        {"name": "New Teacher", "email": "new@uiit.edu.pk",
         "role": "FACULTY", "password": "InitialPass789!"},
    )
    user = User.objects.get(email="new@uiit.edu.pk")
    assert user.password_status == User.PasswordStatus.SET_BY_ADMIN
    assert reveal_admin_password(user) == "InitialPass789!"


# --- Auto-erase when faculty change their own password ----------------------

def test_faculty_change_erases_admin_copy(admin_client, faculty_user):
    admin_client.post(
        reverse("faculty_set_password", args=[faculty_user.pk]),
        {"password": "AdminGiven123!"},
    )
    faculty_user.refresh_from_db()
    assert reveal_admin_password(faculty_user) == "AdminGiven123!"

    # Faculty signs in and changes their own password.
    faculty = Client()
    faculty.force_login(faculty_user)
    resp = faculty.post(reverse("password_change"), {
        "old_password": "AdminGiven123!",
        "new_password1": "MyOwnPass456!",
        "new_password2": "MyOwnPass456!",
    })
    assert resp.status_code == 302

    faculty_user.refresh_from_db()
    assert reveal_admin_password(faculty_user) is None
    assert faculty_user.password_status == User.PasswordStatus.CHANGED_BY_FACULTY

    # Admin can no longer view it, only reset to regain a viewable copy.
    page = admin_client.get(reverse("faculty_set_password", args=[faculty_user.pk]))
    assert b"has set their own password" in page.content
    assert b"AdminGiven123!" not in page.content


def test_admin_reset_after_faculty_change_is_viewable_again(admin_client, faculty_user):
    set_admin_password(faculty_user, "First123!")
    clear_admin_password(faculty_user)  # simulate faculty self-change
    assert faculty_user.password_status == User.PasswordStatus.CHANGED_BY_FACULTY

    admin_client.post(
        reverse("faculty_set_password", args=[faculty_user.pk]),
        {"password": "SecondReset123!"},
    )
    faculty_user.refresh_from_db()
    assert faculty_user.password_status == User.PasswordStatus.SET_BY_ADMIN
    assert reveal_admin_password(faculty_user) == "SecondReset123!"
