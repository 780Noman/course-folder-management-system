"""Image thumbnail generation on upload (Task 3)."""

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


def _png_bytes(size=(1000, 800)):
    buf = io.BytesIO()
    Image.new("RGB", size, "blue").save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.django_db
def test_thumbnail_created_for_image(faculty_client, item):
    upload = SimpleUploadedFile("scan.png", _png_bytes(), content_type="image/png")
    faculty_client.post(reverse("file_upload", args=[item.pk]), {"file": upload})

    f = ItemFile.objects.get(item=item)
    assert f.thumbnail.name
    assert "/thumb/" in f.thumbnail.name

    f.thumbnail.open("rb")
    thumb = Image.open(f.thumbnail)
    assert max(thumb.size) <= 400  # scaled down within the bounding box
    f.thumbnail.close()


@pytest.mark.django_db
def test_no_thumbnail_for_pdf(faculty_client, item):
    upload = SimpleUploadedFile("doc.pdf", b"%PDF-1.4 hello", content_type="application/pdf")
    faculty_client.post(reverse("file_upload", args=[item.pk]), {"file": upload})

    f = ItemFile.objects.get(item=item)
    assert not f.thumbnail
    assert f.is_image is False
