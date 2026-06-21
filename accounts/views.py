"""Authentication and dashboard views."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordResetConfirmView
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from . import ratelimit
from .emails import send_invite_email
from .forms import InviteForm
from .models import User
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


@admin_required
def faculty_list(request):
    """List faculty with search; add (invite) and deactivate/reactivate."""
    query = request.GET.get("q", "").strip()
    faculty = User.objects.filter(role=User.Role.FACULTY)
    if query:
        faculty = faculty.filter(Q(name__icontains=query) | Q(email__icontains=query))
    faculty = faculty.annotate(course_count=Count("courses"))
    return render(
        request,
        "accounts/faculty_list.html",
        {"faculty": faculty, "q": query},
    )


@admin_required
@require_POST
def faculty_set_active(request, pk):
    """Soft remove / restore a faculty member (preserves course history)."""
    member = get_object_or_404(User, pk=pk, role=User.Role.FACULTY)
    member.is_active = not member.is_active
    member.save(update_fields=["is_active"])
    state = "reactivated" if member.is_active else "deactivated"
    messages.success(request, f"{member.name} {state}.")
    return redirect("faculty_list")


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
    """Faculty see their own courses, defaulting to the current term with a
    switcher for the past terms they have taught in."""
    from academics.models import Term

    user = request.user
    taught_term_ids = set(
        user.courses.values_list("term_id", flat=True).distinct()
    )
    # Terms the faculty has taught in (most recent first), for the switcher.
    terms = list(Term.objects.filter(pk__in=taught_term_ids))
    current = Term.get_current()

    selected = None
    requested = request.GET.get("term")
    if requested:
        selected = next((t for t in terms if str(t.pk) == requested), None)
    if selected is None:
        if current and current.pk in taught_term_ids:
            selected = current
        elif terms:
            selected = terms[0]  # most recent taught term

    courses = (
        user.courses.filter(term=selected).select_related("term")
        if selected
        else user.courses.none()
    )

    # Search within the selected term by course code or title.
    query = (request.GET.get("q") or "").strip()
    if query:
        courses = courses.filter(Q(code__icontains=query) | Q(title__icontains=query))

    context = {
        "courses": courses,
        "terms": terms,
        "selected_term": selected,
        "current_term": current,
        "q": query,
    }
    # Live search swaps just the course grid.
    if request.htmx:
        return render(request, "accounts/_faculty_courses.html", context)
    return render(request, "accounts/dashboard_faculty.html", context)
