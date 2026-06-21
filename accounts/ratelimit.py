"""Cache-based login throttling.

Failed login attempts are counted per (client IP, submitted email). Once the
count reaches ``LOGIN_FAILURE_LIMIT`` the pair is locked until the cache entry
expires (``LOGIN_LOCKOUT_SECONDS`` after the most recent failure). A successful
login clears the counter.
"""

from django.conf import settings
from django.core.cache import cache


def _client_ip(request):
    return request.META.get("REMOTE_ADDR") or "unknown"


def _key(request, email):
    return f"login-failures:{_client_ip(request)}:{(email or '').strip().lower()}"


def is_locked(request, email):
    return cache.get(_key(request, email), 0) >= settings.LOGIN_FAILURE_LIMIT


def record_failure(request, email):
    key = _key(request, email)
    count = cache.get(key, 0) + 1
    cache.set(key, count, settings.LOGIN_LOCKOUT_SECONDS)
    return count


def clear_failures(request, email):
    cache.delete(_key(request, email))
