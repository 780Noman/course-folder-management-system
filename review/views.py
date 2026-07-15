"""Review workflow views: faculty submissions and admin review."""

import hashlib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from academics.models import Course
from accounts.permissions import admin_required
from folders.models import CourseFolder, FolderStatus, ItemStatus, Phase
from folders.services import get_or_create_folder

from . import certificates, services
from .pdf import PdfRenderError


def _require_owner(request, course):
    """Submitting is a faculty action on their own course."""
    if course.instructor_id != request.user.id:
        raise PermissionDenied


@login_required
@require_POST
def submit_mid(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    _require_owner(request, course)
    folder = get_or_create_folder(course)
    try:
        services.submit_mid(folder, request.user)
        messages.success(request, "Mid-term submitted for review.")
    except services.TransitionError as exc:
        messages.error(request, str(exc))
    return redirect("folder_detail", course_id=course.pk)


@login_required
@require_POST
def submit_final(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    _require_owner(request, course)
    folder = get_or_create_folder(course)
    try:
        services.submit_final(folder, request.user)
        messages.success(request, "Final-term submitted for review.")
    except services.TransitionError as exc:
        messages.error(request, str(exc))
    return redirect("folder_detail", course_id=course.pk)


# --- Admin review ----------------------------------------------------------

AWAITING_REVIEW = (FolderStatus.MID_SUBMITTED, FolderStatus.FINAL_SUBMITTED)


def _queue_signature(pairs):
    """A stable fingerprint of the awaiting-review set (id + status).

    Changes when a folder enters the queue (new submission) or leaves it (after
    review), so the queue page can tell whether it needs to reload.
    """
    raw = ";".join(f"{pk}:{status}" for pk, status in sorted(pairs))
    return hashlib.md5(raw.encode()).hexdigest()[:12]


@admin_required
def review_list(request):
    """Admin queue of folders awaiting review."""
    folders = (
        CourseFolder.objects.filter(status__in=AWAITING_REVIEW)
        .select_related("course__instructor", "course__term")
        .order_by("-course__term__year", "course__code")
    )
    queue_sig = _queue_signature(folders.values_list("id", "status"))
    return render(
        request, "review/review_list.html",
        {"folders": folders, "queue_sig": queue_sig},
    )


@admin_required
def review_queue_status(request):
    """Lightweight poll target for the review queue.

    Answers HX-Refresh when the awaiting-review set has changed since the page
    was rendered (a new submission arrived, or a folder was reviewed), so the
    open queue reloads itself without a manual refresh. Otherwise 204.
    """
    pairs = CourseFolder.objects.filter(status__in=AWAITING_REVIEW).values_list(
        "id", "status"
    )
    if request.GET.get("sig") != _queue_signature(pairs):
        response = HttpResponse(status=200)
        response["HX-Refresh"] = "true"
        return response
    return HttpResponse(status=204)


def _build_review_sections(folder):
    items = list(folder.items.prefetch_related("files"))
    for item in items:
        item.needs_attention = item.is_flagged or (
            item.is_required
            and item.status != ItemStatus.AVAILABLE
            and item.status != ItemStatus.NOT_APPLICABLE
        )

    def section(label, phase):
        members = [i for i in items if i.phase == phase]
        return {
            "label": label,
            "phase": phase,
            "items": members,
            "progress": CourseFolder.progress(members),
        }

    return [
        section("General", Phase.GENERAL),
        section("Mid-term", Phase.MID),
        section("Final-term", Phase.FINAL),
    ]


@admin_required
def review_detail(request, course_id):
    course = get_object_or_404(
        Course.objects.select_related("instructor", "term"), pk=course_id
    )
    folder = get_or_create_folder(course)
    sections = _build_review_sections(folder)
    phase_label = ""
    if folder.status == FolderStatus.MID_SUBMITTED:
        phase_label = "Mid-term"
    elif folder.status == FolderStatus.FINAL_SUBMITTED:
        phase_label = "Final-term"
    return render(
        request,
        "review/review_detail.html",
        {
            "course": course,
            "folder": folder,
            "sections": sections,
            "reviewable": folder.status in AWAITING_REVIEW,
            "review_phase_label": phase_label,
        },
    )


def _collect_flagged_notes(request, folder):
    """Read flag_<id>/note_<id> form fields into {item_id: note}."""
    flagged = {}
    for item in folder.items.all():
        if request.POST.get(f"flag_{item.id}"):
            flagged[item.id] = request.POST.get(f"note_{item.id}", "").strip()
    return flagged


@admin_required
@require_POST
def review_action(request, course_id):
    """Approve or return the phase currently awaiting review."""
    course = get_object_or_404(Course, pk=course_id)
    folder = get_or_create_folder(course)
    action = request.POST.get("action")

    is_mid = folder.status == FolderStatus.MID_SUBMITTED
    is_final = folder.status == FolderStatus.FINAL_SUBMITTED
    if not (is_mid or is_final):
        messages.error(request, "This folder is not awaiting review.")
        return redirect("review_detail", course_id=course.pk)

    try:
        if action == "approve":
            (services.approve_mid if is_mid else services.approve_final)(folder, request.user)
            messages.success(request, "Phase approved.")
        elif action == "return":
            overall = request.POST.get("overall_note", "").strip()
            flagged = _collect_flagged_notes(request, folder)
            (services.return_mid if is_mid else services.return_final)(
                folder, request.user, overall_note=overall, flagged_notes=flagged
            )
            messages.success(request, "Folder returned to the instructor.")
        else:
            messages.error(request, "Unknown review action.")
            return redirect("review_detail", course_id=course.pk)
    except services.TransitionError as exc:
        messages.error(request, str(exc))
        return redirect("review_detail", course_id=course.pk)

    return redirect("review_list")


# --- Certificate -----------------------------------------------------------

@admin_required
@require_POST
def certify(request, course_id):
    """Admin issues the certificate (blocked unless the folder is eligible)."""
    course = get_object_or_404(Course, pk=course_id)
    folder = get_or_create_folder(course)
    try:
        certificates.issue_certificate(folder, request.user)
        messages.success(request, "Certificate issued.")
    except certificates.CertificationError as exc:
        messages.error(request, str(exc))
    except PdfRenderError:
        messages.error(
            request,
            "The certificate PDF could not be generated. Nothing was saved — "
            "please try again; if it keeps failing, check the server log.",
        )
    return redirect("review_detail", course_id=course.pk)


@login_required
def certificate_download(request, course_id):
    """Download the certificate PDF (course instructor or any admin)."""
    course = get_object_or_404(
        Course.objects.select_related("folder__certificate"), pk=course_id
    )
    if not (request.user.is_admin or course.instructor_id == request.user.id):
        raise PermissionDenied
    certificate = getattr(getattr(course, "folder", None), "certificate", None)
    if certificate is None:
        raise Http404("No certificate has been issued for this course.")

    if settings.USE_S3:
        return redirect(certificate.pdf.url)  # short-lived signed URL
    certificate.pdf.open("rb")
    return FileResponse(
        certificate.pdf, content_type="application/pdf",
        filename=f"{course.code}-{course.section}-certificate.pdf",
    )
