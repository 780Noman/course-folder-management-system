"""Make Course.credit_hours a flexible string ("3" or "4(3-3)").

Converts the existing integer column without risking a DB-specific cast: a temp
text column is added, values are copied as strings, then the old column is
dropped and the temp renamed into place.
"""

import re

import django.core.validators
from django.db import migrations, models


def int_to_text(apps, schema_editor):
    Course = apps.get_model("academics", "Course")
    for course in Course.objects.all().iterator():
        course.credit_hours_tmp = str(course.credit_hours)
        course.save(update_fields=["credit_hours_tmp"])


def text_to_int(apps, schema_editor):
    """Reverse: keep the leading total for the integer round-trip."""
    Course = apps.get_model("academics", "Course")
    for course in Course.objects.all().iterator():
        match = re.match(r"^(\d+)", course.credit_hours_tmp or "3")
        course.credit_hours = int(match.group(1)) if match else 3
        course.save(update_fields=["credit_hours"])


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0002_course"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="credit_hours_tmp",
            field=models.CharField(default="3", max_length=12),
        ),
        migrations.RunPython(int_to_text, text_to_int),
        migrations.RemoveField(model_name="course", name="credit_hours"),
        migrations.RenameField(
            model_name="course",
            old_name="credit_hours_tmp",
            new_name="credit_hours",
        ),
        migrations.AlterField(
            model_name="course",
            name="credit_hours",
            field=models.CharField(
                default="3",
                help_text="e.g. 3 or 4(3-3) — total credits with (theory-lab).",
                max_length=12,
                validators=[
                    django.core.validators.RegexValidator(
                        message=(
                            "Use a number like 3, or the format 4(3-3) — "
                            "total(theory-lab)."
                        ),
                        regex="^\\d{1,2}(\\(\\d{1,2}-\\d{1,2}\\))?$",
                    )
                ],
            ),
        ),
    ]
