"""Phase 11 Task 4: audit log covers create/update/delete/issue actions."""

import pytest
from django.urls import reverse

from academics.models import Course, Term
from audit.models import AuditLog


@pytest.fixture
def term(db):
    return Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)


@pytest.mark.django_db
def test_user_invite_audited(admin_client):
    admin_client.post(
        reverse("invite_user"),
        {
            "name": "New",
            "email": "new@uiit.edu.pk",
            "role": "FACULTY",
            "password": "StartPass123!",
        },
    )
    assert AuditLog.objects.filter(action="user_invite").exists()


@pytest.mark.django_db
def test_faculty_deactivate_activate_audited(admin_client, faculty_user):
    url = reverse("faculty_set_active", args=[faculty_user.pk])
    admin_client.post(url)
    assert AuditLog.objects.filter(action="faculty_deactivate").exists()
    admin_client.post(url)
    assert AuditLog.objects.filter(action="faculty_activate").exists()


@pytest.mark.django_db
def test_term_create_and_set_current_audited(admin_client):
    admin_client.post(reverse("term_list"), {"season": "SPRING", "year": 2027})
    assert AuditLog.objects.filter(action="term_create").exists()
    t = Term.objects.create(season=Term.Season.FALL, year=2028)
    admin_client.post(reverse("term_set_current", args=[t.pk]))
    assert AuditLog.objects.filter(action="term_set_current").exists()


@pytest.mark.django_db
def test_course_create_audited(admin_client, term, faculty_user):
    admin_client.post(reverse("course_list"), {
        "code": "CS101", "title": "PF", "section": "A", "program": "BSCS",
        "study_semester": 1, "credit_hours": 3,
        "instructor": faculty_user.pk, "term": term.pk,
    })
    assert AuditLog.objects.filter(action="course_create").exists()


@pytest.mark.django_db
def test_item_add_remove_and_na_audited(faculty_client, term, faculty_user):
    course = Course.objects.create(code="CS101", title="PF", section="A",
                                   program="BSCS", study_semester=1,
                                   instructor=faculty_user, term=term)
    # add
    faculty_client.post(reverse("item_add", args=[course.pk]),
                        {"kind": "quiz", "phase": "MID"})
    assert AuditLog.objects.filter(action="item_add").exists()
    # mark N/A (update)
    item = course.folder.items.get(order=1)
    faculty_client.post(reverse("item_mark_na", args=[item.pk]))
    assert AuditLog.objects.filter(action="item_mark_na").exists()
    # remove (delete) the added quiz
    added = course.folder.items.filter(is_removable=True).order_by("-order").first()
    faculty_client.post(reverse("item_remove", args=[added.pk]))
    assert AuditLog.objects.filter(action="item_remove").exists()


@pytest.mark.django_db
def test_every_audit_entry_records_an_actor(admin_client, term, faculty_user):
    """Sanity: admin actions attribute the acting user."""
    admin_client.post(reverse("course_list"), {
        "code": "CS900", "title": "X", "section": "A", "program": "BSCS",
        "study_semester": 1, "credit_hours": 3,
        "instructor": faculty_user.pk, "term": term.pk,
    })
    entry = AuditLog.objects.get(action="course_create")
    assert entry.actor is not None
    assert entry.target_type == "Course"
