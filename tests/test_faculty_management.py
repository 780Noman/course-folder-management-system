"""Admin faculty-management screens (Phase 2, Task 3)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


def test_faculty_list_is_admin_only(faculty_client):
    assert faculty_client.get(reverse("faculty_list")).status_code == 403


@pytest.mark.django_db
def test_list_shows_only_faculty(admin_client, faculty_user, admin_user):
    resp = admin_client.get(reverse("faculty_list"))
    assert resp.status_code == 200
    assert faculty_user.email.encode() in resp.content
    # The admin/focal person is not listed as faculty.
    assert admin_user.email.encode() not in resp.content


@pytest.mark.django_db
def test_search_filters_by_name_or_email(admin_client):
    User.objects.create_user(email="alice@uiit.edu.pk", name="Alice Khan")
    User.objects.create_user(email="bob@uiit.edu.pk", name="Bob Malik")

    resp = admin_client.get(reverse("faculty_list"), {"q": "alice"})
    assert b"alice@uiit.edu.pk" in resp.content
    assert b"bob@uiit.edu.pk" not in resp.content

    resp = admin_client.get(reverse("faculty_list"), {"q": "malik"})
    assert b"bob@uiit.edu.pk" in resp.content
    assert b"alice@uiit.edu.pk" not in resp.content


@pytest.mark.django_db
def test_deactivate_and_reactivate(admin_client, faculty_user):
    url = reverse("faculty_set_active", args=[faculty_user.pk])

    admin_client.post(url)
    faculty_user.refresh_from_db()
    assert faculty_user.is_active is False

    admin_client.post(url)
    faculty_user.refresh_from_db()
    assert faculty_user.is_active is True


@pytest.mark.django_db
def test_deactivated_faculty_cannot_log_in(client, faculty_user):
    faculty_user.is_active = False
    faculty_user.save(update_fields=["is_active"])
    ok = client.login(email=faculty_user.email, password="StrongPass123!")
    assert ok is False


@pytest.mark.django_db
def test_cannot_toggle_an_admin_via_faculty_screen(admin_client, admin_user):
    resp = admin_client.post(reverse("faculty_set_active", args=[admin_user.pk]))
    assert resp.status_code == 404
    admin_user.refresh_from_db()
    assert admin_user.is_active is True


def test_set_active_requires_post(admin_client, faculty_user):
    resp = admin_client.get(reverse("faculty_set_active", args=[faculty_user.pk]))
    assert resp.status_code == 405
