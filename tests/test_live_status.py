"""The faculty folder page stays fresh without manual refreshes.

Two mechanisms:
1. HTMX item-action responses include the action panel out-of-band, so the
   submit button enables the moment the last required item is complete.
2. The panel polls folder_status; when the admin changed the folder status
   (approve/return/certify) the poll answers HX-Refresh and the page reloads.
"""

import pytest
from django.urls import reverse

from academics.models import Course, Term
from folders.models import CourseFolder, FolderStatus, ItemStatus

HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def course(db, faculty_user):
    term = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    return Course.objects.create(
        code="CS101", title="PF", section="A", program="BSCS",
        study_semester=1, instructor=faculty_user, term=term,
    )


def _status_url(course, status):
    return reverse("folder_status", args=[course.pk]) + f"?status={status}"


# --- Poll endpoint -----------------------------------------------------------

@pytest.mark.django_db
def test_poll_is_quiet_while_status_unchanged(faculty_client, course):
    resp = faculty_client.get(_status_url(course, FolderStatus.DRAFT))
    assert resp.status_code == 204
    assert "HX-Refresh" not in resp


@pytest.mark.django_db
def test_poll_triggers_refresh_after_admin_action(faculty_client, course):
    """Page was rendered in DRAFT; meanwhile the folder moved on (e.g. the
    admin certified it) -> the open page is told to reload itself."""
    folder = course.folder
    folder.status = FolderStatus.CERTIFIED
    folder.save(update_fields=["status"])

    resp = faculty_client.get(_status_url(course, FolderStatus.DRAFT))
    assert resp.status_code == 200
    assert resp["HX-Refresh"] == "true"


@pytest.mark.django_db
def test_poll_requires_folder_access(client, course):
    from django.contrib.auth import get_user_model

    other = get_user_model().objects.create_user(email="o@uiit.edu.pk", name="O")
    client.force_login(other)
    assert client.get(_status_url(course, FolderStatus.DRAFT)).status_code == 403


@pytest.mark.django_db
def test_folder_page_contains_polling_panel(faculty_client, course):
    resp = faculty_client.get(reverse("folder_detail", args=[course.pk]))
    body = resp.content.decode()
    assert 'id="folder-actions"' in body
    assert reverse("folder_status", args=[course.pk]) in body
    assert "every 30s" in body


# --- Out-of-band action panel on item actions --------------------------------

@pytest.mark.django_db
def test_item_action_response_updates_submit_readiness(faculty_client, course):
    """Marking the last incomplete mid-phase item N/A must return the action
    panel with the submit button enabled - no page refresh needed."""
    folder = course.folder
    mid_items = folder.items.filter(
        phase__in=CourseFolder.MID_PHASES, is_required=True
    )
    # Everything complete except one optional-to-NA target item.
    target = mid_items.first()
    mid_items.exclude(pk=target.pk).update(status=ItemStatus.AVAILABLE)

    resp = faculty_client.post(
        reverse("item_mark_na", args=[target.pk]),
        {"note": "Not applicable this term"},
        **HTMX,
    )
    body = resp.content.decode()
    assert 'id="folder-actions"' in body
    assert 'hx-swap-oob="true"' in body
    assert "Submit mid-term for review" in body
    # Enabled now: the disabled attribute must not be on the submit button.
    panel = body[body.index('id="folder-actions"'):]
    assert "disabled" not in panel


@pytest.mark.django_db
def test_item_action_response_keeps_button_disabled_when_incomplete(
    faculty_client, course
):
    folder = course.folder
    item = folder.items.filter(
        phase__in=CourseFolder.MID_PHASES, is_required=True
    ).first()

    resp = faculty_client.post(
        reverse("item_mark_na", args=[item.pk]), {"note": "n/a"}, **HTMX
    )
    body = resp.content.decode()
    panel = body[body.index('id="folder-actions"'):]
    assert "disabled" in panel  # still incomplete -> still disabled
