"""Certificate eligibility and issuance."""

from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify

from audit.services import record
from folders.models import FolderStatus, ItemStatus

from .models import Certificate
from .pdf import render_pdf


class CertificationError(Exception):
    """Raised when a folder is not eligible to be certified."""


def can_certify(folder):
    """Both phases approved and every required, applicable item is available."""
    if folder.status not in (FolderStatus.FINAL_APPROVED, FolderStatus.CERTIFIED):
        return False
    for item in folder.items.all():
        if (
            item.is_required
            and item.status != ItemStatus.NOT_APPLICABLE
            and item.status != ItemStatus.AVAILABLE
        ):
            return False
    return True


def build_certificate_context(folder, issued_by=None, issued_at=None):
    items = list(folder.items.order_by("order", "id"))
    half = (len(items) + 1) // 2
    left, right = items[:half], items[half:]
    rows = [(left[i], right[i] if i < len(right) else None) for i in range(half)]
    return {
        "course": folder.course,
        "term": folder.course.term,
        "folder": folder,
        "rows": rows,
        "issued_by_name": issued_by.name if issued_by else "",
        "issued_at": issued_at or timezone.now(),
    }


def render_certificate_pdf(folder, issued_by=None, issued_at=None):
    html = render_to_string(
        "review/certificate.html",
        build_certificate_context(folder, issued_by, issued_at),
    )
    return render_pdf(html)


def issue_certificate(folder, user):
    """Generate, store, and record the certificate; mark the folder certified."""
    if folder.status == FolderStatus.CERTIFIED and hasattr(folder, "certificate"):
        return folder.certificate
    if folder.status != FolderStatus.FINAL_APPROVED:
        raise CertificationError("Both phases must be approved before certifying.")
    if not can_certify(folder):
        raise CertificationError(
            "Every required, applicable item must be available before certifying."
        )

    issued_at = timezone.now()
    pdf_bytes = render_certificate_pdf(folder, issued_by=user, issued_at=issued_at)

    course = folder.course
    filename = f"certificate-{slugify(course.code)}-{slugify(course.section)}.pdf"
    certificate = Certificate(folder=folder, issued_by=user)
    certificate.pdf.save(filename, ContentFile(pdf_bytes), save=False)
    certificate.save()

    folder.status = FolderStatus.CERTIFIED
    folder.certified_at = issued_at
    folder.save(update_fields=["status", "certified_at"])
    record(user, "issue_certificate", folder, course=course.id)
    return certificate
