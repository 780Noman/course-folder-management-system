"""Course folder, checklist, and uploaded files.

The official Course Folder Review checklist has 28 items. They are stored as
``ChecklistTemplateItem`` rows (seeded by a data migration) and copied into a
folder's ``ChecklistItem`` rows when a folder is created.
"""

from django.db import models


class Phase(models.TextChoices):
    """Which submission phase an item belongs to."""

    GENERAL = "GENERAL", "General"
    MID = "MID", "Mid-term"
    FINAL = "FINAL", "Final-term"


class ChecklistTemplateItem(models.Model):
    """A default checklist line used to seed each new course folder.

    ``order`` is the official Sr# (1–28) and drives the certificate layout;
    ``phase`` is the system's Mid/Final grouping for the faculty folder view.
    """

    order = models.PositiveSmallIntegerField(unique=True)
    title = models.CharField(max_length=200)
    phase = models.CharField(max_length=10, choices=Phase.choices)
    is_required = models.BooleanField(default=True)
    allows_samples = models.BooleanField(
        default=False, help_text="Item is graded as Worst/Average/Best samples."
    )
    is_removable = models.BooleanField(
        default=False,
        help_text="Count-variable item faculty may add/remove (e.g. extra quizzes).",
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.order}. {self.title}"


class FolderStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    MID_SUBMITTED = "MID_SUBMITTED", "Mid-term submitted"
    MID_APPROVED = "MID_APPROVED", "Mid-term approved"
    FINAL_SUBMITTED = "FINAL_SUBMITTED", "Final-term submitted"
    CERTIFIED = "CERTIFIED", "Certified"


class ItemStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    AVAILABLE = "AVAILABLE", "Available"
    NOT_APPLICABLE = "NOT_APPLICABLE", "Not applicable"


class CourseFolder(models.Model):
    """The checklist container for one course."""

    course = models.OneToOneField(
        "academics.Course", on_delete=models.CASCADE, related_name="folder"
    )
    status = models.CharField(
        max_length=20, choices=FolderStatus.choices, default=FolderStatus.DRAFT
    )
    mid_submitted_at = models.DateTimeField(null=True, blank=True)
    mid_approved_at = models.DateTimeField(null=True, blank=True)
    final_submitted_at = models.DateTimeField(null=True, blank=True)
    certified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # General setup items roll into the mid-term submission.
    MID_PHASES = (Phase.GENERAL, Phase.MID)
    FINAL_PHASES = (Phase.FINAL,)

    def __str__(self):
        return f"Folder: {self.course}"

    @staticmethod
    def progress(items):
        """Completeness over an iterable of ChecklistItems.

        Only required items count, and N/A items are excluded entirely (they
        are neither blocking nor counted). Returns done/total/percent.
        """
        required = [
            i for i in items
            if i.is_required and i.status != ItemStatus.NOT_APPLICABLE
        ]
        total = len(required)
        done = sum(1 for i in required if i.status == ItemStatus.AVAILABLE)
        percent = round(done / total * 100) if total else 0
        return {"done": done, "total": total, "percent": percent}

    def is_phase_complete(self, phases):
        """True when every required, applicable item in ``phases`` is available."""
        prog = self.progress(self.items.filter(phase__in=phases))
        return prog["total"] > 0 and prog["done"] == prog["total"]


class ChecklistItem(models.Model):
    """One checklist line within a folder, copied from a template item.

    Fields are denormalised from the template so faculty can add, remove, or
    mark items N/A without affecting the shared template.
    """

    folder = models.ForeignKey(
        CourseFolder, on_delete=models.CASCADE, related_name="items"
    )
    template = models.ForeignKey(
        ChecklistTemplateItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    order = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200)
    phase = models.CharField(max_length=10, choices=Phase.choices)
    is_required = models.BooleanField(default=True)
    allows_samples = models.BooleanField(default=False)
    is_removable = models.BooleanField(default=False)

    status = models.CharField(
        max_length=20, choices=ItemStatus.choices, default=ItemStatus.PENDING
    )
    na_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.title} ({self.folder.course})"
