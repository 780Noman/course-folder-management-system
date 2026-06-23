"""Logged-in users can change their own password."""

import pytest
from django.urls import reverse

PASSWORD = "StrongPass123!"


def test_change_password_requires_login(client):
    resp = client.get(reverse("password_change"))
    assert resp.status_code == 302
    assert reverse("login") in resp.headers["Location"]


@pytest.mark.django_db
def test_change_password_page_loads(faculty_client):
    resp = faculty_client.get(reverse("password_change"))
    assert resp.status_code == 200
    assert b"Change your password" in resp.content


@pytest.mark.django_db
def test_change_password_updates_credentials(client, faculty_user):
    client.force_login(faculty_user)
    resp = client.post(reverse("password_change"), {
        "old_password": PASSWORD,
        "new_password1": "BrandNewPass456!",
        "new_password2": "BrandNewPass456!",
    })
    assert resp.status_code == 302
    assert resp.headers["Location"] == reverse("password_change_done")
    faculty_user.refresh_from_db()
    assert faculty_user.check_password("BrandNewPass456!")


@pytest.mark.django_db
def test_change_password_rejects_wrong_old_password(client, faculty_user):
    client.force_login(faculty_user)
    resp = client.post(reverse("password_change"), {
        "old_password": "wrong-password",
        "new_password1": "BrandNewPass456!",
        "new_password2": "BrandNewPass456!",
    })
    assert resp.status_code == 200  # re-render with error
    faculty_user.refresh_from_db()
    assert faculty_user.check_password(PASSWORD)  # unchanged
