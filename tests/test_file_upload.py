"""Uploads land in private storage under course/item keys (Task 1)."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from academics.models import Course, Term
from folders.models import ItemFile, ItemStatus, SampleKind


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


@pytest.mark.django_db
def test_upload_stores_under_course_item_key_and_marks_available(faculty_client, course):
    item = course.folder.items.get(order=1)  # Academic Calendar
    upload = SimpleUploadedFile(
        "calendar.pdf", b"%PDF-1.4 fake pdf bytes", content_type="application/pdf"
    )

    resp = faculty_client.post(reverse("file_upload", args=[item.pk]), {"file": upload})
    assert resp.status_code == 302

    f = ItemFile.objects.get(item=item)
    assert f.file.name == f"course/{course.pk}/item/{item.pk}/calendar.pdf"
    assert f.original_name == "calendar.pdf"
    assert f.size_bytes > 0
    assert f.content_type == "application/pdf"
    assert f.sample_kind == SampleKind.NONE
    assert f.uploaded_by_id == course.instructor_id

    item.refresh_from_db()
    assert item.status == ItemStatus.AVAILABLE


@pytest.mark.django_db
def test_other_faculty_cannot_upload(client, course):
    from django.contrib.auth import get_user_model

    other = get_user_model().objects.create_user(
        email="other@uiit.edu.pk", name="Other", password="StrongPass123!"
    )
    client.force_login(other)
    item = course.folder.items.get(order=1)
    upload = SimpleUploadedFile("x.pdf", b"%PDF-1.4", content_type="application/pdf")
    resp = client.post(reverse("file_upload", args=[item.pk]), {"file": upload})
    assert resp.status_code == 403
    assert ItemFile.objects.count() == 0


def test_upload_requires_post(faculty_client, course):
    item = course.folder.items.get(order=1)
    assert faculty_client.get(reverse("file_upload", args=[item.pk])).status_code == 405
