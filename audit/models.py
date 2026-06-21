"""Audit log: who did what, when. Written by services across the project."""

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    action = models.CharField(max_length=50)
    target_type = models.CharField(max_length=50, blank=True)
    target_id = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        who = self.actor_id or "system"
        return f"{self.action} by {who} on {self.target_type}#{self.target_id}"
