"""Admin-viewable password copies (offline password recovery).

The focal person sets or generates faculty passwords and later needs to read
them back to hand over (this is an offline LAN deployment with no email). Django
only stores a one-way hash, so we keep a *reversible* copy encrypted at rest with
Fernet (AES-128-CBC + HMAC), key from the environment. The copy is admin-only and
is erased the instant the faculty change their own password.

This is a deliberate, documented exception to the usual "never store a recoverable
password" rule — see CLAUDE.md §6. Nothing here ever writes a plaintext column.
"""

import base64
import hashlib
import secrets
import string

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.utils import timezone


def _fernet():
    """Build the Fernet cipher from PASSWORD_ENC_KEY, or derive one from
    SECRET_KEY when unset so dev/tests work without extra configuration."""
    key = settings.PASSWORD_ENC_KEY or ""
    if key:
        key_bytes = key.encode() if isinstance(key, str) else key
    else:
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key_bytes = base64.urlsafe_b64encode(digest)
    return Fernet(key_bytes)


def _encrypt(raw):
    return _fernet().encrypt(raw.encode()).decode()


def _decrypt(token):
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        # Key rotated or corrupt token: treat as unavailable rather than crash.
        return None


def generate_password(length=14):
    """A strong random password that satisfies the project's password policy
    (mixed case, digit, symbol, no all-numeric)."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pw)
            and any(c.isupper() for c in pw)
            and any(c.isdigit() for c in pw)
            and any(c in "!@#$%^&*" for c in pw)
        ):
            return pw


def set_admin_password(user, raw):
    """Set the user's password AND keep an admin-viewable encrypted copy."""
    user.set_password(raw)
    user.admin_password_ciphertext = _encrypt(raw)
    user.password_set_by_admin_at = timezone.now()
    # A fresh admin-set password supersedes any prior faculty change.
    user.password_changed_by_faculty_at = None
    user.save(update_fields=[
        "password",
        "admin_password_ciphertext",
        "password_set_by_admin_at",
        "password_changed_by_faculty_at",
    ])


def clear_admin_password(user):
    """Erase the admin-viewable copy because the faculty changed their own
    password. Idempotent and cheap; safe to call after any password change."""
    if not user.admin_password_ciphertext and user.password_changed_by_faculty_at:
        return
    user.admin_password_ciphertext = ""
    user.password_changed_by_faculty_at = timezone.now()
    user.save(update_fields=[
        "admin_password_ciphertext",
        "password_changed_by_faculty_at",
    ])


def reveal_admin_password(user):
    """Return the admin-set password in clear, or None if none is stored
    (never set, or erased after the faculty changed it)."""
    if not user.admin_password_ciphertext:
        return None
    return _decrypt(user.admin_password_ciphertext)
