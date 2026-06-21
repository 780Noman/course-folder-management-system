"""Create and seed a course folder as soon as a course is created."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from academics.models import Course

from .services import get_or_create_folder


@receiver(post_save, sender=Course, dispatch_uid="create_course_folder")
def create_course_folder(sender, instance, created, **kwargs):
    if created:
        get_or_create_folder(instance)
