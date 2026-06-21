"""Upload validation: extension, size, content sniffing (Task 2)."""

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
def item(db, faculty_user):
    term = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    course = Course.objects.create(
        code="CS101", title="PF", section="A", program="BSCS",
        study_semester=1, instructor=faculty_user, term=term,
    )
    return course.folder.items.get(order=1)


def _png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, format="PNG")
    return buf.getvalue()


def _upload(faculty_client, item, f):
    return faculty_client.post(reverse("file_upload", args=[item.pk]), {"file": f},
                               follow=True)


@pytest.mark.django_db
def test_disallowed_extension_rejected(faculty_client, item):
    bad = SimpleUploadedFile("hack.exe", b"MZ\x90\x00", content_type="application/octet-stream")
    resp = _upload(faculty_client, item, bad)
    assert b"not allowed" in resp.content
    assert ItemFile.objects.count() == 0


@pytest.mark.django_db
def test_extension_content_mismatch_rejected(faculty_client, item):
    # .pdf extension but the bytes are not a PDF.
    fake = SimpleUploadedFile("notreally.pdf", b"this is plain text",
                              content_type="application/pdf")
    resp = _upload(faculty_client, item, fake)
    assert b"do not match its extension" in resp.content
    assert ItemFile.objects.count() == 0


@pytest.mark.django_db
def test_oversized_file_rejected(faculty_client, item, settings):
    settings.MAX_UPLOAD_MB = 1
    big = SimpleUploadedFile("big.pdf", b"%PDF-1.4" + b"0" * (1_200_000),
                             content_type="application/pdf")
    resp = _upload(faculty_client, item, big)
    assert b"too large" in resp.content
    assert ItemFile.objects.count() == 0


@pytest.mark.django_db
def test_corrupt_image_rejected(faculty_client, item):
    fake_png = SimpleUploadedFile(
        "fake.png", b"\x89PNG\r\n\x1a\n" + b"garbage", content_type="image/png"
    )
    resp = _upload(faculty_client, item, fake_png)
    assert b"corrupt" in resp.content
    assert ItemFile.objects.count() == 0


@pytest.mark.django_db
def test_valid_png_accepted(faculty_client, item):
    good = SimpleUploadedFile("scan.png", _png_bytes(), content_type="image/png")
    resp = _upload(faculty_client, item, good)
    assert ItemFile.objects.filter(item=item).count() == 1
    assert b"Uploaded" in resp.content
