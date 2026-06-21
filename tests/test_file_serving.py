"""Lazy, access-controlled file/thumbnail serving (Task 4)."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from academics.models import Course, Term
from folders.models import ItemFile


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
    Image.new("RGB", (300, 200), "green").save(buf, format="PNG")
    return buf.getvalue()


def _upload(faculty_client, course, name, data, ctype):
    item = course.folder.items.get(order=1)
    faculty_client.post(
        reverse("file_upload", args=[item.pk]),
        {"file": SimpleUploadedFile(name, data, content_type=ctype)},
    )
    return ItemFile.objects.get(item=item)


@pytest.mark.django_db
def test_owner_streams_file_locally(faculty_client, course):
    f = _upload(faculty_client, course, "doc.pdf", b"%PDF-1.4 data", "application/pdf")
    resp = faculty_client.get(reverse("file_open", args=[f.pk]))
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    streamed = b"".join(resp.streaming_content)
    assert streamed.startswith(b"%PDF")


@pytest.mark.django_db
def test_thumbnail_served(faculty_client, course):
    f = _upload(faculty_client, course, "scan.png", _png(), "image/png")
    resp = faculty_client.get(reverse("file_thumb", args=[f.pk]))
    assert resp.status_code == 200
    assert resp["Content-Type"] == "image/jpeg"


@pytest.mark.django_db
def test_other_faculty_cannot_open_file(client, course, faculty_client):
    f = _upload(faculty_client, course, "doc.pdf", b"%PDF-1.4", "application/pdf")
    from django.contrib.auth import get_user_model

    other = get_user_model().objects.create_user(email="o@uiit.edu.pk", name="O")
    client.force_login(other)
    assert client.get(reverse("file_open", args=[f.pk])).status_code == 403


@pytest.mark.django_db
def test_s3_mode_redirects_to_signed_url(faculty_client, course, settings, monkeypatch):
    f = _upload(faculty_client, course, "doc.pdf", b"%PDF-1.4", "application/pdf")
    settings.USE_S3 = True
    # Pretend the storage produced a signed URL for the field's .url.
    monkeypatch.setattr(
        type(f.file), "url",
        property(lambda self: "https://r2.example.com/signed?sig=abc"),
        raising=False,
    )
    resp = faculty_client.get(reverse("file_open", args=[f.pk]))
    assert resp.status_code == 302
    assert resp.headers["Location"].startswith("https://r2.example.com/signed")
