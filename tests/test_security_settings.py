"""Phase 11 Task 3: production security settings are present and correct."""

import importlib
import os

import pytest


@pytest.fixture(scope="module")
def prod_settings():
    """Import the prod settings module directly with the env it requires."""
    os.environ.setdefault("SECRET_KEY", "x" * 60)
    os.environ.setdefault("ALLOWED_HOSTS", "example.com")
    os.environ.setdefault("DATABASE_URL", "postgres://u:p@db:5432/c")
    mod = importlib.import_module("config.settings.prod")
    return importlib.reload(mod)


def test_https_and_hsts(prod_settings):
    assert prod_settings.SECURE_SSL_REDIRECT is True
    assert prod_settings.SECURE_HSTS_SECONDS >= 31536000
    assert prod_settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    assert prod_settings.SECURE_HSTS_PRELOAD is True
    assert prod_settings.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")


def test_secure_cookies(prod_settings):
    assert prod_settings.SESSION_COOKIE_SECURE is True
    assert prod_settings.CSRF_COOKIE_SECURE is True
    assert prod_settings.SESSION_COOKIE_HTTPONLY is True
    assert prod_settings.CSRF_COOKIE_HTTPONLY is True


def test_headers(prod_settings):
    assert prod_settings.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert prod_settings.X_FRAME_OPTIONS == "DENY"
    assert prod_settings.SECURE_REFERRER_POLICY == "same-origin"


def test_debug_off_in_prod(prod_settings):
    assert prod_settings.DEBUG is False


def test_csrf_and_clickjacking_middleware_enabled(settings):
    assert "django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE
    assert "django.middleware.clickjacking.XFrameOptionsMiddleware" in settings.MIDDLEWARE
    assert "django.middleware.security.SecurityMiddleware" in settings.MIDDLEWARE


def test_lockout_configured(settings):
    assert settings.LOGIN_FAILURE_LIMIT >= 1
    assert settings.LOGIN_LOCKOUT_SECONDS >= 1
