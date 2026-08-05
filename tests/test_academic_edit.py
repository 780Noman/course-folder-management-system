"""Editing terms and courses (TASK 3)."""

import pytest
from django.test import Client
from django.urls import reverse

from academics.models import Course, Term
from folders.models import CourseFolder


@pytest.fixture
def term(db):
    return Term.objects.create(season=Term.Season.SPRING, year=2026, is_current=True)


def _course(term, instructor, **overrides):
    data = dict(code="CS101", title="PF", section="A", program="BSCS",
                study_semester=1, credit_hours=3, instructor=instructor, term=term)
    data.update(overrides)
    return Course.objects.create(**data)


def _course_payload(term, instructor, **overrides):
    data = {
        "code": "CS101", "title": "PF", "section": "A", "program": "BSCS",
        "study_semester": 1, "credit_hours": 3,
        "instructor": instructor.pk, "term": term.pk,
    }
    data.update(overrides)
    return data


# --- Terms ------------------------------------------------------------------

def test_admin_can_edit_term(admin_client, term):
    resp = admin_client.post(
        reverse("term_edit", args=[term.pk]),
        {"season": Term.Season.SPRING, "year": 2027, "is_current": True},
        follow=True,
    )
    assert resp.status_code == 200
    term.refresh_from_db()
    assert term.year == 2027


def test_term_edit_rejects_duplicate(admin_client, term):
    Term.objects.create(season=Term.Season.FALL, year=2026)
    # Try to make the Spring term collide with the existing Fall 2026.
    resp = admin_client.post(
        reverse("term_edit", args=[term.pk]),
        {"season": Term.Season.FALL, "year": 2026},
    )
    assert resp.status_code == 200
    assert b"already exists" in resp.content
    term.refresh_from_db()
    assert term.season == Term.Season.SPRING


def test_term_edit_can_set_current(admin_client):
    old = Term.objects.create(season=Term.Season.SPRING, year=2025, is_current=True)
    new = Term.objects.create(season=Term.Season.FALL, year=2025, is_current=False)
    admin_client.post(
        reverse("term_edit", args=[new.pk]),
        {"season": Term.Season.FALL, "year": 2025, "is_current": True},
    )
    old.refresh_from_db()
    new.refresh_from_db()
    assert new.is_current and not old.is_current


def test_term_edit_is_admin_only(faculty_client, term):
    assert faculty_client.get(reverse("term_edit", args=[term.pk])).status_code == 403


# --- Courses ----------------------------------------------------------------

def test_admin_can_edit_course(admin_client, term, faculty_user):
    course = _course(term, faculty_user)
    resp = admin_client.post(
        reverse("course_edit", args=[course.pk]),
        _course_payload(term, faculty_user, title="Programming Fundamentals"),
        follow=True,
    )
    assert resp.status_code == 200
    course.refresh_from_db()
    assert course.title == "Programming Fundamentals"


def test_course_edit_rejects_duplicate(admin_client, term, faculty_user):
    _course(term, faculty_user, code="CS101", section="A")
    target = _course(term, faculty_user, code="CS201", section="B")
    # Try to collide target with the existing CS101/A in the same term.
    resp = admin_client.post(
        reverse("course_edit", args=[target.pk]),
        _course_payload(term, faculty_user, code="CS101", section="A"),
    )
    assert resp.status_code == 200
    assert b"already exists" in resp.content
    target.refresh_from_db()
    assert target.code == "CS201"


def test_course_edit_preserves_existing_folder(admin_client, term, faculty_user):
    course = _course(term, faculty_user)
    # A folder is auto-seeded when the course is created.
    folder = CourseFolder.objects.get(course=course)
    admin_client.post(
        reverse("course_edit", args=[course.pk]),
        _course_payload(term, faculty_user, title="Renamed"),
    )
    # The folder is neither rebuilt nor duplicated.
    assert CourseFolder.objects.filter(course=course).count() == 1
    assert CourseFolder.objects.get(course=course).pk == folder.pk


def test_course_edit_reflects_in_faculty_view(admin_client, term, faculty_user):
    course = _course(term, faculty_user)
    admin_client.post(
        reverse("course_edit", args=[course.pk]),
        _course_payload(term, faculty_user, title="Data Structures"),
    )
    # A separate client for the faculty (the shared test `client` is the admin's).
    faculty = Client()
    faculty.force_login(faculty_user)
    resp = faculty.get(reverse("faculty_dashboard"))
    assert b"Data Structures" in resp.content


def test_course_edit_is_admin_only(faculty_client, term, faculty_user):
    course = _course(term, faculty_user)
    assert faculty_client.get(
        reverse("course_edit", args=[course.pk])
    ).status_code == 403
