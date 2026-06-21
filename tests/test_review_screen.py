"""Admin review queue and review detail with red highlighting (Task 2)."""

import pytest
from django.urls import reverse

from academics.models import Course, Term
from folders.models import FolderStatus, ItemStatus


@pytest.fixture
def course(db, faculty_user):
    term = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    return Course.objects.create(
        code="CS101", title="PF", section="A", program="BSCS",
        study_semester=1, instructor=faculty_user, term=term,
    )


def test_review_queue_is_admin_only(faculty_client):
    assert faculty_client.get(reverse("review_list")).status_code == 403


@pytest.mark.django_db
def test_queue_lists_only_submitted_folders(admin_client, course, faculty_user):
    # A second course left in DRAFT should NOT appear.
    other = Course.objects.create(code="CS102", title="X", section="A", program="BSCS",
                                  study_semester=1, instructor=faculty_user,
                                  term=course.term)
    course.folder.status = FolderStatus.MID_SUBMITTED
    course.folder.save(update_fields=["status"])

    resp = admin_client.get(reverse("review_list"))
    assert b"CS101" in resp.content
    assert b"CS102" not in resp.content


def test_review_detail_is_admin_only(faculty_client, course):
    assert faculty_client.get(reverse("review_detail", args=[course.pk])).status_code == 403


@pytest.mark.django_db
def test_review_detail_flags_missing_required_items_in_red(admin_client, course):
    course.folder.status = FolderStatus.MID_SUBMITTED
    course.folder.save(update_fields=["status"])
    resp = admin_client.get(reverse("review_detail", args=[course.pk]))
    assert resp.status_code == 200
    # Required items are still PENDING -> shown as "Missing" with red styling.
    assert b"Missing" in resp.content
    assert b"bg-red-50" in resp.content


@pytest.mark.django_db
def test_flagged_item_note_shown(admin_client, course):
    item = course.folder.items.get(order=1)
    item.is_flagged = True
    item.review_note = "Wrong calendar attached"
    item.save()
    resp = admin_client.get(reverse("review_detail", args=[course.pk]))
    assert b"Wrong calendar attached" in resp.content
