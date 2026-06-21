"""Course model + admin course-management screen (Phase 2, Task 2)."""

import pytest
from django.db import IntegrityError
from django.urls import reverse

from academics.models import Course, Term


@pytest.fixture
def term(db):
    return Term.objects.create(season=Term.Season.SPRING, year=2026, is_current=True)


def _course_payload(term, instructor, **overrides):
    data = {
        "code": "CS101",
        "title": "Programming Fundamentals",
        "section": "A",
        "program": "BSCS",
        "study_semester": 1,
        "credit_hours": 3,
        "instructor": instructor.pk,
        "term": term.pk,
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_course_uniqueness_code_section_term(term, faculty_user):
    Course.objects.create(
        code="CS101", title="PF", section="A", program="BSCS",
        study_semester=1, instructor=faculty_user, term=term,
    )
    with pytest.raises(IntegrityError):
        Course.objects.create(
            code="CS101", title="PF dup", section="A", program="BSCS",
            study_semester=1, instructor=faculty_user, term=term,
        )


@pytest.mark.django_db
def test_same_code_section_allowed_in_different_term(faculty_user):
    spring = Term.objects.create(season=Term.Season.SPRING, year=2026)
    fall = Term.objects.create(season=Term.Season.FALL, year=2026)
    Course.objects.create(code="CS101", title="PF", section="A", program="BSCS",
                          study_semester=1, instructor=faculty_user, term=spring)
    # Same code+section in a different term is fine (history across terms).
    Course.objects.create(code="CS101", title="PF", section="A", program="BSCS",
                          study_semester=1, instructor=faculty_user, term=fall)
    assert Course.objects.count() == 2


def test_course_list_is_admin_only(faculty_client):
    assert faculty_client.get(reverse("course_list")).status_code == 403


def test_admin_can_create_and_assign_course(admin_client, term, faculty_user):
    resp = admin_client.post(
        reverse("course_list"), _course_payload(term, faculty_user), follow=True
    )
    assert resp.status_code == 200
    course = Course.objects.get(code="CS101", section="A", term=term)
    assert course.instructor == faculty_user


def test_admin_duplicate_course_rejected_in_form(admin_client, term, faculty_user):
    Course.objects.create(code="CS101", title="PF", section="A", program="BSCS",
                          study_semester=1, instructor=faculty_user, term=term)
    resp = admin_client.post(reverse("course_list"), _course_payload(term, faculty_user))
    assert resp.status_code == 200
    assert b"already exists" in resp.content
    assert Course.objects.filter(code="CS101", section="A", term=term).count() == 1


def test_course_list_filters_by_term(admin_client, faculty_user):
    spring = Term.objects.create(season=Term.Season.SPRING, year=2026)
    fall = Term.objects.create(season=Term.Season.FALL, year=2026)
    Course.objects.create(code="CS101", title="PF", section="A", program="BSCS",
                          study_semester=1, instructor=faculty_user, term=spring)
    Course.objects.create(code="CS201", title="DS", section="A", program="BSCS",
                          study_semester=3, instructor=faculty_user, term=fall)

    resp = admin_client.get(reverse("course_list"), {"term": spring.pk})
    assert b"CS101" in resp.content
    assert b"CS201" not in resp.content


@pytest.mark.django_db
def test_instructor_choices_limited_to_active_faculty(admin_user, faculty_user):
    """An admin user must not be selectable as an instructor."""
    from academics.forms import CourseForm

    qs = CourseForm().fields["instructor"].queryset
    assert faculty_user in qs
    assert admin_user not in qs
