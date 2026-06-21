"""
Development settings.

Safe-by-default local values so the project runs without a fully populated
``.env``: an insecure throwaway secret key, debug on, and a permissive host
list. Never use this module in production.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-dev-only-key-not-for-production",
)

ALLOWED_HOSTS = env("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "[::1]"])

# Show emails (invites, password resets) in the console during development.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
