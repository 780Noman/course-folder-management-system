"""Authentication and dashboard views."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordResetConfirmView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from . import ratelimit
from .emails import send_invite_email
from .forms import InviteForm
from .permissions import admin_required, faculty_required


class RoleLoginView(LoginView):
    """Single login page with per-(IP, email) throttling. Authenticated users
    are bounced to their dashboard."""

    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def _submitted_email(self):
        return self.request.POST.get("username", "")

    def _locked_response(self, form):
        minutes = max(1, settings.LOGIN_LOCKOUT_SECONDS // 60)
        context = self.get_context_data(form=form, locked=True, lockout_minutes=minutes)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        if ratelimit.is_locked(request, self._submitted_email()):
            return self._locked_response(self.get_form())
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        ratelimit.clear_failures(self.request, self._submitted_email())
        return super().form_valid(form)

    def form_invalid(self, form):
        count = ratelimit.record_failure(self.request, self._submitted_email())
        if count >= settings.LOGIN_FAILURE_LIMIT:
            return self._locked_response(form)
        return super().form_invalid(form)


@admin_required
def invite_user(request):
    """Admin invites a user by name + email; a one-time set-password link is sent."""
    if request.method == "POST":
        form = InviteForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # No usable password until the invitee sets one via the emailed link.
            user.set_unusable_password()
            user.save()
            send_invite_email(user, request)
            messages.success(
                request, f"Invitation sent to {user.email}."
            )
            return redirect("invite_user")
    else:
        form = InviteForm()
    return render(request, "accounts/invite_form.html", {"form": form})


class InviteSetPasswordView(PasswordResetConfirmView):
    """The invited user sets their own password via the one-time link, then is
    logged in. Reuses Django's token validation (single-use + expiring)."""

    template_name = "accounts/set_password.html"
    post_reset_login = True
    success_url = reverse_lazy("dashboard")


@login_required
def dashboard_redirect(request):
    """Send each user to the dashboard for their role."""
    if request.user.is_admin:
        return redirect("admin_dashboard")
    return redirect("faculty_dashboard")


@admin_required
def admin_dashboard(request):
    return render(request, "accounts/dashboard_admin.html")


@faculty_required
def faculty_dashboard(request):
    return render(request, "accounts/dashboard_faculty.html")
