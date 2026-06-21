"""Faculty submit actions and gating (Phase 6, Task 1)."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from academics.models import Course, Term
from folders.models import FolderStatus, ItemStatus, SampleKind
from review import services


@pytest.fixture(autouse=True)
def _media_to_tmp(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.fixture
def course(db, faculty_user):
    term = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    return Course.objects.create(
        code="CS101", title="PF", section="A", program="BSCS",
        study_semester=1, instructor=faculty_user, term=term,
    )


def _pdf(name="x.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 data", content_type="application/pdf")


def _complete_phase(faculty_client, folder, phases):
    """Make every required item in the given phases satisfied."""
    for item in folder.items.filter(phase__in=phases, is_required=True):
        if item.allows_samples:
            for kind in (SampleKind.WORST, SampleKind.AVERAGE, SampleKind.BEST):
                faculty_client.post(reverse("file_upload", args=[item.pk]),
                                    {"file": _pdf(), "sample_kind": kind})
        else:
            faculty_client.post(reverse("file_upload", args=[item.pk]), {"file": _pdf()})


@pytest.mark.django_db
def test_cannot_submit_mid_until_general_and_mid_complete(faculty_client, course):
    folder = course.folder
    resp = faculty_client.post(reverse("submit_mid", args=[course.pk]), follow=True)
    assert b"Complete every required" in resp.content
    folder.refresh_from_db()
    assert folder.status == FolderStatus.DRAFT


@pytest.mark.django_db
def test_submit_mid_when_complete(faculty_client, course):
    folder = course.folder
    from folders.models import CourseFolder
    _complete_phase(faculty_client, folder, CourseFolder.MID_PHASES)

    resp = faculty_client.post(reverse("submit_mid", args=[course.pk]), follow=True)
    assert b"Mid-term submitted" in resp.content
    folder.refresh_from_db()
    assert folder.status == FolderStatus.MID_SUBMITTED
    assert folder.mid_submitted_at is not None


@pytest.mark.django_db
def test_final_blocked_until_mid_approved(faculty_client, course):
    folder = course.folder
    from folders.models import CourseFolder
    _complete_phase(faculty_client, folder, CourseFolder.FINAL_PHASES)
    # Status is DRAFT (mid not approved) -> final must be refused.
    resp = faculty_client.post(reverse("submit_final", args=[course.pk]), follow=True)
    assert b"only after the mid-term is approved" in resp.content
    folder.refresh_from_db()
    assert folder.status == FolderStatus.DRAFT


@pytest.mark.django_db
def test_submit_final_after_mid_approved(faculty_client, course):
    folder = course.folder
    from folders.models import CourseFolder
    _complete_phase(faculty_client, folder, CourseFolder.FINAL_PHASES)
    folder.status = FolderStatus.MID_APPROVED
    folder.save(update_fields=["status"])

    resp = faculty_client.post(reverse("submit_final", args=[course.pk]), follow=True)
    assert b"Final-term submitted" in resp.content
    folder.refresh_from_db()
    assert folder.status == FolderStatus.FINAL_SUBMITTED


@pytest.mark.django_db
def test_submit_clears_prior_flags(faculty_client, course):
    folder = course.folder
    from folders.models import CourseFolder
    _complete_phase(faculty_client, folder, CourseFolder.MID_PHASES)
    # Simulate a prior return: flag a mid item.
    flagged = folder.items.filter(phase="MID").first()
    flagged.is_flagged = True
    flagged.review_note = "fix this"
    flagged.save()

    faculty_client.post(reverse("submit_mid", args=[course.pk]))
    flagged.refresh_from_db()
    assert flagged.is_flagged is False
    assert flagged.review_note == ""


@pytest.mark.django_db
def test_other_faculty_cannot_submit(client, course):
    from django.contrib.auth import get_user_model
    other = get_user_model().objects.create_user(email="o@uiit.edu.pk", name="O")
    client.force_login(other)
    assert client.post(reverse("submit_mid", args=[course.pk])).status_code == 403


def test_submit_requires_post(faculty_client, course):
    assert faculty_client.get(reverse("submit_mid", args=[course.pk])).status_code == 405
