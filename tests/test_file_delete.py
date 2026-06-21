"""Deleting files removes the storage object and resets the item (Task 5)."""

import io

import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from academics.models import Course, Term
from folders.models import ItemFile, ItemStatus


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


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (200, 150), "purple").save(buf, format="PNG")
    return buf.getvalue()


def _upload(faculty_client, item, name, data, ctype):
    faculty_client.post(
        reverse("file_upload", args=[item.pk]),
        {"file": SimpleUploadedFile(name, data, content_type=ctype)},
    )
    return ItemFile.objects.get(item=item, original_name=name)


@pytest.mark.django_db
def test_delete_removes_storage_object_and_row(faculty_client, course):
    item = course.folder.items.get(order=1)
    f = _upload(faculty_client, item, "scan.png", _png(), "image/png")
    file_key, thumb_key = f.file.name, f.thumbnail.name
    assert default_storage.exists(file_key)
    assert default_storage.exists(thumb_key)

    resp = faculty_client.post(reverse("file_delete", args=[f.pk]))
    assert resp.status_code == 302
    assert not ItemFile.objects.filter(pk=f.pk).exists()
    assert not default_storage.exists(file_key)      # file gone from storage
    assert not default_storage.exists(thumb_key)     # thumbnail gone too


@pytest.mark.django_db
def test_item_reverts_to_pending_when_last_file_deleted(faculty_client, course):
    item = course.folder.items.get(order=1)
    f = _upload(faculty_client, item, "doc.pdf", b"%PDF-1.4 data", "application/pdf")
    item.refresh_from_db()
    assert item.status == ItemStatus.AVAILABLE

    faculty_client.post(reverse("file_delete", args=[f.pk]))
    item.refresh_from_db()
    assert item.status == ItemStatus.PENDING


@pytest.mark.django_db
def test_item_stays_available_if_other_files_remain(faculty_client, course):
    item = course.folder.items.get(order=1)
    f1 = _upload(faculty_client, item, "a.pdf", b"%PDF-1.4 a", "application/pdf")
    _upload(faculty_client, item, "b.pdf", b"%PDF-1.4 b", "application/pdf")

    faculty_client.post(reverse("file_delete", args=[f1.pk]))
    item.refresh_from_db()
    assert item.status == ItemStatus.AVAILABLE


@pytest.mark.django_db
def test_other_faculty_cannot_delete(client, course, faculty_client):
    item = course.folder.items.get(order=1)
    f = _upload(faculty_client, item, "doc.pdf", b"%PDF-1.4", "application/pdf")
    from django.contrib.auth import get_user_model

    other = get_user_model().objects.create_user(email="o@uiit.edu.pk", name="O")
    client.force_login(other)
    resp = client.post(reverse("file_delete", args=[f.pk]))
    assert resp.status_code == 403
    assert ItemFile.objects.filter(pk=f.pk).exists()


def test_delete_requires_post(faculty_client, course):
    item = course.folder.items.get(order=1)
    f = _upload(faculty_client, item, "doc.pdf", b"%PDF-1.4", "application/pdf")
    assert faculty_client.get(reverse("file_delete", args=[f.pk])).status_code == 405
