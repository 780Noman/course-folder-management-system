"""Authentication and dashboard views."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordResetConfirmView
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from audit.services import record

from . import ratelimit
from .emails import send_email_changed_notice
from .forms import InviteForm, SetUserPasswordForm, UserEditForm
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


def admin_login(request, extra_context=None):
    """Django admin's login wrapped with the same (IP, email) throttling as
    the main login page, so staff accounts can't be brute-forced via /admin/.

    Routed at admin/login/ ahead of the admin site's own URLs.
    """
    from django.contrib import admin as django_admin
    from django.contrib.auth.forms import AuthenticationForm

    email = request.POST.get("username", "")
    if request.method == "POST" and ratelimit.is_locked(request, email):
        minutes = max(1, settings.LOGIN_LOCKOUT_SECONDS // 60)
        return render(
            request,
            "accounts/login.html",
            {
                "form": AuthenticationForm(request),
                "locked": True,
                "lockout_minutes": minutes,
            },
            status=429,
        )
    response = django_admin.site.login(request, extra_context)
    if request.method == "POST":
        if request.user.is_authenticated:
            ratelimit.clear_failures(request, email)
        else:
            ratelimit.record_failure(request, email)
    return response


@admin_required
def invite_user(request):
    """Admin creates a user with an initial password (offline: no email sent).

    The admin shares the password with the user, who can change it afterwards
    from their account. The raw password is never logged.
    """
    if request.method == "POST":
        form = InviteForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            with transaction.atomic():
                user.save()
                record(
                    request.user, "user_invite", user,
                    email=user.email, role=user.role,
                )
            messages.success(
                request,
                f"Account created for {user.name} ({user.email}). "
                "Share the password you set; they can change it after signing in.",
            )
            return redirect("faculty_list")
    else:
        form = InviteForm()
    return render(request, "accounts/invite_form.html", {"form": form})


@admin_required
def faculty_set_password(request, pk):
    """Admin sets/resets a user's password (offline password recovery)."""
    member = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = SetUserPasswordForm(request.POST, user=member)
        if form.is_valid():
            with transaction.atomic():
                member.set_password(form.cleaned_data["password"])
                member.save(update_fields=["password"])
                record(request.user, "user_set_password", member, email=member.email)
            messages.success(
                request,
                f"Password reset for {member.name} ({member.email}). "
                "Share it; they can change it after signing in.",
            )
            return redirect("faculty_list")
    else:
        form = SetUserPasswordForm(user=member)
    return render(
        request,
        "accounts/set_faculty_password.html",
        {"form": form, "member": member},
    )


class InviteSetPasswordView(PasswordResetConfirmView):
    """The invited user sets their own password via a one-time link, then is
    logged in. Reuses Django's token validation (single-use + expiring). Kept
    for the online/email path; the offline flow uses admin-set passwords."""

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
    record(request.user,
           "faculty_activate" if member.is_active else "faculty_deactivate",
           member)
    messages.success(request, f"{member.name} {state}.")
    return redirect("faculty_list")


@admin_required
def faculty_edit(request, pk):
    """Admin edits a faculty member's display name and login email.

    Email is admin-only (faculty cannot change their own), so this is where a
    mistyped address gets corrected. A changed email updates the login
    immediately; the faculty keeps their session and password, sees the new
    address in their own account view, and is notified by email (best effort).
    """
    member = get_object_or_404(User, pk=pk, role=User.Role.FACULTY)
    if request.method == "POST":
        form = UserEditForm(request.POST, instance=member)
        if form.is_valid():
            old_email = User.objects.values_list("email", flat=True).get(pk=member.pk)
            with transaction.atomic():
                form.save()
                email_changed = member.email != old_email
                record(request.user, "faculty_edit", member,
                       name=member.name, email=member.email,
                       old_email=old_email if email_changed else "")
            if email_changed:
                send_email_changed_notice(member, old_email)
                messages.success(
                    request,
                    f"{member.name}'s details updated. New login email: "
                    f"{member.email}. They have been notified — please also "
                    f"share it with them directly.",
                )
            else:
                messages.success(request, f"{member.name}'s details updated.")
            return redirect("faculty_list")
    else:
        form = UserEditForm(instance=member)
    return render(
        request, "accounts/faculty_edit.html", {"form": form, "member": member}
    )


@admin_required
def faculty_delete(request, pk):
    """Confirm and (only when safe) permanently delete a faculty member.

    Faculty with any course on record cannot be hard-deleted: the instructor FK
    is PROTECTed and deleting would destroy folders, files, and certificates.
    The admin is steered to Deactivate (soft-delete) or reassignment instead. A
    hard delete is offered only when nothing is linked, and needs an explicit
    typed confirmation.
    """
    from folders.models import CourseFolder, ItemFile
    from review.models import Certificate

    member = get_object_or_404(User, pk=pk, role=User.Role.FACULTY)
    courses = member.courses.select_related("term").all()
    course_count = courses.count()
    folder_count = CourseFolder.objects.filter(course__instructor=member).count()
    file_count = ItemFile.objects.filter(
        item__folder__course__instructor=member
    ).count()
    cert_count = Certificate.objects.filter(
        folder__course__instructor=member
    ).count()
    can_hard_delete = course_count == 0

    if request.method == "POST":
        if not can_hard_delete:
            messages.error(
                request,
                f"{member.name} has {course_count} course(s) on record and "
                f"cannot be permanently deleted (that would erase folders and "
                f"certificates). Deactivate them to keep the history, or "
                f"reassign their courses first.",
            )
            return redirect("faculty_list")
        if request.POST.get("confirm") != "DELETE":
            messages.error(request, "Type DELETE to confirm permanent deletion.")
            return redirect("faculty_delete", pk=pk)
        name, email = member.name, member.email
        with transaction.atomic():
            record(request.user, "faculty_delete", member, name=name, email=email)
            member.delete()
        messages.success(request, f"{name} ({email}) was permanently deleted.")
        return redirect("faculty_list")

    return render(
        request,
        "accounts/faculty_delete.html",
        {
            "member": member,
            "courses": courses,
            "course_count": course_count,
            "folder_count": folder_count,
            "file_count": file_count,
            "cert_count": cert_count,
            "can_hard_delete": can_hard_delete,
        },
    )


@login_required
def profile(request):
    """Each user's own account page.

    Admins may correct their own name and login email here. Faculty see their
    details read-only (email is admin-managed) with a link to change their
    password — enforced server-side so a crafted POST from a faculty user can
    never change their email.
    """
    user = request.user
    if request.method == "POST":
        if not user.is_admin:
            raise PermissionDenied
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            old_email = User.objects.values_list("email", flat=True).get(pk=user.pk)
            with transaction.atomic():
                form.save()
                if user.email != old_email:
                    record(user, "user_email_change", user,
                           old_email=old_email, new_email=user.email)
            messages.success(request, "Your account details were updated.")
            return redirect("profile")
    else:
        form = UserEditForm(instance=user) if user.is_admin else None
    return render(request, "accounts/profile.html", {"form": form})


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
        user.courses.filter(term=selected).select_related("term", "folder")
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
