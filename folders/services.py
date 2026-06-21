"""Folder lifecycle services (creation/seeding live here, not in views)."""

from django.db import transaction

from .models import ChecklistItem, ChecklistTemplateItem, CourseFolder


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
