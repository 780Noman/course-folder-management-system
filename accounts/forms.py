"""Forms for account management (admin create/change + faculty invites)."""

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class InviteForm(forms.ModelForm):
    """Admin-facing form to invite a user by name + email (no password here).

    The invited user receives a one-time link and sets their own password, so
    this form never collects or stores a password.
    """

    class Meta:
        model = User
        fields = ("name", "email", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        widget_classes = (
            "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 "
            "text-sm shadow-sm focus:border-gray-900 focus:outline-none "
            "focus:ring-1 focus:ring-gray-900"
        )
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", widget_classes)

    def clean_email(self):
        # Stored and compared case-insensitively to avoid duplicate accounts.
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email


class AdminUserCreationForm(UserCreationForm):
    """Create-user form used in the Django admin (sets a password directly)."""

    class Meta:
        model = User
        fields = ("email", "name", "role")
        field_classes = {"email": forms.EmailField}


class AdminUserChangeForm(UserChangeForm):
    """Change-user form used in the Django admin."""

    class Meta:
        model = User
        fields = ("email", "name", "role", "is_active", "is_staff",
                  "is_superuser", "groups", "user_permissions")
