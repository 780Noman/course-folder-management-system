"""Certificate generation: template, gating, issuance, download (Phase 7)."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from academics.models import Course, Term
from folders.models import FolderStatus, ItemStatus, SampleKind
from review import certificates


@pytest.fixture(autouse=True)
def _media_to_tmp(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.fixture
def course(db, faculty_user):
    term = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    return Course.objects.create(
        code="CS101", title="Programming Fundamentals", section="A", program="BSCS",
        study_semester=1, instructor=faculty_user, term=term,
    )


def _make_all_required_available(folder):
    """Bypass the UI: mark every required item available (samples included)."""
    for item in folder.items.all():
        if item.is_required:
            item.status = ItemStatus.AVAILABLE
            item.save(update_fields=["status"])


# --- Task 1: template + context --------------------------------------------

@pytest.mark.django_db
def test_context_splits_items_into_two_columns(course):
    ctx = certificates.build_certificate_context(course.folder)
    # 28 seeded items -> 14 rows, each with a left and right item.
    assert len(ctx["rows"]) == 14
    assert ctx["rows"][0][0].order == 1
    assert ctx["rows"][0][1].order == 15
    assert all(left is not None for left, _ in ctx["rows"])


@pytest.mark.django_db
def test_certificate_renders_to_pdf(course):
    pdf = certificates.render_certificate_pdf(course.folder)
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 1000


# --- Task 2 + 3: gating, issuance, storage, download -----------------------

@pytest.mark.django_db
def test_cannot_certify_unless_final_approved(course):
    assert certificates.can_certify(course.folder) is False  # DRAFT
    with pytest.raises(certificates.CertificationError):
        certificates.issue_certificate(course.folder, course.instructor)


@pytest.mark.django_db
def test_issue_blocked_when_a_required_item_missing(admin_client, course):
    folder = course.folder
    _make_all_required_available(folder)
    # Approved, but then a required item goes missing -> issuance must be blocked.
    folder.status = FolderStatus.FINAL_APPROVED
    folder.save(update_fields=["status"])
    missing = folder.items.filter(is_required=True).first()
    missing.status = ItemStatus.PENDING
    missing.save(update_fields=["status"])

    resp = admin_client.post(reverse("certify", args=[course.pk]), follow=True)
    assert b"must be available" in resp.content
    folder.refresh_from_db()
    assert folder.status == FolderStatus.FINAL_APPROVED  # unchanged
    assert not hasattr(folder, "certificate")


@pytest.mark.django_db
def test_admin_issues_certificate_and_it_is_stored(admin_client, course, admin_user):
    from review.models import Certificate

    folder = course.folder
    _make_all_required_available(folder)
    folder.status = FolderStatus.FINAL_APPROVED
    folder.save(update_fields=["status"])

    resp = admin_client.post(reverse("certify", args=[course.pk]), follow=True)
    assert b"Certificate issued" in resp.content

    folder.refresh_from_db()
    assert folder.status == FolderStatus.CERTIFIED
    assert folder.certified_at is not None
    cert = Certificate.objects.get(folder=folder)
    assert cert.issued_by_id == admin_user.id
    assert cert.pdf.name.endswith(".pdf")
    cert.pdf.open("rb")
    assert cert.pdf.read(5) == b"%PDF-"
    cert.pdf.close()


@pytest.mark.django_db
def test_certify_is_admin_only(faculty_client, course):
    course.folder.status = FolderStatus.FINAL_APPROVED
    course.folder.save(update_fields=["status"])
    assert faculty_client.post(reverse("certify", args=[course.pk])).status_code == 403


@pytest.mark.django_db
def test_issue_is_logged(admin_client, course):
    from audit.models import AuditLog

    folder = course.folder
    _make_all_required_available(folder)
    folder.status = FolderStatus.FINAL_APPROVED
    folder.save(update_fields=["status"])
    admin_client.post(reverse("certify", args=[course.pk]))
    assert AuditLog.objects.filter(action="issue_certificate").exists()


@pytest.mark.django_db
def test_owner_downloads_certificate(faculty_client, course):
    folder = course.folder
    _make_all_required_available(folder)
    folder.status = FolderStatus.FINAL_APPROVED
    folder.save(update_fields=["status"])
    certificates.issue_certificate(folder, course.instructor)

    resp = faculty_client.get(reverse("certificate_download", args=[course.pk]))
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert b"".join(resp.streaming_content)[:5] == b"%PDF-"


@pytest.mark.django_db
def test_other_faculty_cannot_download(client, course):
    from django.contrib.auth import get_user_model

    folder = course.folder
    _make_all_required_available(folder)
    folder.status = FolderStatus.FINAL_APPROVED
    folder.save(update_fields=["status"])
    certificates.issue_certificate(folder, course.instructor)

    other = get_user_model().objects.create_user(email="o@uiit.edu.pk", name="O")
    client.force_login(other)
    assert client.get(reverse("certificate_download", args=[course.pk])).status_code == 403


@pytest.mark.django_db
def test_download_404_when_not_issued(faculty_client, course):
    assert faculty_client.get(reverse("certificate_download", args=[course.pk])).status_code == 404


# --- Issuance robustness (transaction + idempotency) ------------------------

@pytest.mark.django_db
def test_issue_twice_returns_same_certificate(course, admin_user):
    from review.models import Certificate

    folder = course.folder
    _make_all_required_available(folder)
    folder.status = FolderStatus.FINAL_APPROVED
    folder.save(update_fields=["status"])

    first = certificates.issue_certificate(folder, admin_user)
    folder.refresh_from_db()
    second = certificates.issue_certificate(folder, admin_user)
    assert first.pk == second.pk
    assert Certificate.objects.filter(folder=folder).count() == 1


@pytest.mark.django_db
def test_retry_repairs_interrupted_issuance(course, admin_user):
    """Certificate row exists but the folder was never marked certified (a
    crash between the two writes before the fix). A retry must repair the
    folder instead of raising IntegrityError on the OneToOne."""
    from django.core.files.base import ContentFile

    from review.models import Certificate

    folder = course.folder
    _make_all_required_available(folder)
    folder.status = FolderStatus.FINAL_APPROVED
    folder.save(update_fields=["status"])

    orphan = Certificate(folder=folder, issued_by=admin_user)
    orphan.pdf.save("orphan.pdf", ContentFile(b"%PDF- fake"), save=False)
    orphan.save()

    cert = certificates.issue_certificate(folder, admin_user)
    assert cert.pk == orphan.pk
    folder.refresh_from_db()
    assert folder.status == FolderStatus.CERTIFIED
    assert folder.certified_at is not None


@pytest.mark.django_db
def test_failed_issuance_leaves_no_partial_state(course, admin_user, monkeypatch):
    """If the audit write (last step in the transaction) blows up, neither the
    certificate row nor the folder status change may survive."""
    from review.models import Certificate

    folder = course.folder
    _make_all_required_available(folder)
    folder.status = FolderStatus.FINAL_APPROVED
    folder.save(update_fields=["status"])

    def _boom(*args, **kwargs):
        raise RuntimeError("db hiccup")

    monkeypatch.setattr(certificates, "record", _boom)
    with pytest.raises(RuntimeError):
        certificates.issue_certificate(folder, admin_user)

    folder.refresh_from_db()
    assert folder.status == FolderStatus.FINAL_APPROVED
    assert not Certificate.objects.filter(folder=folder).exists()

    # And a retry after the hiccup succeeds cleanly.
    monkeypatch.undo()
    cert = certificates.issue_certificate(folder, admin_user)
    folder.refresh_from_db()
    assert folder.status == FolderStatus.CERTIFIED
    assert Certificate.objects.get(folder=folder) == cert

