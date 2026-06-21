"""Course folder views (faculty folder view + flexible items)."""

import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from academics.models import Course

from .models import ChecklistItem, CourseFolder, ItemStatus, Phase
from .services import get_or_create_folder

# Count-variable families faculty can grow/shrink to match the course.
FAMILIES = {
    "quiz": "Quizzes- Paper {n} (W,A,B)",
    "assignment": "Assignment {n} (W,A,B)",
}
_FAMILY_PREFIX = {"quiz": "Quizzes- Paper", "assignment": "Assignment"}


def _require_folder_access(request, course):
    """Faculty may open their own course folders; admins may open any."""
    user = request.user
    if not (user.is_admin or course.instructor_id == user.id):
        raise PermissionDenied


@login_required
def folder_detail(request, course_id):
    course = get_object_or_404(Course.objects.select_related("instructor", "term"),
                               pk=course_id)
    _require_folder_access(request, course)

    folder = get_or_create_folder(course)
    items = list(folder.items.all())  # ordered by (order, id); single query

    def section(label, phase, can_add):
        members = [i for i in items if i.phase == phase]
        return {
            "label": label,
            "phase": phase,
            "can_add": can_add,
            "items": members,
            "progress": CourseFolder.progress(members),
        }

    sections = [
        section("General", Phase.GENERAL, False),
        section("Mid-term", Phase.MID, True),
        section("Final-term", Phase.FINAL, True),
    ]
    overall = CourseFolder.progress(items)

    return render(
        request,
        "folders/folder_detail.html",
        {
            "course": course,
            "folder": folder,
            "sections": sections,
            "overall": overall,
            "add_kinds": [("quiz", "quiz"), ("assignment", "assignment")],
        },
    )


def _next_family_number(folder, prefix):
    """Next sequence number for a family, based on the max already present."""
    numbers = []
    for title in folder.items.filter(title__istartswith=prefix).values_list(
        "title", flat=True
    ):
        match = re.search(r"(\d+)", title)
        if match:
            numbers.append(int(match.group(1)))
    return (max(numbers) + 1) if numbers else 1


@login_required
@require_POST
def item_add(request, course_id):
    """Add a count-variable item (extra quiz/assignment) to a folder."""
    course = get_object_or_404(Course, pk=course_id)
    _require_folder_access(request, course)

    kind = request.POST.get("kind")
    phase = request.POST.get("phase")
    if kind not in FAMILIES or phase not in (Phase.MID, Phase.FINAL):
        messages.error(request, "Unknown item to add.")
        return redirect("folder_detail", course_id=course.pk)

    folder = get_or_create_folder(course)
    number = _next_family_number(folder, _FAMILY_PREFIX[kind])
    next_order = (folder.items.aggregate(m=Max("order"))["m"] or 0) + 1
    item = ChecklistItem.objects.create(
        folder=folder,
        template=None,
        order=next_order,
        title=FAMILIES[kind].format(n=number),
        phase=phase,
        is_required=False,   # extras beyond the standard set are optional
        allows_samples=True,
        is_removable=True,
        status=ItemStatus.PENDING,
    )
    messages.success(request, f"Added “{item.title}”.")
    return redirect("folder_detail", course_id=course.pk)


@login_required
@require_POST
def item_remove(request, item_id):
    """Remove a count-variable item. Core checklist items cannot be removed."""
    item = get_object_or_404(
        ChecklistItem.objects.select_related("folder__course"), pk=item_id
    )
    course = item.folder.course
    _require_folder_access(request, course)

    if not item.is_removable:
        messages.error(
            request,
            "This item is part of the standard checklist and cannot be removed.",
        )
    else:
        title = item.title
        item.delete()
        messages.success(request, f"Removed “{title}”.")
    return redirect("folder_detail", course_id=course.pk)


def _get_item_for_edit(request, item_id):
    item = get_object_or_404(
        ChecklistItem.objects.select_related("folder__course"), pk=item_id
    )
    _require_folder_access(request, item.folder.course)
    return item


@login_required
@require_POST
def item_mark_na(request, item_id):
    """Mark an item Not Applicable (with an optional note). N/A items are
    excluded from completeness."""
    item = _get_item_for_edit(request, item_id)
    item.status = ItemStatus.NOT_APPLICABLE
    item.na_note = request.POST.get("na_note", "").strip()
    item.save(update_fields=["status", "na_note"])
    messages.success(request, f"“{item.title}” marked not applicable.")
    return redirect("folder_detail", course_id=item.folder.course_id)


@login_required
@require_POST
def item_clear_na(request, item_id):
    """Return an N/A item to pending (it counts toward completeness again)."""
    item = _get_item_for_edit(request, item_id)
    item.status = ItemStatus.PENDING
    item.na_note = ""
    item.save(update_fields=["status", "na_note"])
    messages.success(request, f"“{item.title}” marked applicable.")
    return redirect("folder_detail", course_id=item.folder.course_id)
