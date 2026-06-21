"""Review app models: the issued Course Folder Review Certificate."""

from django.conf import settings
from django.db import models


def certificate_path(instance, filename):
    return f"course/{instance.folder.course_id}/certificate/{filename}"


class Certificate(models.Model):
    """One generated certificate PDF per course folder (stored privately)."""

    folder = models.OneToOneField(
        "folders.CourseFolder", on_delete=models.CASCADE, related_name="certificate"
    )
    pdf = models.FileField(upload_to=certificate_path, max_length=500)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    issued_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Certificate: {self.folder.course}"
