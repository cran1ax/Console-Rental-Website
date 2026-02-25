from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("ID Verification", {"fields": ("id_proof_type", "id_proof_number", "id_proof_document")}),
        ("Stripe", {"fields": ("stripe_customer_id",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]

    # ── List view ────────────────────────────────────────────────
    list_display = (
        "email",
        "full_name",
        "phone_number",
        "is_active",
        "is_staff",
        "is_verified",
        "date_joined",
    )
    list_filter = ("is_active", "is_staff", "is_verified", "is_superuser", "date_joined")
    list_editable = ("is_verified",)
    search_fields = ("email", "full_name", "phone_number")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "updated_at", "last_login")

    # ── Detail view ──────────────────────────────────────────────
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal Info"), {"fields": ("full_name", "phone_number", "address", "avatar")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_verified",
                    "groups",
                    "user_permissions",
                ),
                "classes": ("collapse",),
            },
        ),
        (_("Important Dates"), {"fields": ("date_joined", "updated_at", "last_login")}),
    )

    # ── Add user form ────────────────────────────────────────────
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "password1", "password2"),
            },
        ),
    )

    # Override: no username field
    filter_horizontal = ("groups", "user_permissions")
