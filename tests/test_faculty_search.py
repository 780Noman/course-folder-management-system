"""Faculty dashboard: filter own courses by term + live search (Task 2)."""

import pytest
from django.urls import reverse

from academics.models import Course, Term

HTMX = {"HTTP_HX_REQUEST": "true"}


def _course(term, instructor, code, title=None, sem=1):
    return Course.objects.create(
        code=code, title=title or code, section="A", program="BSCS",
        study_semester=sem, instructor=instructor, term=term,
    )


@pytest.fixture
def terms(db):
    return {
        "fall": Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True),
        "spring": Term.objects.create(season=Term.Season.SPRING, year=2025),
    }


@pytest.mark.django_db
def test_search_filters_within_selected_term(faculty_client, faculty_user, terms):
    _course(terms["fall"], faculty_user, "CS301", "Operating Systems")
    _course(terms["fall"], faculty_user, "CS302", "Databases")

    resp = faculty_client.get(reverse("faculty_dashboard"), {"q": "database"})
    assert b"CS302" in resp.content
    assert b"CS301" not in resp.content


@pytest.mark.django_db
def test_search_respects_term_scope(faculty_client, faculty_user, terms):
    _course(terms["fall"], faculty_user, "CS301", "Operating Systems")
    _course(terms["spring"], faculty_user, "CS101", "Operating Concepts")

    # Default term is the current (fall); searching "Operating" finds only CS301.
    resp = faculty_client.get(reverse("faculty_dashboard"), {"q": "operating"})
    assert b"CS301" in resp.content
    assert b"CS101" not in resp.content

    # Switch to spring + same query -> only CS101.
    resp = faculty_client.get(
        reverse("faculty_dashboard"), {"q": "operating", "term": terms["spring"].pk}
    )
    assert b"CS101" in resp.content
    assert b"CS301" not in resp.content


@pytest.mark.django_db
def test_htmx_returns_grid_partial_only(faculty_client, faculty_user, terms):
    _course(terms["fall"], faculty_user, "CS301")
    resp = faculty_client.get(reverse("faculty_dashboard"), {"q": "CS301"}, **HTMX)
    assert resp.status_code == 200
    assert b"faculty-courses" in resp.content
    assert b"<html" not in resp.content
    assert b"Sign out" not in resp.content  # no page chrome


@pytest.mark.django_db
def test_search_only_returns_own_courses(faculty_client, faculty_user, terms):
    from django.contrib.auth import get_user_model
    other = get_user_model().objects.create_user(email="o@uiit.edu.pk", name="Other")
    _course(terms["fall"], faculty_user, "CS301", "Networks")
    _course(terms["fall"], other, "CS999", "Networks Advanced")

    resp = faculty_client.get(reverse("faculty_dashboard"), {"q": "networks"})
    assert b"CS301" in resp.content
    assert b"CS999" not in resp.content


@pytest.mark.django_db
def test_no_match_shows_message(faculty_client, faculty_user, terms):
    _course(terms["fall"], faculty_user, "CS301", "Operating Systems")
    resp = faculty_client.get(reverse("faculty_dashboard"), {"q": "zzz"})
    assert b"No courses match" in resp.content
