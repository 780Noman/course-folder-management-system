"""Admin approve / return-with-notes and the resubmit loop (Task 3)."""

import pytest
from django.urls import reverse

from academics.models import Course, Term
from folders.models import FolderStatus


@pytest.fixture
def course(db, faculty_user):
    term = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    return Course.objects.create(
        code="CS101", title="PF", section="A", program="BSCS",
        study_semester=1, instructor=faculty_user, term=term,
    )


@pytest.fixture
def mid_submitted(course):
    course.folder.status = FolderStatus.MID_SUBMITTED
    course.folder.save(update_fields=["status"])
    return course


def test_review_action_is_admin_only(faculty_client, mid_submitted):
    resp = faculty_client.post(
        reverse("review_action", args=[mid_submitted.pk]), {"action": "approve"}
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_approve_mid_moves_to_mid_approved(admin_client, mid_submitted):
    resp = admin_client.post(
        reverse("review_action", args=[mid_submitted.pk]), {"action": "approve"}
    )
    assert resp.status_code == 302
    folder = mid_submitted.folder
    folder.refresh_from_db()
    assert folder.status == FolderStatus.MID_APPROVED
    assert folder.mid_approved_at is not None


@pytest.mark.django_db
def test_return_mid_flags_items_and_reverts_to_draft(admin_client, mid_submitted):
    folder = mid_submitted.folder
    item = folder.items.get(order=1)

    resp = admin_client.post(
        reverse("review_action", args=[mid_submitted.pk]),
        {
            "action": "return",
            "overall_note": "Please fix the flagged items.",
            f"flag_{item.pk}": "on",
            f"note_{item.pk}": "Calendar is from last year",
        },
    )
    assert resp.status_code == 302
    folder.refresh_from_db()
    item.refresh_from_db()
    assert folder.status == FolderStatus.DRAFT
    assert folder.mid_return_note == "Please fix the flagged items."
    assert item.is_flagged is True
    assert item.review_note == "Calendar is from last year"


@pytest.mark.django_db
def test_return_requires_a_note_or_a_flag(admin_client, mid_submitted):
    resp = admin_client.post(
        reverse("review_action", args=[mid_submitted.pk]),
        {"action": "return"}, follow=True,
    )
    assert b"Add an overall note or flag at least one item" in resp.content
    mid_submitted.folder.refresh_from_db()
    assert mid_submitted.folder.status == FolderStatus.MID_SUBMITTED  # unchanged


@pytest.mark.django_db
def test_faculty_sees_flag_then_resubmit_clears_it(admin_client, mid_submitted, faculty_user):
    from django.test import Client

    folder = mid_submitted.folder
    item = folder.items.get(order=1)
    admin_client.post(
        reverse("review_action", args=[mid_submitted.pk]),
        {"action": "return", "overall_note": "fix",
         f"flag_{item.pk}": "on", f"note_{item.pk}": "bad calendar"},
    )

    # Faculty (separate client) opens the folder and sees the flag + return note.
    fac = Client()
    fac.force_login(faculty_user)
    resp = fac.get(reverse("folder_detail", args=[mid_submitted.pk]))
    assert b"Needs revision: bad calendar" in resp.content
    assert b"Returned for revision" in resp.content


@pytest.mark.django_db
def test_approve_final_moves_to_final_approved(admin_client, course):
    folder = course.folder
    folder.status = FolderStatus.FINAL_SUBMITTED
    folder.save(update_fields=["status"])
    admin_client.post(reverse("review_action", args=[course.pk]), {"action": "approve"})
    folder.refresh_from_db()
    assert folder.status == FolderStatus.FINAL_APPROVED
    assert folder.final_approved_at is not None


@pytest.mark.django_db
def test_return_final_reverts_to_mid_approved(admin_client, course):
    folder = course.folder
    folder.status = FolderStatus.FINAL_SUBMITTED
    folder.save(update_fields=["status"])
    item = folder.items.filter(phase="FINAL").first()
    admin_client.post(
        reverse("review_action", args=[course.pk]),
        {"action": "return", "overall_note": "redo results",
         f"flag_{item.pk}": "on", f"note_{item.pk}": "missing OBE"},
    )
    folder.refresh_from_db()
    assert folder.status == FolderStatus.MID_APPROVED
    assert folder.final_return_note == "redo results"


@pytest.mark.django_db
def test_cannot_act_when_not_under_review(admin_client, course):
    # Folder is DRAFT, not submitted.
    resp = admin_client.post(
        reverse("review_action", args=[course.pk]), {"action": "approve"}, follow=True
    )
    assert b"not awaiting review" in resp.content
