"""Password reset flow and login rate-limiting/lockout (Task 5)."""

import re

import pytest
from django.core import mail
from django.core.cache import cache
from django.urls import reverse

PASSWORD = "StrongPass123!"


@pytest.fixture(autouse=True)
def _isolate(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    cache.clear()  # lockout counters live in the (process-wide) cache
    yield
    cache.clear()


# --- Password reset --------------------------------------------------------

def test_password_reset_sends_email_with_link(client, faculty_user):
    resp = client.post(reverse("password_reset"), {"email": faculty_user.email})
    assert resp.status_code == 302
    assert resp.headers["Location"] == reverse("password_reset_done")
    assert len(mail.outbox) == 1
    assert "/reset/" in mail.outbox[0].body


def test_password_reset_end_to_end(client, faculty_user):
    client.post(reverse("password_reset"), {"email": faculty_user.email})
    path = re.search(r"(/reset/[^\s]+)", mail.outbox[0].body).group(1)

    resp = client.get(path)  # redirects to the set-password step
    form_url = resp.headers["Location"]

    resp = client.post(
        form_url,
        {"new_password1": "ResetPass456!", "new_password2": "ResetPass456!"},
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] == reverse("password_reset_complete")

    faculty_user.refresh_from_db()
    assert faculty_user.check_password("ResetPass456!")


def test_password_reset_for_unknown_email_reveals_nothing(db, client):
    resp = client.post(reverse("password_reset"), {"email": "nobody@uiit.edu.pk"})
    assert resp.status_code == 302  # same response as a real address
    assert len(mail.outbox) == 0


# --- Login lockout ---------------------------------------------------------

def test_lockout_after_repeated_failures(client, faculty_user, settings):
    settings.LOGIN_FAILURE_LIMIT = 3
    settings.LOGIN_LOCKOUT_SECONDS = 900
    url = reverse("login")

    for _ in range(3):
        resp = client.post(url, {"username": faculty_user.email, "password": "wrong"})
        assert resp.status_code == 200  # re-render with error

    # Now locked: even the CORRECT password is refused.
    resp = client.post(url, {"username": faculty_user.email, "password": PASSWORD})
    assert resp.status_code == 200
    assert b"Too many failed sign-in attempts" in resp.content
    assert resp.wsgi_request.user.is_authenticated is False


def test_successful_login_clears_failure_counter(client, faculty_user, settings):
    settings.LOGIN_FAILURE_LIMIT = 3
    url = reverse("login")

    # Two failures (below the limit)...
    for _ in range(2):
        client.post(url, {"username": faculty_user.email, "password": "wrong"})

    # ...then a success should clear the counter.
    resp = client.post(url, {"username": faculty_user.email, "password": PASSWORD})
    assert resp.status_code == 302  # logged in -> redirect

    from accounts import ratelimit
    assert ratelimit.is_locked(resp.wsgi_request, faculty_user.email) is False
