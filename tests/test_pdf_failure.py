"""PDF engine failure must surface as a friendly error, never a 500."""

import pytest
from django.urls import reverse

from folders.models import FolderStatus, ItemStatus
from review import pdf as pdf_module
from review.pdf import PdfRenderError, render_pdf


@pytest.fixture(autouse=True)
def _media_to_tmp(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.fixture
def _all_engines_broken(monkeypatch):
    def _boom(html, base_url):
        raise RuntimeError("engine exploded")

    monkeypatch.setattr(pdf_module, "_weasyprint", _boom)
    monkeypatch.setattr(pdf_module, "_xhtml2pdf", _boom)


def test_render_pdf_raises_typed_error(settings, _all_engines_broken):
    settings.PDF_ENGINE = "auto"
    with pytest.raises(PdfRenderError):
        render_pdf("<p>x</p>")
    settings.PDF_ENGINE = "xhtml2pdf"
    with pytest.raises(PdfRenderError):
        render_pdf("<p>x</p>")


@pytest.mark.django_db
def test_certify_survives_pdf_failure(admin_client, faculty_user, _all_engines_broken):
    from academics.models import Course, Term
    from review.models import Certificate

    term = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    course = Course.objects.create(
        code="CS101", title="Programming Fundamentals", section="A", program="BSCS",
        study_semester=1, instructor=faculty_user, term=term,
    )
    folder = course.folder
    folder.items.filter(is_required=True).update(status=ItemStatus.AVAILABLE)
    folder.status = FolderStatus.FINAL_APPROVED
    folder.save(update_fields=["status"])

    resp = admin_client.post(reverse("certify", args=[course.pk]), follow=True)
    assert resp.status_code == 200  # message page, not a 500
    assert b"could not be generated" in resp.content

    folder.refresh_from_db()
    assert folder.status == FolderStatus.FINAL_APPROVED  # unchanged
    assert not Certificate.objects.filter(folder=folder).exists()


@pytest.mark.django_db
def test_report_pdf_export_survives_pdf_failure(admin_client, _all_engines_broken):
    resp = admin_client.get(reverse("report_export_pdf"), follow=True)
    assert resp.status_code == 200  # redirected back to the report page
    assert b"could not be generated" in resp.content
