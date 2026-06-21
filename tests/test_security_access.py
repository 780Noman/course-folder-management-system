"""Phase 11 Task 1: role + object-level access-control audit (regression locks).

Properties asserted:
- Admin-only views reject faculty (403) and anonymous (redirect to login).
- Faculty-only views reject admin (403).
- Folder WRITE actions are owner-only (other faculty AND admin get 403).
- Folder READ actions allow owner + admin, reject other faculty.
"""

import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from academics.models import Course, Term
from folders.models import ItemFile

User = get_user_model()


@pytest.fixture(autouse=True)
def _media_tmp(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


@pytest.fixture
def course(db, faculty_user):
    term = Term.objects.create(season=Term.Season.FALL, year=2026, is_current=True)
    return Course.objects.create(
        code="CS101", title="PF", section="A", program="BSCS",
        study_semester=1, instructor=faculty_user, term=term,
    )


@pytest.fixture
def other_faculty(db):
    return User.objects.create_user(email="intruder@uiit.edu.pk", name="Intruder",
                                    password="StrongPass123!")


# --- Admin-only views ------------------------------------------------------

ADMIN_ONLY = [
    ("invite_user", ()),
    ("faculty_list", ()),
    ("term_list", ()),
    ("course_list", ()),
    ("course_search", ()),
    ("report", ()),
    ("report_export_pdf", ()),
    ("report_export_xlsx", ()),
    ("review_list", ()),
]


@pytest.mark.parametrize("name,args", ADMIN_ONLY)
def test_admin_only_views_reject_faculty(faculty_client, name, args):
    assert faculty_client.get(reverse(name, args=args)).status_code == 403


@pytest.mark.parametrize("name,args", ADMIN_ONLY)
def test_admin_only_views_redirect_anonymous(client, name, args):
    resp = client.get(reverse(name, args=args))
    assert resp.status_code == 302
    assert reverse("login") in resp.headers["Location"]


def test_faculty_dashboard_rejects_admin(admin_client):
    assert admin_client.get(reverse("faculty_dashboard")).status_code == 403


def test_admin_dashboard_rejects_faculty(faculty_client):
    assert faculty_client.get(reverse("admin_dashboard")).status_code == 403


# --- Folder object-level: another faculty is always denied -----------------

@pytest.mark.django_db
def test_other_faculty_denied_read_and_write(client, course, other_faculty):
    client.force_login(other_faculty)
    item = course.folder.items.get(order=1)

    # read
    assert client.get(reverse("folder_detail", args=[course.pk])).status_code == 403
    # writes
    assert client.post(reverse("item_add", args=[course.pk]),
                       {"kind": "quiz", "phase": "MID"}).status_code == 403
    assert client.post(reverse("file_upload", args=[item.pk]),
                       {"file": SimpleUploadedFile("x.pdf", b"%PDF-1.4")}).status_code == 403
    assert client.post(reverse("item_mark_na", args=[item.pk])).status_code == 403


# --- Folder writes are owner-only: admin is READ-only ----------------------

@pytest.mark.django_db
def test_admin_can_read_but_not_write_folder(admin_client, course):
    item = course.folder.items.get(order=1)

    # admin READ is allowed
    assert admin_client.get(reverse("folder_detail", args=[course.pk])).status_code == 200

    # admin WRITES are denied (faculty edit their own; admin reviews)
    assert admin_client.post(reverse("item_add", args=[course.pk]),
                             {"kind": "quiz", "phase": "MID"}).status_code == 403
    assert admin_client.post(reverse("file_upload", args=[item.pk]),
                             {"file": SimpleUploadedFile("x.pdf", b"%PDF-1.4")}).status_code == 403
    assert admin_client.post(reverse("item_mark_na", args=[item.pk])).status_code == 403


@pytest.mark.django_db
def test_owner_can_write(faculty_client, course):
    item = course.folder.items.get(order=1)
    assert faculty_client.post(reverse("item_mark_na", args=[item.pk])).status_code == 302


@pytest.mark.django_db
def test_admin_can_read_files_for_review(course, faculty_user, admin_user):
    """Admin must still open faculty files (read) during review, not delete them."""
    from django.test import Client

    fac = Client(); fac.force_login(faculty_user)
    adm = Client(); adm.force_login(admin_user)

    item = course.folder.items.get(order=1)
    fac.post(reverse("file_upload", args=[item.pk]),
             {"file": SimpleUploadedFile("c.pdf", b"%PDF-1.4 x",
                                         content_type="application/pdf")})
    f = ItemFile.objects.get(item=item)

    # admin READ ok; close the streamed response so no file handle lingers
    resp = adm.get(reverse("file_open", args=[f.pk]))
    assert resp.status_code == 200
    if hasattr(resp, "streaming_content"):
        b"".join(resp.streaming_content)
        resp.close()
    # admin DELETE denied (owner-only)
    assert adm.post(reverse("file_delete", args=[f.pk])).status_code == 403
