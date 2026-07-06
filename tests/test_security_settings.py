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


def test_prod_cache_is_process_shared(prod_settings):
    """Lockout counters live in the cache; it must be shared across Gunicorn
    workers (LocMemCache would silently weaken the login lockout)."""
    backend = prod_settings.CACHES["default"]["BACKEND"]
    assert backend == "django.core.cache.backends.db.DatabaseCache"


def test_prod_logging_reaches_the_console(prod_settings):
    """Errors must land in the container log (Django's default prod config
    silently drops them: console is debug-only, mail_admins has no ADMINS)."""
    logging_conf = prod_settings.LOGGING
    assert "console" in logging_conf["handlers"]
    assert logging_conf["root"]["handlers"] == ["console"]
    assert "console" in logging_conf["loggers"]["django"]["handlers"]


def test_email_backend_follows_email_host(prod_settings):
    """No SMTP host configured -> console backend (links readable in the app
    log) instead of an SMTP backend that errors on every send."""
    import importlib
    import os

    old = os.environ.pop("EMAIL_HOST", None)
    try:
        mod = importlib.reload(prod_settings)
        assert mod.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend"

        os.environ["EMAIL_HOST"] = "smtp.example.com"
        mod = importlib.reload(prod_settings)
        assert mod.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend"
        assert mod.EMAIL_HOST == "smtp.example.com"
    finally:
        if old is None:
            os.environ.pop("EMAIL_HOST", None)
        else:
            os.environ["EMAIL_HOST"] = old
        importlib.reload(prod_settings)
