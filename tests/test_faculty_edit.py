"""Faculty edit permissions, email admin-only, and safe delete (TASK 2)."""

import pytest
from django.core import mail
from django.urls import reverse

from academics.models import Course, Term
from accounts.models import User


@pytest.fixture
def term(db):
    return Term.objects.create(season=Term.Season.SPRING, year=2026, is_current=True)


def _course(term, instructor):
    return Course.objects.create(
        code="CS101", title="PF", section="A", program="BSCS",
        study_semester=1, instructor=instructor, term=term,
    )


# --- Admin editing faculty email/name ---------------------------------------

def test_admin_can_edit_faculty_email(admin_client, faculty_user):
    resp = admin_client.post(
        reverse("faculty_edit", args=[faculty_user.pk]),
        {"name": "Dr Faculty", "email": "new.address@uiit.edu.pk"},
        follow=True,
    )
    assert resp.status_code == 200
    faculty_user.refresh_from_db()
    assert faculty_user.email == "new.address@uiit.edu.pk"


def test_email_change_notifies_faculty(admin_client, faculty_user):
    mail.outbox.clear()
    admin_client.post(
        reverse("faculty_edit", args=[faculty_user.pk]),
        {"name": faculty_user.name, "email": "moved@uiit.edu.pk"},
    )
    assert len(mail.outbox) == 1
    assert "moved@uiit.edu.pk" in mail.outbox[0].to


def test_admin_cannot_set_duplicate_faculty_email(admin_client, faculty_user, admin_user):
    other = User.objects.create_user(
        email="taken@uiit.edu.pk", name="Other", password="StrongPass123!"
    )
    resp = admin_client.post(
        reverse("faculty_edit", args=[faculty_user.pk]),
        {"name": faculty_user.name, "email": "TAKEN@uiit.edu.pk"},
    )
    assert resp.status_code == 200
    assert b"already exists" in resp.content
    faculty_user.refresh_from_db()
    assert faculty_user.email != "taken@uiit.edu.pk"


def test_faculty_edit_only_targets_faculty(admin_client, admin_user):
    # The edit endpoint is scoped to FACULTY; an admin pk is not editable here.
    resp = admin_client.get(reverse("faculty_edit", args=[admin_user.pk]))
    assert resp.status_code == 404


def test_faculty_cannot_reach_edit_endpoint(faculty_client, faculty_user):
    assert faculty_client.get(
        reverse("faculty_edit", args=[faculty_user.pk])
    ).status_code == 403


def test_changing_email_keeps_faculty_logged_in(admin_client, faculty_client, faculty_user):
    # faculty_client is already authenticated; an admin email edit must not
    # invalidate their session (email is not part of the session auth hash).
    admin_client.post(
        reverse("faculty_edit", args=[faculty_user.pk]),
        {"name": faculty_user.name, "email": "still.here@uiit.edu.pk"},
    )
    resp = faculty_client.get(reverse("faculty_dashboard"))
    assert resp.status_code == 200


# --- Faculty self-service: password only, never email -----------------------

def test_faculty_profile_is_read_only(faculty_client, faculty_user):
    resp = faculty_client.get(reverse("profile"))
    assert resp.status_code == 200
    assert faculty_user.email.encode() in resp.content
    # No editable email form is offered to faculty.
    assert b'name="email"' not in resp.content


def test_faculty_cannot_change_own_email_via_post(faculty_client, faculty_user):
    resp = faculty_client.post(
        reverse("profile"),
        {"name": "Hacker", "email": "self.changed@uiit.edu.pk"},
    )
    assert resp.status_code == 403
    faculty_user.refresh_from_db()
    assert faculty_user.email == "faculty@uiit.edu.pk"


# --- Admin editing own email ------------------------------------------------

def test_admin_can_edit_own_email(admin_client, admin_user):
    resp = admin_client.post(
        reverse("profile"),
        {"name": admin_user.name, "email": "focal.new@uiit.edu.pk"},
        follow=True,
    )
    assert resp.status_code == 200
    admin_user.refresh_from_db()
    assert admin_user.email == "focal.new@uiit.edu.pk"


# --- Safe delete ------------------------------------------------------------

def test_faculty_with_courses_cannot_be_hard_deleted(admin_client, faculty_user, term):
    _course(term, faculty_user)
    resp = admin_client.get(reverse("faculty_delete", args=[faculty_user.pk]))
    assert resp.status_code == 200
    assert b"cannot be" in resp.content  # steered to deactivate
    # A POST is refused and the user survives.
    admin_client.post(
        reverse("faculty_delete", args=[faculty_user.pk]), {"confirm": "DELETE"}
    )
    assert User.objects.filter(pk=faculty_user.pk).exists()


def test_faculty_without_records_can_be_hard_deleted(admin_client, faculty_user):
    resp = admin_client.post(
        reverse("faculty_delete", args=[faculty_user.pk]),
        {"confirm": "DELETE"},
        follow=True,
    )
    assert resp.status_code == 200
    assert not User.objects.filter(pk=faculty_user.pk).exists()


def test_hard_delete_requires_confirmation(admin_client, faculty_user):
    admin_client.post(reverse("faculty_delete", args=[faculty_user.pk]), {"confirm": "no"})
    assert User.objects.filter(pk=faculty_user.pk).exists()


def test_faculty_delete_is_admin_only(faculty_client, faculty_user):
    assert faculty_client.get(
        reverse("faculty_delete", args=[faculty_user.pk])
    ).status_code == 403
