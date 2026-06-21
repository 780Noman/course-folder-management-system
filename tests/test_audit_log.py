"""Audit log records review-loop and file actions (Task 4)."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from academics.models import Course, Term
from audit.models import AuditLog
from folders.models import FolderStatus, ItemFile


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


def _pdf():
    return SimpleUploadedFile("x.pdf", b"%PDF-1.4 data", content_type="application/pdf")


@pytest.mark.django_db
def test_file_upload_and_delete_are_logged(faculty_client, course, faculty_user):
    item = course.folder.items.get(order=1)
    faculty_client.post(reverse("file_upload", args=[item.pk]), {"file": _pdf()})
    up = AuditLog.objects.filter(action="file_upload").first()
    assert up is not None and up.actor_id == faculty_user.id

    f = ItemFile.objects.get(item=item)
    faculty_client.post(reverse("file_delete", args=[f.pk]))
    assert AuditLog.objects.filter(action="file_delete").exists()


@pytest.mark.django_db
def test_approve_mid_is_logged(admin_client, course, admin_user):
    course.folder.status = FolderStatus.MID_SUBMITTED
    course.folder.save(update_fields=["status"])
    admin_client.post(reverse("review_action", args=[course.pk]), {"action": "approve"})

    entry = AuditLog.objects.filter(action="approve_mid").first()
    assert entry is not None
    assert entry.actor_id == admin_user.id
    assert entry.target_type == "CourseFolder"
    assert entry.metadata.get("course") == course.pk


@pytest.mark.django_db
def test_return_mid_is_logged(admin_client, course):
    course.folder.status = FolderStatus.MID_SUBMITTED
    course.folder.save(update_fields=["status"])
    item = course.folder.items.get(order=1)
    admin_client.post(
        reverse("review_action", args=[course.pk]),
        {"action": "return", "overall_note": "fix",
         f"flag_{item.pk}": "on", f"note_{item.pk}": "bad"},
    )
    assert AuditLog.objects.filter(action="return_mid").exists()
