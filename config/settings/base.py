"""
Base settings shared by every environment.

All environment-specific or secret values are read from the environment via
``django-environ``. Never hard-code secrets here. See ``.env.example`` for the
full list of variables. ``dev.py`` and ``prod.py`` import everything from this
module and override what differs.
"""

from pathlib import Path

import environ

# config/settings/base.py -> config/settings -> config -> repo root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    MAX_UPLOAD_MB=(int, 50),
)

# Load a local .env file if present (never committed). In production the
# variables are provided by the host environment instead.
environ.Env.read_env(BASE_DIR / ".env")

# SECRET_KEY, DEBUG, and ALLOWED_HOSTS are environment-specific and are set in
# dev.py / prod.py (prod reads them strictly from the environment; dev provides
# safe local defaults).

# --- Applications ----------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "django_htmx",
    # Local
    "accounts",
]

AUTH_USER_MODEL = "accounts.User"

# Authentication redirects
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"

# Login throttling / lockout. Counted per (IP, email) in the cache; after
# LOGIN_FAILURE_LIMIT failures the pair is locked for LOGIN_LOCKOUT_SECONDS.
# NOTE: uses Django's default local-memory cache; configure a shared cache
# (Redis/Memcached) in production so the lockout holds across processes.
LOGIN_FAILURE_LIMIT = env.int("LOGIN_FAILURE_LIMIT", default=5)
LOGIN_LOCKOUT_SECONDS = env.int("LOGIN_LOCKOUT_SECONDS", default=900)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves static files directly; must sit right after security.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database --------------------------------------------------------------
# PostgreSQL in Docker/production via DATABASE_URL. Falls back to a local
# SQLite file when DATABASE_URL is unset so the app runs without a database
# server during early local development.
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

# --- Password validation ---------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalization --------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Karachi"
USE_I18N = True
USE_TZ = True

# --- Static files ----------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# --- Uploads ---------------------------------------------------------------
MAX_UPLOAD_MB = env("MAX_UPLOAD_MB")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
