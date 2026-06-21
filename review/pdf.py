"""HTML -> PDF rendering.

WeasyPrint is the production engine (best fidelity, needs GTK). On systems
without GTK (e.g. local Windows dev) it raises at render time, so we fall back
to the pure-Python xhtml2pdf. The engine is selectable via the PDF_ENGINE
setting ("auto" | "weasyprint" | "xhtml2pdf").
"""

import logging
from io import BytesIO

from django.conf import settings

logger = logging.getLogger(__name__)


def _weasyprint(html, base_url):
    from weasyprint import HTML

    return HTML(string=html, base_url=base_url).write_pdf()


def _xhtml2pdf(html, base_url):
    from xhtml2pdf import pisa

    buffer = BytesIO()
    result = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")
    if result.err:
        raise RuntimeError("xhtml2pdf failed to render the document.")
    return buffer.getvalue()


def render_pdf(html, base_url=None):
    engine = getattr(settings, "PDF_ENGINE", "auto")

    if engine == "weasyprint":
        return _weasyprint(html, base_url)
    if engine == "xhtml2pdf":
        return _xhtml2pdf(html, base_url)

    # auto: prefer WeasyPrint, fall back to xhtml2pdf if it can't run here.
    try:
        return _weasyprint(html, base_url)
    except Exception as exc:  # noqa: BLE001 - GTK/library issues, etc.
        logger.warning("WeasyPrint unavailable (%s); using xhtml2pdf.", exc)
        return _xhtml2pdf(html, base_url)
