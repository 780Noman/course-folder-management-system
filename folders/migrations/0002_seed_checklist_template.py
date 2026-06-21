"""Seed the 28 official Course Folder Review checklist items.

Source of truth: docs/Updated Checklist-Course Assessment.docx (Sr# 1–28 and
the W/A/B markings are verbatim from that file). Phase tags, required/optional,
and count-variable (removable) flags follow the agreed mapping documented in
docs/DATA_MODEL.md. To change the official checklist, edit ITEMS here and add a
follow-up migration.
"""

from django.db import migrations

GENERAL, MID, FINAL = "GENERAL", "MID", "FINAL"

# (order, title, phase, is_required, allows_samples, is_removable)
ITEMS = [
    (1, "Academic Calendar", GENERAL, True, False, False),
    (2, "Timetable", GENERAL, True, False, False),
    (3, "Course Description", GENERAL, True, False, False),
    (4, "Course Log", GENERAL, True, False, False),
    (5, "Course Monitoring Form", GENERAL, True, False, False),
    (6, "Attendance Record", GENERAL, True, False, False),
    (7, "Lectures Notes/Lab Manual", GENERAL, True, False, False),
    (8, "Lab Tasks/Evaluation", GENERAL, True, False, False),
    (9, "Marks Distribution", GENERAL, True, False, False),
    (10, "Grading Model", GENERAL, True, False, False),
    # Mid-term
    (11, "Quizzes- Paper 1 (W,A,B)", MID, True, True, True),
    (12, "Quizzes- Paper 2 (W,A,B)", MID, True, True, True),
    (15, "Assignment 1 (W,A,B)", MID, True, True, True),
    (16, "Assignment 2 (W,A,B)", MID, True, True, True),
    (19, "Mid Question Paper", MID, True, False, False),
    (20, "Mid Solution", MID, True, False, False),
    (21, "Mid Exam (W,A,B)", MID, True, True, False),
    # Final-term
    (13, "Quizzes- Paper 3 (W,A,B)", FINAL, False, True, True),
    (14, "Quizzes- Paper 4 (W,A,B)", FINAL, False, True, True),
    (17, "Assignment 3 (W,A,B)", FINAL, False, True, True),
    (18, "Assignment 4 (W,A,B)", FINAL, False, True, True),
    (22, "Final Exam Question Paper", FINAL, True, False, False),
    (23, "Final Exam Solution", FINAL, True, False, False),
    (24, "Final Exam (W,A,B)", FINAL, True, True, False),
    (25, "Projects (If any)", FINAL, False, False, False),
    (26, "Final Results (Grade Based)", FINAL, True, False, False),
    (27, "Final Results (OBE Based)", FINAL, True, False, False),
    (28, "Outcomes Assessment", FINAL, True, False, False),
]


def seed(apps, schema_editor):
    Template = apps.get_model("folders", "ChecklistTemplateItem")
    for order, title, phase, required, samples, removable in ITEMS:
        Template.objects.update_or_create(
            order=order,
            defaults={
                "title": title,
                "phase": phase,
                "is_required": required,
                "allows_samples": samples,
                "is_removable": removable,
            },
        )


def unseed(apps, schema_editor):
    Template = apps.get_model("folders", "ChecklistTemplateItem")
    Template.objects.filter(order__in=[i[0] for i in ITEMS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("folders", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
