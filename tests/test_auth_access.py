"""Login redirect-by-role (Task 2) and server-side role enforcement (Task 3)."""

from django.urls import reverse


def test_login_page_renders(client):
    resp = client.get(reverse("login"))
    assert resp.status_code == 200
    assert b"Sign in" in resp.content


def test_dashboard_redirect_admin(admin_client):
    resp = admin_client.get(reverse("dashboard"))
    assert resp.status_code == 302
    assert resp.headers["Location"] == reverse("admin_dashboard")


def test_dashboard_redirect_faculty(faculty_client):
    resp = faculty_client.get(reverse("dashboard"))
    assert resp.status_code == 302
    assert resp.headers["Location"] == reverse("faculty_dashboard")


def test_anonymous_redirected_to_login(client):
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 302
    assert reverse("login") in resp.headers["Location"]


def test_faculty_cannot_reach_admin_dashboard(faculty_client):
    resp = faculty_client.get(reverse("admin_dashboard"))
    assert resp.status_code == 403


def test_admin_cannot_reach_faculty_dashboard(admin_client):
    resp = admin_client.get(reverse("faculty_dashboard"))
    assert resp.status_code == 403


def test_admin_reaches_admin_dashboard(admin_client):
    assert admin_client.get(reverse("admin_dashboard")).status_code == 200


def test_faculty_reaches_faculty_dashboard(faculty_client):
    assert faculty_client.get(reverse("faculty_dashboard")).status_code == 200


def test_anonymous_blocked_from_role_views(client):
    # wrong-role gets 403, but logged-out should be sent to login
    resp = client.get(reverse("admin_dashboard"))
    assert resp.status_code == 302
    assert reverse("login") in resp.headers["Location"]
