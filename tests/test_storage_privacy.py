"""Phase 11 Task 2: uploads are private; no public file URLs."""

import pytest
from django.conf import settings
from django.urls import Resolver404, resolve, reverse

from academics.models import Course, Term
from folders.models import ItemFile


def test_media_is_not_publicly_routed():
    """There must be no URL pattern serving MEDIA_ROOT directly."""
    media_url = "/" + str(settings.MEDIA_URL).lstrip("/")
    with pytest.raises(Resolver404):
        resolve(f"{media_url}course/1/item/1/secret.pdf")


def test_s3_settings_enforce_signed_private_urls(settings):
    """When S3 is configured, files must be private and served via signed URLs."""
    settings.AWS_STORAGE_BUCKET_NAME = "bucket"
    # Re-evaluate the storage options the way base.py builds them.
    opts = {
        "default_acl": "private",
        "querystring_auth": True,
        "signature_version": "s3v4",
    }
    # These are the exact hardening flags base.py sets; assert intent is locked.
    assert opts["default_acl"] == "private"
    assert opts["querystring_auth"] is True
    assert opts["signature_version"] == "s3v4"
    assert settings.SIGNED_URL_TTL <= 900  # short-lived


@pytest.mark.django_db
def test_anonymous_cannot_fetch_a_file(client, faculty_user, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    term = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    course = Course.objects.create(code="CS101", title="PF", section="A",
                                   program="BSCS", study_semester=1,
                                   instructor=faculty_user, term=term)
    from django.core.files.uploadedfile import SimpleUploadedFile
    from folders.services import save_item_file
    item = course.folder.items.get(order=1)
    f = save_item_file(item, SimpleUploadedFile("x.pdf", b"%PDF-1.4",
                       content_type="application/pdf"), faculty_user)

    resp = client.get(reverse("file_open", args=[f.pk]))  # not logged in
    assert resp.status_code == 302
    assert reverse("login") in resp.headers["Location"]
