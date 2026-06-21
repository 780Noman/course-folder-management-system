"""Transactional emails for accounts (invites, etc.)."""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def build_invite_link(user, request):
    """Build the absolute, single-use set-password URL for an invited user."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse("invite_confirm", kwargs={"uidb64": uidb64, "token": token})
    return request.build_absolute_uri(path)


def send_invite_email(user, request):
    """Email the invited user a one-time link to set their own password."""
    link = build_invite_link(user, request)
    timeout_days = settings.PASSWORD_RESET_TIMEOUT // 86400
    context = {"user": user, "link": link, "timeout_days": timeout_days}

    subject = render_to_string("accounts/email/invite_subject.txt", context).strip()
    body = render_to_string("accounts/email/invite_body.txt", context)
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
