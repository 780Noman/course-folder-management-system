"""Term model + admin term-management screen (Phase 2, Task 1)."""

import pytest
from django.urls import reverse

from academics.models import Term


@pytest.mark.django_db
def test_name_is_derived_from_season_and_year():
    term = Term.objects.create(season=Term.Season.SPRING, year=2026)
    assert term.name == "Spring 2026"
    assert str(term) == "Spring 2026"


@pytest.mark.django_db
def test_only_one_current_term_is_kept():
    spring = Term.objects.create(season=Term.Season.SPRING, year=2026, is_current=True)
    fall = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)

    spring.refresh_from_db()
    fall.refresh_from_db()
    assert fall.is_current is True
    assert spring.is_current is False
    assert Term.objects.filter(is_current=True).count() == 1
    assert Term.get_current() == fall


@pytest.mark.django_db
def test_duplicate_season_year_blocked_at_db_level():
    Term.objects.create(season=Term.Season.FALL, year=2026)
    from django.db import IntegrityError

    with pytest.raises(IntegrityError):
        Term.objects.create(season=Term.Season.FALL, year=2026)


def test_term_list_is_admin_only(faculty_client):
    assert faculty_client.get(reverse("term_list")).status_code == 403


def test_admin_can_create_term(admin_client):
    resp = admin_client.post(
        reverse("term_list"),
        {"season": "SPRING", "year": 2026, "is_current": "on"},
        follow=True,
    )
    assert resp.status_code == 200
    term = Term.objects.get(season="SPRING", year=2026)
    assert term.is_current is True


def test_admin_duplicate_term_is_rejected_in_form(admin_client):
    Term.objects.create(season=Term.Season.SPRING, year=2026)
    resp = admin_client.post(
        reverse("term_list"), {"season": "SPRING", "year": 2026}
    )
    assert resp.status_code == 200
    assert b"already exists" in resp.content
    assert Term.objects.filter(season="SPRING", year=2026).count() == 1


def test_admin_can_set_current_term(admin_client):
    spring = Term.objects.create(season=Term.Season.SPRING, year=2026, is_current=True)
    fall = Term.objects.create(season=Term.Season.FALL, year=2026)

    resp = admin_client.post(reverse("term_set_current", args=[fall.pk]))
    assert resp.status_code == 302

    spring.refresh_from_db()
    fall.refresh_from_db()
    assert fall.is_current is True and spring.is_current is False


def test_set_current_requires_post(admin_client):
    fall = Term.objects.create(season=Term.Season.FALL, year=2026)
    assert admin_client.get(reverse("term_set_current", args=[fall.pk])).status_code == 405
