"""Admin course search with live (HTMX) results (Phase 9, Task 1)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from academics.models import Course, Term
from folders.models import FolderStatus

User = get_user_model()

HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def data(db, faculty_user):
    term = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    other = User.objects.create_user(email="amir@uiit.edu.pk", name="Amir Sohail")
    c1 = Course.objects.create(code="CS101", title="Programming", section="A",
                               program="BSCS", study_semester=1,
                               instructor=faculty_user, term=term)
    c2 = Course.objects.create(code="SE201", title="Software Design", section="A",
                               program="BSSE", study_semester=3,
                               instructor=other, term=term)
    return {"term": term, "c1": c1, "c2": c2, "other": other}


def test_search_is_admin_only(faculty_client):
    assert faculty_client.get(reverse("course_search")).status_code == 403


@pytest.mark.django_db
def test_search_by_course_code(admin_client, data):
    resp = admin_client.get(reverse("course_search"), {"q": "CS101"})
    assert b"CS101" in resp.content
    assert b"SE201" not in resp.content


@pytest.mark.django_db
def test_search_by_title(admin_client, data):
    resp = admin_client.get(reverse("course_search"), {"q": "design"})
    assert b"SE201" in resp.content
    assert b"CS101" not in resp.content


@pytest.mark.django_db
def test_search_by_faculty_name(admin_client, data):
    resp = admin_client.get(reverse("course_search"), {"q": "amir"})
    assert b"SE201" in resp.content
    assert b"CS101" not in resp.content


@pytest.mark.django_db
def test_filter_by_program(admin_client, data):
    resp = admin_client.get(reverse("course_search"), {"program": "BSSE"})
    assert b"SE201" in resp.content
    assert b"CS101" not in resp.content


@pytest.mark.django_db
def test_filter_by_status(admin_client, data):
    data["c1"].folder.status = FolderStatus.CERTIFIED
    data["c1"].folder.save(update_fields=["status"])
    resp = admin_client.get(reverse("course_search"), {"status": "certified"})
    assert b"CS101" in resp.content
    assert b"SE201" not in resp.content


@pytest.mark.django_db
def test_htmx_request_returns_partial_only(admin_client, data):
    resp = admin_client.get(reverse("course_search"), {"q": "CS101"}, **HTMX)
    assert resp.status_code == 200
    assert b"course-results" in resp.content
    # The partial must NOT carry the full page chrome.
    assert b"<html" not in resp.content
    assert b"Find courses" not in resp.content


@pytest.mark.django_db
def test_full_request_returns_page(admin_client, data):
    resp = admin_client.get(reverse("course_search"))
    assert b"<html" in resp.content
    assert b"Find courses" in resp.content
