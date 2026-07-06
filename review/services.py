r"""Folder review lifecycle: submit, approve, return.

State machine (strict, linear):
    DRAFT --submit_mid--> MID_SUBMITTED --approve_mid--> MID_APPROVED
                                        \--return_mid--> DRAFT
    MID_APPROVED --submit_final--> FINAL_SUBMITTED --approve_final--> FINAL_APPROVED
                                                    \--return_final--> MID_APPROVED
(FINAL_APPROVED --> CERTIFIED is handled at certificate issuance in Phase 7.)
"""

from functools import wraps

from django.db import transaction
from django.utils import timezone

from audit.services import record
from folders.models import CourseFolder, FolderStatus


class TransitionError(Exception):
    """Raised when a lifecycle transition is not allowed in the current state."""


def _transition(func):
    """Run a lifecycle transition atomically on a row-locked folder.

    Re-reads the folder with select_for_update so concurrent transitions
    (double-click, two tabs) serialize: the second sees the new status and
    fails its guard instead of applying twice. The caller's instance is
    refreshed to the committed state afterwards.
    """
    @wraps(func)
    def wrapper(folder, user, **kwargs):
        with transaction.atomic():
            locked = CourseFolder.objects.select_for_update().get(pk=folder.pk)
            result = func(locked, user, **kwargs)
        folder.refresh_from_db()
        return result
    return wrapper


def _clear_flags(folder, phases):
    folder.items.filter(phase__in=phases).update(is_flagged=False, review_note="")


@_transition
def submit_mid(folder, user):
    if folder.status != FolderStatus.DRAFT:
        raise TransitionError("The mid-term phase is not in a submittable state.")
    if not folder.is_phase_complete(CourseFolder.MID_PHASES):
        raise TransitionError(
            "Complete every required General and Mid-term item before submitting."
        )
    folder.status = FolderStatus.MID_SUBMITTED
    folder.mid_submitted_at = timezone.now()
    folder.mid_return_note = ""
    folder.save(update_fields=["status", "mid_submitted_at", "mid_return_note"])
    _clear_flags(folder, CourseFolder.MID_PHASES)
    record(user, "submit_mid", folder, course=folder.course_id)


@_transition
def submit_final(folder, user):
    if folder.status != FolderStatus.MID_APPROVED:
        raise TransitionError(
            "The final-term phase can be submitted only after the mid-term is approved."
        )
    if not folder.is_phase_complete(CourseFolder.FINAL_PHASES):
        raise TransitionError(
            "Complete every required Final-term item before submitting."
        )
    folder.status = FolderStatus.FINAL_SUBMITTED
    folder.final_submitted_at = timezone.now()
    folder.final_return_note = ""
    folder.save(update_fields=["status", "final_submitted_at", "final_return_note"])
    _clear_flags(folder, CourseFolder.FINAL_PHASES)
    record(user, "submit_final", folder, course=folder.course_id)


@_transition
def approve_mid(folder, user):
    if folder.status != FolderStatus.MID_SUBMITTED:
        raise TransitionError("The mid-term phase is not awaiting review.")
    folder.status = FolderStatus.MID_APPROVED
    folder.mid_approved_at = timezone.now()
    folder.mid_return_note = ""
    folder.save(update_fields=["status", "mid_approved_at", "mid_return_note"])
    _clear_flags(folder, CourseFolder.MID_PHASES)
    record(user, "approve_mid", folder, course=folder.course_id)


@_transition
def approve_final(folder, user):
    if folder.status != FolderStatus.FINAL_SUBMITTED:
        raise TransitionError("The final-term phase is not awaiting review.")
    folder.status = FolderStatus.FINAL_APPROVED
    folder.final_approved_at = timezone.now()
    folder.final_return_note = ""
    folder.save(update_fields=["status", "final_approved_at", "final_return_note"])
    _clear_flags(folder, CourseFolder.FINAL_PHASES)
    record(user, "approve_final", folder, course=folder.course_id)


def _apply_return(folder, phases, overall_note, flagged_notes):
    """Reset flags for the phase, then flag the items the admin marked."""
    if not overall_note and not flagged_notes:
        raise TransitionError(
            "Add an overall note or flag at least one item before returning."
        )
    items = folder.items.filter(phase__in=phases)
    items.update(is_flagged=False, review_note="")
    for item in items:
        if item.id in flagged_notes:
            item.is_flagged = True
            item.review_note = flagged_notes[item.id]
            item.save(update_fields=["is_flagged", "review_note"])


@_transition
def return_mid(folder, user, overall_note="", flagged_notes=None):
    if folder.status != FolderStatus.MID_SUBMITTED:
        raise TransitionError("The mid-term phase is not awaiting review.")
    _apply_return(folder, CourseFolder.MID_PHASES, overall_note, flagged_notes or {})
    folder.status = FolderStatus.DRAFT
    folder.mid_return_note = overall_note
    folder.save(update_fields=["status", "mid_return_note"])
    record(user, "return_mid", folder, course=folder.course_id,
           flagged=list(flagged_notes or {}))


@_transition
def return_final(folder, user, overall_note="", flagged_notes=None):
    if folder.status != FolderStatus.FINAL_SUBMITTED:
        raise TransitionError("The final-term phase is not awaiting review.")
    _apply_return(folder, CourseFolder.FINAL_PHASES, overall_note, flagged_notes or {})
    folder.status = FolderStatus.MID_APPROVED
    folder.final_return_note = overall_note
    folder.save(update_fields=["status", "final_return_note"])
    record(user, "return_final", folder, course=folder.course_id,
           flagged=list(flagged_notes or {}))
