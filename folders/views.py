"""Course folder views (faculty folder view + flexible items)."""

import logging
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Max
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from academics.models import Course
from audit.services import record

from .models import (
    ChecklistItem,
    CourseFolder,
    ItemFile,
    ItemStatus,
    Phase,
    SampleKind,
)
from .services import (
    delete_item,
    delete_item_file,
    get_or_create_folder,
    recompute_item_status,
    save_item_file,
)
from .validators import validate_upload

logger = logging.getLogger(__name__)

# Count-variable families faculty can grow/shrink to match the course.
FAMILIES = {
    "quiz": "Quizzes- Paper {n} (W,A,B)",
    "assignment": "Assignment {n} (W,A,B)",
}
_FAMILY_PREFIX = {"quiz": "Quizzes- Paper", "assignment": "Assignment"}


def _require_folder_access(request, course):
    """READ access: faculty may open their own folders; admins may open any."""
    user = request.user
    if not (user.is_admin or course.instructor_id == user.id):
        raise PermissionDenied


def _require_folder_owner(request, course):
    """WRITE access: only the course's own instructor may modify the folder.

    Admins review folders (read-only); they do not edit faculty content, per the
    role model in CLAUDE.md. Least privilege for mutation endpoints.
    """
    if course.instructor_id != request.user.id:
        raise PermissionDenied


_PHASE_LABELS = {Phase.GENERAL: "General", Phase.MID: "Mid-term", Phase.FINAL: "Final-term"}


def _item_update(request, folder, phase, item=None, **row_ctx):
    """HTMX response: the item row (or nothing, if removed) plus out-of-band
    refreshes of the progress bars and the action panel (submit readiness)."""
    items = list(folder.items.all())
    context = {
        "item": item,
        "overall": CourseFolder.progress(items),
        "phase": phase,
        "phase_label": _PHASE_LABELS.get(phase, ""),
        "section_prog": CourseFolder.progress([i for i in items if i.phase == phase]),
        # For the out-of-band action panel: item actions are owner-only, so
        # the requester is always the instructor here.
        "course": folder.course,
        "folder": folder,
        "mid_ready": folder.is_phase_complete(CourseFolder.MID_PHASES),
        "final_ready": folder.is_phase_complete(CourseFolder.FINAL_PHASES),
    }
    context.update(row_ctx)
    return render(request, "folders/_item_update.html", context)


@login_required
def folder_detail(request, course_id):
    course = get_object_or_404(Course.objects.select_related("instructor", "term"),
                               pk=course_id)
    _require_folder_access(request, course)

    folder = get_or_create_folder(course)
    # Prefetch files so per-item file lists / sample groups add no extra queries.
    items = list(folder.items.prefetch_related("files"))

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
    is_owner = course.instructor_id == request.user.id

    # Compact list the bulk-upload panel maps local subfolders onto (owner only).
    bulk_items = None
    if is_owner:
        bulk_items = [
            {
                "pk": i.pk,
                "order": i.order,
                "title": i.title,
                "allows_samples": i.allows_samples,
                "upload_url": reverse("file_upload", args=[i.pk]),
            }
            for i in items
        ]

    return render(
        request,
        "folders/folder_detail.html",
        {
            "course": course,
            "folder": folder,
            "sections": sections,
            "overall": overall,
            "add_kinds": [("quiz", "quiz"), ("assignment", "assignment")],
            "is_owner": is_owner,
            "bulk_items": bulk_items,
            "max_upload_mb": settings.MAX_UPLOAD_MB,
            "mid_ready": folder.is_phase_complete(CourseFolder.MID_PHASES),
            "final_ready": folder.is_phase_complete(CourseFolder.FINAL_PHASES),
        },
    )


@login_required
def folder_status(request, course_id):
    """Lightweight poll target for the folder page.

    The action panel polls this with the status it was rendered with; when the
    focal person has since approved/returned/certified, we answer with
    HX-Refresh so the open page reloads itself and shows the change (return
    notes, flags, certificate button) without a manual refresh. Otherwise 204.
    """
    course = get_object_or_404(Course, pk=course_id)
    _require_folder_access(request, course)
    folder = get_or_create_folder(course)
    if request.GET.get("status") != folder.status:
        response = HttpResponse(status=200)
        response["HX-Refresh"] = "true"
        return response
    return HttpResponse(status=204)


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
    _require_folder_owner(request, course)

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
    record(request.user, "item_add", item, course=course.pk, title=item.title)
    # HTMX: append the new row to the section list and refresh the progress bars.
    if request.htmx:
        return _item_update(request, folder, item.phase, item=item)
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
    _require_folder_owner(request, course)

    if not item.is_removable:
        if request.htmx:
            # Re-render the row unchanged with an inline error note.
            return _item_update(
                request, item.folder, item.phase, item=item,
                upload_error="This item is part of the standard checklist and "
                             "cannot be removed.")
        messages.error(
            request,
            "This item is part of the standard checklist and cannot be removed.",
        )
        return redirect("folder_detail", course_id=course.pk)

    folder, phase, title = item.folder, item.phase, item.title
    delete_item(item)  # also removes any uploaded files from storage
    record(request.user, "item_remove", course, title=title)
    # HTMX: no row (it is removed) + out-of-band progress refresh.
    if request.htmx:
        return _item_update(request, folder, phase, item=None)
    messages.success(request, f"Removed “{title}”.")
    return redirect("folder_detail", course_id=course.pk)


