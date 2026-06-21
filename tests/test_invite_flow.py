"""Invite flow (Task 4): admin invites a user who sets their own password via a
single-use, expiring link. No raw password is ever stored or emailed."""

import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

User = get_user_model()


@pytest.fixture(autouse=True)
def _locmem_email(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


def test_invite_page_is_admin_only(faculty_client):
    assert faculty_client.get(reverse("invite_user")).status_code == 403


def test_admin_can_invite_and_email_is_sent(admin_client):
    resp = admin_client.post(
        reverse("invite_user"),
        {"name": "New Teacher", "email": "new@uiit.edu.pk", "role": "FACULTY"},
        follow=True,
    )
    assert resp.status_code == 200

    user = User.objects.get(email="new@uiit.edu.pk")
    assert user.role == User.Role.FACULTY
    assert user.has_usable_password() is False  # no password set yet

    assert len(mail.outbox) == 1
    body = mail.outbox[0].body
    assert "/invite/" in body
    # The raw password must never appear anywhere in the email.
    assert "password" not in body.lower() or "set your password" in body.lower()


def _extract_invite_path(email_body):
    match = re.search(r"(/invite/[^\s]+)", email_body)
    assert match, "invite link not found in email"
    return match.group(1)


def test_invited_user_sets_password_and_is_logged_in(admin_client, client):
    admin_client.post(
        reverse("invite_user"),
        {"name": "New Teacher", "email": "new@uiit.edu.pk", "role": "FACULTY"},
    )
    path = _extract_invite_path(mail.outbox[0].body)

    # First GET redirects to the 'set-password' step (token moved to session).
    resp = client.get(path)
    assert resp.status_code == 302
    form_url = resp.headers["Location"]

    resp = client.get(form_url)
    assert resp.status_code == 200
    assert b"Set your password" in resp.content

    resp = client.post(
        form_url,
        {"new_password1": "BrandNewPass123!", "new_password2": "BrandNewPass123!"},
    )
    assert resp.status_code == 302  # success -> dashboard

    user = User.objects.get(email="new@uiit.edu.pk")
    assert user.has_usable_password()
    assert user.check_password("BrandNewPass123!")


def test_invite_link_is_single_use(admin_client, client):
    admin_client.post(
        reverse("invite_user"),
        {"name": "New Teacher", "email": "new@uiit.edu.pk", "role": "FACULTY"},
    )
    path = _extract_invite_path(mail.outbox[0].body)

    # Use the link once to set a password.
    resp = client.get(path)
    form_url = resp.headers["Location"]
    client.post(
        form_url,
        {"new_password1": "BrandNewPass123!", "new_password2": "BrandNewPass123!"},
    )

    # The original token is now invalid (password changed) -> invalid link page.
    fresh = client.__class__()
    resp = fresh.get(path)
    # Either a redirect to the set-password step that then shows invalid, or a
    # direct invalid render. Follow to the final page and assert it's not usable.
    resp = fresh.get(path, follow=True)
    assert b"Link not valid" in resp.content


def test_duplicate_email_is_rejected(admin_client, faculty_user):
    resp = admin_client.post(
        reverse("invite_user"),
        {"name": "Dupe", "email": faculty_user.email, "role": "FACULTY"},
    )
    assert resp.status_code == 200  # re-render with error, no redirect
    assert b"already exists" in resp.content
    assert len(mail.outbox) == 0
