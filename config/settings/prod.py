"""
Production settings.

Every secret and host value MUST come from the environment; there are no
insecure defaults here. Adds HTTPS/security hardening and the WhiteNoise
compressed+hashed static storage. Object storage (R2/S3) and email are wired
in their respective later phases.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# Fails fast if these are not provided by the environment.
SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Hosts/origins trusted for cross-site POSTs (needed for forms over plain HTTP on
# an internal server, e.g. CSRF_TRUSTED_ORIGINS=http://192.168.1.50:8000).
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# --- Cache (must be process-shared) -----------------------------------------
# The login lockout counts failed attempts in the cache. Django's default
# LocMemCache is per-process, so under multi-worker Gunicorn each worker would
# keep its own counter and the lockout would be ineffective. The database
# cache is shared by all workers and needs no extra service; its table is
# created by `manage.py createcachetable` in the container entrypoint.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    }
}

# --- Static files: hashed + compressed, served by WhiteNoise ---------------
STORAGES["staticfiles"]["BACKEND"] = (  # noqa: F405
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

# --- Security headers (always on) ------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
# Cookies are not readable by JavaScript (CSRF travels in the hidden form input).
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# --- HTTPS hardening --------------------------------------------------------
# ON by default (cloud / behind a TLS proxy). Set ENABLE_HTTPS=False for an
# internal server reached over plain HTTP, otherwise the HTTPS redirect and
# secure-only cookies would make the site unreachable / unable to log in.
ENABLE_HTTPS = env.bool("ENABLE_HTTPS", default=True)
if ENABLE_HTTPS:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --- Logging -----------------------------------------------------------------
# Django's default prod logging drops errors (console handler is debug-only and
# the mail handler has no ADMINS). Send everything to stderr instead so errors
# and warnings show up in `docker compose logs web`. Tracebacks stay in the
# server log only — users always get the generic 500 page.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

# --- Email -----------------------------------------------------------------
EMAIL_HOST = env("EMAIL_HOST", default="")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    # No SMTP configured (common on a fresh internal server): print emails to
    # the app log instead of erroring, so the admin can copy invite/reset
    # links from `docker compose logs web`.
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default="Course Folder System <no-reply@uiit.edu.pk>",
)
