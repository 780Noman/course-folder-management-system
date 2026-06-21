"""Mark items Not Applicable; excluded from completeness (Task 5)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from academics.models import Course, Term
from folders.models import CourseFolder, ItemStatus

User = get_user_model()


@pytest.fixture
def course(db, faculty_user):
    term = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    return Course.objects.create(
        code="CS101", title="PF", section="A", program="BSCS",
        study_semester=1, instructor=faculty_user, term=term,
    )


@pytest.mark.django_db
def test_mark_na_with_note(faculty_client, course):
    lab = course.folder.items.get(order=8)  # Lab Tasks/Evaluation (core, required)
    resp = faculty_client.post(
        reverse("item_mark_na", args=[lab.pk]), {"na_note": "Theory course, no lab"}
    )
    assert resp.status_code == 302
    lab.refresh_from_db()
    assert lab.status == ItemStatus.NOT_APPLICABLE
    assert lab.na_note == "Theory course, no lab"


@pytest.mark.django_db
def test_na_excluded_from_completeness(faculty_client, course):
    folder = course.folder
    general = folder.items.filter(phase="GENERAL")
    before = CourseFolder.progress(general)["total"]

    lab = folder.items.get(order=8)
    faculty_client.post(reverse("item_mark_na", args=[lab.pk]))

    after = CourseFolder.progress(folder.items.filter(phase="GENERAL"))["total"]
    assert after == before - 1  # the N/A item drops out of the denominator


@pytest.mark.django_db
def test_clear_na_returns_to_pending(faculty_client, course):
    item = course.folder.items.get(order=8)
    faculty_client.post(reverse("item_mark_na", args=[item.pk]), {"na_note": "x"})
    faculty_client.post(reverse("item_clear_na", args=[item.pk]))
    item.refresh_from_db()
    assert item.status == ItemStatus.PENDING
    assert item.na_note == ""


@pytest.mark.django_db
def test_na_allowed_on_required_core_item(faculty_client, course):
    """N/A is permitted even on core required items (e.g. no-lab course)."""
    final_exam = course.folder.items.get(order=24)  # required core
    faculty_client.post(reverse("item_mark_na", args=[final_exam.pk]))
    final_exam.refresh_from_db()
    assert final_exam.status == ItemStatus.NOT_APPLICABLE


@pytest.mark.django_db
def test_other_faculty_cannot_mark_na(client, course):
    other = User.objects.create_user(email="other@uiit.edu.pk", name="Other")
    client.force_login(other)
    item = course.folder.items.get(order=8)
    resp = client.post(reverse("item_mark_na", args=[item.pk]))
    assert resp.status_code == 403


def test_mark_na_requires_post(faculty_client, course):
    item = course.folder.items.get(order=8)
    assert faculty_client.get(reverse("item_mark_na", args=[item.pk])).status_code == 405
