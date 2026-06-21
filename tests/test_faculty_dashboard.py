"""Faculty dashboard: own courses, current-term default, term switch (Task 4)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from academics.models import Course, Term

User = get_user_model()


def _course(term, instructor, code, **kw):
    return Course.objects.create(
        code=code, title=kw.get("title", code), section=kw.get("section", "A"),
        program="BSCS", study_semester=kw.get("sem", 1),
        instructor=instructor, term=term,
    )


@pytest.fixture
def terms(db):
    spring = Term.objects.create(season=Term.Season.SPRING, year=2025)
    fall = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    return {"spring": spring, "fall": fall}


@pytest.mark.django_db
def test_defaults_to_current_term(faculty_client, faculty_user, terms):
    _course(terms["fall"], faculty_user, "CS301")   # current term
    _course(terms["spring"], faculty_user, "CS101")  # past term

    resp = faculty_client.get(reverse("faculty_dashboard"))
    assert resp.status_code == 200
    assert b"CS301" in resp.content       # current-term course shown
    assert b"CS101" not in resp.content   # past-term course hidden by default


@pytest.mark.django_db
def test_term_switch_shows_past_term(faculty_client, faculty_user, terms):
    _course(terms["fall"], faculty_user, "CS301")
    _course(terms["spring"], faculty_user, "CS101")

    resp = faculty_client.get(
        reverse("faculty_dashboard"), {"term": terms["spring"].pk}
    )
    assert b"CS101" in resp.content
    assert b"CS301" not in resp.content


@pytest.mark.django_db
def test_faculty_only_sees_own_courses(faculty_client, faculty_user, terms):
    other = User.objects.create_user(email="other@uiit.edu.pk", name="Other Teacher")
    _course(terms["fall"], faculty_user, "CS301")
    _course(terms["fall"], other, "CS999")

    resp = faculty_client.get(reverse("faculty_dashboard"))
    assert b"CS301" in resp.content
    assert b"CS999" not in resp.content


@pytest.mark.django_db
def test_switcher_only_lists_taught_terms(faculty_client, faculty_user, terms):
    # Faculty taught only in spring; an empty extra term must not appear.
    Term.objects.create(season=Term.Season.SUMMER, year=2026)
    _course(terms["spring"], faculty_user, "CS101")

    resp = faculty_client.get(reverse("faculty_dashboard"))
    content = resp.content.decode()
    assert "Spring 2025" in content
    assert "Summer 2026" not in content


@pytest.mark.django_db
def test_no_courses_shows_empty_state(faculty_client, faculty_user, terms):
    resp = faculty_client.get(reverse("faculty_dashboard"))
    assert resp.status_code == 200
    assert b"no assigned courses" in resp.content.lower()
