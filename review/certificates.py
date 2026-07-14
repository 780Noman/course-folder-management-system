"""Certificate eligibility and issuance."""

import base64
import logging
from functools import lru_cache
from io import BytesIO

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify

from audit.services import record
from folders.models import FolderStatus, ItemStatus

from .models import Certificate
from .pdf import render_pdf

logger = logging.getLogger(__name__)

_LOGO_BOX = 130  # px; logos are downscaled to fit this box before embedding


@lru_cache(maxsize=8)
def _logo_data_uri(static_rel):
    """Return a base64 PNG data URI for a static logo, downscaled to a small box.

    Embedding the image inline (rather than a URL) lets both PDF engines
    (WeasyPrint and xhtml2pdf) render it without any base_url / link_callback.
    Certificates must issue even if a branding asset is missing, so any failure
    degrades to an empty string and the template simply omits that logo.
    """
    try:
        path = finders.find(static_rel) or str(settings.BASE_DIR / "static" / static_rel)
        from PIL import Image

        with Image.open(path) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            img.thumbnail((_LOGO_BOX, _LOGO_BOX))
            buf = BytesIO()
            img.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:  # noqa: BLE001 - branding must never block certificate issuance
        logger.warning("Certificate logo %r unavailable; omitting it.", static_rel)
        return ""


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
        "uiit_logo": _logo_data_uri("img/uiit-logo.jpg"),
        "arid_logo": _logo_data_uri("img/arid-logo.png"),
    }


def render_certificate_pdf(folder, issued_by=None, issued_at=None):
    html = render_to_string(
        "review/certificate.html",
        build_certificate_context(folder, issued_by, issued_at),
    )
    return render_pdf(html)


def issue_certificate(folder, user):
    """Generate, store, and record the certificate; mark the folder certified."""
    # Idempotent on the certificate itself (OneToOne), not the folder status:
    # if an earlier attempt saved the certificate but crashed before marking
    # the folder, retrying must repair rather than hit an IntegrityError.
    existing = Certificate.objects.filter(folder=folder).first()
    if existing:
        if folder.status != FolderStatus.CERTIFIED:
            folder.status = FolderStatus.CERTIFIED
            folder.certified_at = folder.certified_at or existing.issued_at
            folder.save(update_fields=["status", "certified_at"])
        return existing
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
    # All-or-nothing: certificate row, folder status, and audit entry commit
    # together (the PDF was already rendered above, outside the transaction).
    with transaction.atomic():
        certificate.pdf.save(filename, ContentFile(pdf_bytes), save=False)
        certificate.save()
        folder.status = FolderStatus.CERTIFIED
        folder.certified_at = issued_at
        folder.save(update_fields=["status", "certified_at"])
        record(user, "issue_certificate", folder, course=course.id)
    return certificate
