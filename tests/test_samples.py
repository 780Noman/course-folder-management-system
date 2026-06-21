"""W/A/B sample grouping, per-group upload, and completeness (Phase 5)."""

import io

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


@pytest.fixture
def sample_item(course):
    # Order 21 = "Mid Exam (W,A,B)", a required sample item.
    return course.folder.items.get(order=21)


def _pdf(name="x.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 data", content_type="application/pdf")


# --- Task 1: grouping ------------------------------------------------------

@pytest.mark.django_db
def test_sample_groups_buckets_files(sample_item, faculty_user):
    ItemFile.objects.create(item=sample_item, sample_kind=SampleKind.WORST,
                            file=_pdf("w.pdf"), original_name="w.pdf",
                            content_type="application/pdf", uploaded_by=faculty_user)
    ItemFile.objects.create(item=sample_item, sample_kind=SampleKind.BEST,
                            file=_pdf("b.pdf"), original_name="b.pdf",
                            content_type="application/pdf", uploaded_by=faculty_user)

    groups = {g["kind"]: g for g in sample_item.sample_groups()}
    assert [g["label"] for g in sample_item.sample_groups()] == ["Worst", "Average", "Best"]
    assert len(groups[SampleKind.WORST]["files"]) == 1
    assert len(groups[SampleKind.AVERAGE]["files"]) == 0
    assert len(groups[SampleKind.BEST]["files"]) == 1


@pytest.mark.django_db
def test_folder_view_shows_three_groups_for_sample_item(faculty_client, course):
    resp = faculty_client.get(reverse("folder_detail", args=[course.pk]))
    content = resp.content.decode()
    assert "Worst" in content and "Average" in content and "Best" in content


# --- Task 2: upload into a specific group ----------------------------------

@pytest.mark.django_db
def test_upload_into_named_group(faculty_client, sample_item):
    faculty_client.post(
        reverse("file_upload", args=[sample_item.pk]),
        {"file": _pdf("avg.pdf"), "sample_kind": SampleKind.AVERAGE},
    )
    f = ItemFile.objects.get(item=sample_item)
    assert f.sample_kind == SampleKind.AVERAGE


@pytest.mark.django_db
def test_sample_item_requires_group_choice(faculty_client, sample_item):
    resp = faculty_client.post(
        reverse("file_upload", args=[sample_item.pk]), {"file": _pdf()}, follow=True
    )
    assert b"Choose a sample group" in resp.content
    assert ItemFile.objects.filter(item=sample_item).count() == 0


@pytest.mark.django_db
def test_invalid_group_rejected(faculty_client, sample_item):
    resp = faculty_client.post(
        reverse("file_upload", args=[sample_item.pk]),
        {"file": _pdf(), "sample_kind": "BOGUS"}, follow=True,
    )
    assert b"Choose a sample group" in resp.content
    assert ItemFile.objects.filter(item=sample_item).count() == 0


@pytest.mark.django_db
def test_non_sample_item_ignores_group(faculty_client, course):
    plain = course.folder.items.get(order=1)  # Academic Calendar, no samples
    faculty_client.post(
        reverse("file_upload", args=[plain.pk]),
        {"file": _pdf(), "sample_kind": SampleKind.BEST},  # should be ignored
    )
    f = ItemFile.objects.get(item=plain)
    assert f.sample_kind == SampleKind.NONE


# --- Task 3: completeness accounts for required sample groups ---------------

def _upload_group(faculty_client, item, kind, name):
    faculty_client.post(
        reverse("file_upload", args=[item.pk]),
        {"file": _pdf(name), "sample_kind": kind},
    )


@pytest.mark.django_db
def test_sample_item_incomplete_until_all_three_groups(faculty_client, sample_item):
    _upload_group(faculty_client, sample_item, SampleKind.WORST, "w.pdf")
    sample_item.refresh_from_db()
    assert sample_item.is_satisfied is False
    assert sample_item.status == ItemStatus.PENDING  # not yet complete

    _upload_group(faculty_client, sample_item, SampleKind.AVERAGE, "a.pdf")
    _upload_group(faculty_client, sample_item, SampleKind.BEST, "b.pdf")
    sample_item.refresh_from_db()
    assert sample_item.is_satisfied is True
    assert sample_item.status == ItemStatus.AVAILABLE


@pytest.mark.django_db
def test_removing_a_group_makes_item_incomplete_again(faculty_client, sample_item):
    for kind, name in [(SampleKind.WORST, "w.pdf"), (SampleKind.AVERAGE, "a.pdf"),
                       (SampleKind.BEST, "b.pdf")]:
        _upload_group(faculty_client, sample_item, kind, name)
    sample_item.refresh_from_db()
    assert sample_item.status == ItemStatus.AVAILABLE

    best = ItemFile.objects.get(item=sample_item, sample_kind=SampleKind.BEST)
    faculty_client.post(reverse("file_delete", args=[best.pk]))
    sample_item.refresh_from_db()
    assert sample_item.status == ItemStatus.PENDING


@pytest.mark.django_db
def test_sample_item_counts_toward_phase_progress_only_when_complete(faculty_client, course, sample_item):
    folder = course.folder
    mid_items = folder.items.filter(phase="MID")

    before = folder.progress(mid_items)["done"]
    _upload_group(faculty_client, sample_item, SampleKind.WORST, "w.pdf")
    after_partial = folder.progress(folder.items.filter(phase="MID"))["done"]
    assert after_partial == before  # partial samples don't count

    _upload_group(faculty_client, sample_item, SampleKind.AVERAGE, "a.pdf")
    _upload_group(faculty_client, sample_item, SampleKind.BEST, "b.pdf")
    after_full = folder.progress(folder.items.filter(phase="MID"))["done"]
    assert after_full == before + 1  # now it counts
