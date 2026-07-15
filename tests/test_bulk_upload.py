"""Multi-file upload per item (drives the folder bulk-upload panel).

`file_upload` accepts many files under the `file` field and saves each one
independently, so a single bad file never aborts the rest. The manual single-file
form keeps working unchanged.
"""

import pytest
from django.contrib.auth import get_user_model
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


def _pdf(name):
    return SimpleUploadedFile(name, b"%PDF-1.4 fake pdf bytes", content_type="application/pdf")


@pytest.mark.django_db
def test_multi_file_upload_to_plain_item(faculty_client, course):
    item = course.folder.items.get(order=1)  # Academic Calendar (plain)
    files = [_pdf("a.pdf"), _pdf("b.pdf"), _pdf("c.pdf")]

    resp = faculty_client.post(reverse("file_upload", args=[item.pk]), {"file": files})
    assert resp.status_code == 302

    stored = ItemFile.objects.filter(item=item)
    assert stored.count() == 3
    for f in stored:
        assert f.file.name.startswith(f"course/{course.pk}/item/{item.pk}/")
        assert f.sample_kind == SampleKind.NONE
    item.refresh_from_db()
    assert item.status == ItemStatus.AVAILABLE


@pytest.mark.django_db
def test_multi_file_upload_to_sample_group(faculty_client, course):
    item = course.folder.items.get(order=11)  # Quizzes- Paper 1 (W,A,B)
    assert item.allows_samples
    files = [_pdf("w1.pdf"), _pdf("w2.pdf")]

    resp = faculty_client.post(
        reverse("file_upload", args=[item.pk]),
        {"file": files, "sample_kind": SampleKind.WORST},
    )
    assert resp.status_code == 302

    stored = ItemFile.objects.filter(item=item)
    assert stored.count() == 2
    assert all(f.sample_kind == SampleKind.WORST for f in stored)


@pytest.mark.django_db
def test_partial_failure_saves_good_and_reports_bad(faculty_client, course):
    """A disallowed file must not abort the good ones; the error is surfaced."""
    item = course.folder.items.get(order=1)
    good = _pdf("good.pdf")
    bad = SimpleUploadedFile("notes.txt", b"hello world", content_type="text/plain")

    resp = faculty_client.post(
        reverse("file_upload", args=[item.pk]),
        {"file": [good, bad]},
        HTTP_HX_REQUEST="true",  # render the row so we can read the error text
    )
    assert resp.status_code == 200

    # The good file is saved; the bad one is rejected but did not abort the batch.
    assert ItemFile.objects.filter(item=item).count() == 1
    assert b"not uploaded" in resp.content
    assert b"notes.txt" in resp.content
    item.refresh_from_db()
    assert item.status == ItemStatus.AVAILABLE


@pytest.mark.django_db
def test_other_faculty_cannot_bulk_upload(client, course):
    other = get_user_model().objects.create_user(
        email="other@uiit.edu.pk", name="Other", password="StrongPass123!"
    )
    client.force_login(other)
    item = course.folder.items.get(order=1)
    resp = client.post(
        reverse("file_upload", args=[item.pk]), {"file": [_pdf("x.pdf"), _pdf("y.pdf")]}
    )
    assert resp.status_code == 403
    assert ItemFile.objects.count() == 0


@pytest.mark.django_db
def test_single_file_still_works(faculty_client, course):
    """Backward compatibility: the manual per-item form sends one file."""
    item = course.folder.items.get(order=2)
    resp = faculty_client.post(
        reverse("file_upload", args=[item.pk]), {"file": _pdf("one.pdf")}
    )
    assert resp.status_code == 302
    assert ItemFile.objects.filter(item=item).count() == 1


@pytest.mark.django_db
def test_bulk_items_report_existing_filenames(faculty_client, course):
    """The bulk panel gets existing filenames so it re-uploads only genuinely
    new files (skips exact duplicates) and never doubles a file."""
    url = reverse("folder_detail", args=[course.pk])

    entry = next(b for b in faculty_client.get(url).context["bulk_items"] if b["order"] == 1)
    assert entry["existing"] == []

    item = course.folder.items.get(order=1)
    faculty_client.post(reverse("file_upload", args=[item.pk]), {"file": _pdf("A.pdf")})
    entry = next(b for b in faculty_client.get(url).context["bulk_items"] if b["order"] == 1)
    assert entry["existing"] == ["a.pdf"]  # lowercased for case-insensitive matching

    # Sample item: existing names are reported per W/A/B group.
    sample = course.folder.items.get(order=11)
    faculty_client.post(
        reverse("file_upload", args=[sample.pk]),
        {"file": _pdf("w1.pdf"), "sample_kind": SampleKind.WORST},
    )
    s = next(b for b in faculty_client.get(url).context["bulk_items"] if b["order"] == 11)
    assert s["existing_groups"]["WORST"] == ["w1.pdf"]
    assert s["existing_groups"]["AVERAGE"] == []


@pytest.mark.django_db
def test_multi_file_manual_upload_appends(faculty_client, course):
    """Faculty can add several files to an item at once (manual multi-select),
    and adding more later appends rather than replacing."""
    item = course.folder.items.get(order=1)
    url = reverse("file_upload", args=[item.pk])

    faculty_client.post(url, {"file": [_pdf("one.pdf"), _pdf("two.pdf")]})
    assert ItemFile.objects.filter(item=item).count() == 2

    faculty_client.post(url, {"file": _pdf("three.pdf")})
    assert ItemFile.objects.filter(item=item).count() == 3


@pytest.mark.django_db
def test_sample_item_without_kind_is_rejected(faculty_client, course):
    item = course.folder.items.get(order=11)  # sample item
    resp = faculty_client.post(
        reverse("file_upload", args=[item.pk]), {"file": [_pdf("q.pdf")]}
    )
    assert resp.status_code == 302
    assert ItemFile.objects.filter(item=item).count() == 0
