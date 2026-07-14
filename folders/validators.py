"""Upload validation: extension whitelist, size cap, and content sniffing.

Validation is defence-in-depth: the file extension, declared content type, and
the actual leading bytes must all agree, and the size must be within the limit.
"""

from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "jpg", "jpeg", "png",
}

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",  # .doc
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.ms-powerpoint",  # .ppt
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    "application/vnd.ms-excel",  # .xls
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "image/jpeg",
    "image/png",
}

# Leading "magic" bytes expected for each extension. OOXML formats (docx/pptx/xlsx)
# are zip containers; legacy Office formats (doc/ppt/xls) are OLE2 compound files.
_OOXML = [b"PK\x03\x04"]
_OLE2 = [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"]
_MAGIC = {
    "pdf": [b"%PDF"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "docx": _OOXML,
    "pptx": _OOXML,
    "xlsx": _OOXML,
    "doc": _OLE2,
    "ppt": _OLE2,
    "xls": _OLE2,
}

_IMAGE_EXTS = {"png", "jpg", "jpeg"}


def _extension(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""


def validate_upload(uploaded_file):
    """Raise ValidationError if the upload is not an allowed, well-formed file."""
    ext = _extension(uploaded_file.name)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            "File type is not allowed. Allowed types: "
            "PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX, JPG, PNG."
        )

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if uploaded_file.size > max_bytes:
        raise ValidationError(f"File is too large (maximum {settings.MAX_UPLOAD_MB} MB).")

    content_type = (getattr(uploaded_file, "content_type", "") or "").lower()
    # Browsers sometimes send octet-stream for office docs; the magic-byte check
    # below is the real gate, so only reject clearly-wrong declared types.
    if (
        content_type
        and content_type != "application/octet-stream"
        and content_type not in ALLOWED_CONTENT_TYPES
    ):
        raise ValidationError("File content type is not allowed.")

    head = uploaded_file.read(8)
    uploaded_file.seek(0)
    signatures = _MAGIC.get(ext, [])
    if signatures and not any(head.startswith(sig) for sig in signatures):
        raise ValidationError("File contents do not match its extension.")

    if ext in _IMAGE_EXTS:
        from PIL import Image

        try:
            Image.open(uploaded_file).verify()
        except Exception as exc:  # noqa: BLE001 - any Pillow failure = invalid image
            raise ValidationError("The image file appears to be corrupt.") from exc
        finally:
            uploaded_file.seek(0)
