"""Helper for writing audit-log entries."""

from .models import AuditLog


def record(actor, action, target=None, **metadata):
    """Write an audit entry. ``target`` is any model instance (or None)."""
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "pk", None) else None,
        action=action,
        target_type=target.__class__.__name__ if target is not None else "",
        target_id=str(target.pk) if target is not None else "",
        metadata=metadata,
    )
