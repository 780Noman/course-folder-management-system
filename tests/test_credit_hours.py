"""Flexible credit-hours field: format 4(3-3) or a plain number (TASK 5)."""

import pytest
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils import timezone

from academics.forms import CourseForm
from academics.models import Course, Term


@pytest.fixture
def term(db):
    return Term.objects.create(season=Term.Season.SPRING, year=2026, is_current=True)


def _build(term, instructor, value):
    return Course(
        code="CS101", title="PF", section="A", program="BSCS",
        study_semester=1, credit_hours=value, instructor=instructor, term=term,
    )


@pytest.mark.parametrize("value", ["3", "4(3-3)", "1(1-0)", "12", "3(3-0)"])
def test_valid_formats_pass_validation(term, faculty_user, value):
    _build(term, faculty_user, value).full_clean()  # must not raise


@pytest.mark.parametrize("value", ["", "abc", "4(3-3", "3-3", "4()", "4(3)"])
def test_invalid_formats_are_rejected(term, faculty_user, value):
    with pytest.raises(ValidationError):
        _build(term, faculty_user, value).full_clean()


def test_form_accepts_bracket_format(term, faculty_user):
    form = CourseForm(data={
        "code": "CS101", "title": "PF", "section": "A", "program": "BSCS",
        "study_semester": 1, "credit_hours": "4(3-3)",
        "instructor": faculty_user.pk, "term": term.pk,
    })
    assert form.is_valid(), form.errors


def test_form_rejects_bad_credit_hours(term, faculty_user):
    form = CourseForm(data={
        "code": "CS101", "title": "PF", "section": "A", "program": "BSCS",
        "study_semester": 1, "credit_hours": "lots",
        "instructor": faculty_user.pk, "term": term.pk,
    })
    assert not form.is_valid()
    assert "credit_hours" in form.errors


def test_bracket_value_round_trips(term, faculty_user):
    course = _build(term, faculty_user, "4(3-3)")
    course.save()
    course.refresh_from_db()
    assert course.credit_hours == "4(3-3)"


def test_certificate_shows_credit_hours(term, faculty_user):
    course = _build(term, faculty_user, "4(3-3)")
    course.save()
    html = render_to_string(
        "review/certificate.html",
        {
            "course": course, "term": term, "rows": [],
            "issued_by_name": "Focal Person", "issued_at": timezone.now(),
            "uiit_logo": "", "arid_logo": "",
        },
    )
    assert "4(3-3)" in html