def _get_item_for_edit(request, item_id):
    """Fetch an item for a WRITE action (owner-only)."""
    item = get_object_or_404(
        ChecklistItem.objects.select_related("folder__course"), pk=item_id
    )
    _require_folder_owner(request, item.folder.course)
    return item


@login_required
@require_POST
def file_upload(request, item_id):
    """Upload one or more files to a checklist item (private object storage).

    Accepts a single file (the manual per-item form) or many (the folder
    bulk-upload panel sends a whole subfolder at once). Every file is validated
    and saved independently, so one bad file never aborts the rest; a per-request
    summary of what succeeded and what failed is returned.
    """
    item = _get_item_for_edit(request, item_id)

    def _respond(error=None, uploaded_name=None):
        # HTMX: swap the row in place (status + evidence) and refresh progress bars.
        if request.htmx:
            item.refresh_from_db()
            return _item_update(request, item.folder, item.phase, item=item,
                                upload_error=error, uploaded_name=uploaded_name)
        if error:
            messages.error(request, error)
        elif uploaded_name:
            messages.success(request, f"Uploaded “{uploaded_name}”.")
        return redirect("folder_detail", course_id=item.folder.course_id)

    uploads = request.FILES.getlist("file")
    if not uploads:
        return _respond(error="No file selected.")

    # Sample (W/A/B) items require the target group; ordinary items ignore it.
    sample_kind = SampleKind.NONE
    if item.allows_samples:
        sample_kind = request.POST.get("sample_kind", "")
        if sample_kind not in {SampleKind.WORST, SampleKind.AVERAGE, SampleKind.BEST}:
            return _respond(error="Choose a sample group (Worst, Average, or Best).")

    saved, failures = [], []
    for upload in uploads:
        try:
            validate_upload(upload)
            save_item_file(item, upload, request.user, sample_kind=sample_kind)
            saved.append(upload.name)
        except ValidationError as exc:
            failures.append(f"{upload.name}: {' '.join(exc.messages)}")
        except Exception:  # storage/thumbnail/unexpected — never abort the batch
            logger.exception(
                "Upload failed for %r on item %s", upload.name, item.pk
            )
            failures.append(f"{upload.name}: could not be saved, please retry.")

    error = None
    if failures:
        error = "Some files were not uploaded — " + "; ".join(failures)
    uploaded_name = None
    if saved:
        uploaded_name = saved[0] if len(saved) == 1 else f"{len(saved)} files"
    return _respond(error=error, uploaded_name=uploaded_name)


def _get_file_for_access(request, file_id):
    item_file = get_object_or_404(
        ItemFile.objects.select_related("item__folder__course"), pk=file_id
    )
    _require_folder_access(request, item_file.item.folder.course)
    return item_file


def _serve(field_file, content_type, download_name):
    """Serve a private file: redirect to a signed URL (S3) or stream (local)."""
    if settings.USE_S3:
        # querystring_auth makes .url a short-lived signed URL.
        return redirect(field_file.url)
    field_file.open("rb")
    return FileResponse(
        field_file, content_type=content_type or "application/octet-stream",
        filename=download_name,
    )


@login_required
def file_open(request, file_id):
    """Open the full file on demand (lazy) via a short-lived signed URL."""
    item_file = _get_file_for_access(request, file_id)
    return _serve(item_file.file, item_file.content_type, item_file.original_name)


@login_required
def file_thumb(request, file_id):
    """Serve the (small) thumbnail for an image file."""
    item_file = _get_file_for_access(request, file_id)
    if not item_file.thumbnail:
        raise Http404("No thumbnail for this file.")
    return _serve(item_file.thumbnail, "image/jpeg", "thumb.jpg")


@login_required
@require_POST
def file_delete(request, file_id):
    """Delete a file (and its thumbnail) from storage and the database."""
    item_file = _get_file_for_access(request, file_id)
    _require_folder_owner(request, item_file.item.folder.course)  # owner-only write
    item = item_file.item
    course_id = item.folder.course_id
    name = item_file.original_name
    delete_item_file(item_file, user=request.user)
    if request.htmx:
        item.refresh_from_db()
        return _item_update(request, item.folder, item.phase, item=item)
    messages.success(request, f"Deleted “{name}”.")
    return redirect("folder_detail", course_id=course_id)


@login_required
@require_POST
def item_mark_na(request, item_id):
    """Mark an item Not Applicable (with an optional note). N/A items are
    excluded from completeness."""
    item = _get_item_for_edit(request, item_id)
    item.status = ItemStatus.NOT_APPLICABLE
    item.na_note = request.POST.get("na_note", "").strip()
    item.save(update_fields=["status", "na_note"])
    record(request.user, "item_mark_na", item, note=item.na_note)
    if request.htmx:
        return _item_update(request, item.folder, item.phase, item=item)
    messages.success(request, f"“{item.title}” marked not applicable.")
    return redirect("folder_detail", course_id=item.folder.course_id)


@login_required
@require_POST
def item_clear_na(request, item_id):
    """Return an N/A item to pending (it counts toward completeness again)."""
    item = _get_item_for_edit(request, item_id)
    # Leave N/A, then recompute from the actual uploaded evidence.
    item.status = ItemStatus.PENDING
    item.na_note = ""
    item.save(update_fields=["status", "na_note"])
    recompute_item_status(item)
    record(request.user, "item_clear_na", item)
    if request.htmx:
        return _item_update(request, item.folder, item.phase, item=item)
    messages.success(request, f"“{item.title}” marked applicable.")
    return redirect("folder_detail", course_id=item.folder.course_id)
