"""Folder lifecycle services (creation/seeding live here, not in views)."""

from io import BytesIO

from django.core.files.base import ContentFile
from django.db import transaction

from audit.services import record

from .models import (
    ChecklistItem,
    ChecklistTemplateItem,
    CourseFolder,
    ItemFile,
    ItemStatus,
    SampleKind,
)

THUMBNAIL_SIZE = (400, 400)


@transaction.atomic
def get_or_create_folder(course):
    """Return the course's folder, creating and seeding it on first use.

    Seeding copies every ChecklistTemplateItem into the folder as a
    ChecklistItem (denormalised so the folder can later diverge from the
    template). Idempotent: items are only seeded when the folder is created.
    """
    folder, created = CourseFolder.objects.get_or_create(course=course)
    if created:
        items = [
            ChecklistItem(
                folder=folder,
                template=t,
                order=t.order,
                title=t.title,
                phase=t.phase,
                is_required=t.is_required,
                allows_samples=t.allows_samples,
                is_removable=t.is_removable,
            )
            for t in ChecklistTemplateItem.objects.all()
        ]
        ChecklistItem.objects.bulk_create(items)
    return folder


def save_item_file(item, uploaded_file, user, sample_kind=SampleKind.NONE):
    """Persist an uploaded file to private storage and mark the item available.

    The storage backend places it under course/<id>/item/<id>/ keys (see
    ItemFile.upload_to). Thumbnail generation is handled separately.
    """
    item_file = ItemFile(
        item=item,
        sample_kind=sample_kind,
        file=uploaded_file,
        original_name=uploaded_file.name[:255],
        size_bytes=getattr(uploaded_file, "size", 0) or 0,
        content_type=getattr(uploaded_file, "content_type", "") or "",
        uploaded_by=user,
    )
    item_file.save()

    generate_thumbnail(item_file)
    recompute_item_status(item)
    record(user, "file_upload", item_file, item=item.id,
           name=item_file.original_name, sample_kind=item_file.sample_kind)
    return item_file


def recompute_item_status(item):
    """Set an item's status from its evidence (N/A is left untouched).

    AVAILABLE when complete: sample items need all W/A/B groups; ordinary items
    need at least one file. PENDING otherwise.
    """
    if item.status == ItemStatus.NOT_APPLICABLE:
        return
    new_status = ItemStatus.AVAILABLE if item.is_satisfied else ItemStatus.PENDING
    if item.status != new_status:
        item.status = new_status
        item.save(update_fields=["status"])


def generate_thumbnail(item_file):
    """Create a small JPEG thumbnail for image uploads (no-op otherwise)."""
    if item_file.content_type not in ItemFile.IMAGE_CONTENT_TYPES:
        return None

    from PIL import Image

    try:
        item_file.file.open("rb")
        image = Image.open(item_file.file)
        image = image.convert("RGB")
        image.thumbnail(THUMBNAIL_SIZE)
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=85)
    except Exception:  # noqa: BLE001 - never let a bad thumbnail block the upload
        return None
    finally:
        item_file.file.close()

    base = item_file.original_name.rsplit(".", 1)[0]
    item_file.thumbnail.save(f"{base}.jpg", ContentFile(buffer.getvalue()), save=True)
    return item_file.thumbnail


def delete_item(item):
    """Remove a checklist item together with its files' storage objects.

    item.delete() cascades the ItemFile rows, but the physical files (and
    thumbnails) live in storage and must be deleted explicitly — otherwise
    they are orphaned on disk/S3 forever.
    """
    for item_file in item.files.all():
        item_file.file.delete(save=False)
        if item_file.thumbnail:
            item_file.thumbnail.delete(save=False)
    item.delete()


def delete_item_file(item_file, user=None):
    """Delete a file (and its thumbnail) from storage and the database, and
    reset the item to pending if it has no files left."""
    item = item_file.item
    name = item_file.original_name
    # Remove the storage objects, then the row.
    item_file.file.delete(save=False)
    if item_file.thumbnail:
        item_file.thumbnail.delete(save=False)
    item_file.delete()

    recompute_item_status(item)
    record(user, "file_delete", item, name=name)
