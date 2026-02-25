from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models

from apps.core.models import UUIDModel

from .managers import UserManager


phone_regex = RegexValidator(
    regex=r"^\+?1?\d{9,15}$",
    message="Phone number must be 9-15 digits. Can start with '+'.",
)


class User(UUIDModel, AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for Corner Console.
    Uses email as the unique identifier instead of username.
    """

    # ── Core fields ──────────────────────────────────────────────
    email = models.EmailField(
        "email address",
        unique=True,
        db_index=True,
        error_messages={"unique": "A user with this email already exists."},
    )
    full_name = models.CharField("full name", max_length=255, blank=True)
    phone_number = models.CharField(
        "phone number",
        max_length=17,
        blank=True,
        validators=[phone_regex],
    )
    address = models.TextField("address", blank=True)
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", blank=True, null=True)

    # ── Status flags ─────────────────────────────────────────────
    is_active = models.BooleanField(
        "active",
        default=True,
        help_text="Designates whether this user should be treated as active.",
    )
    is_staff = models.BooleanField(
        "staff status",
        default=False,
        help_text="Designates whether the user can log into the admin site.",
    )
    is_verified = models.BooleanField(
        "verified",
        default=False,
        help_text="Designates whether the user has verified their identity.",
    )

    # ── Timestamps ───────────────────────────────────────────────
    date_joined = models.DateTimeField("date joined", auto_now_add=True)
    updated_at = models.DateTimeField("last updated", auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []  # email & password prompted by default

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["email"], name="idx_user_email"),
            models.Index(fields=["is_active", "is_verified"], name="idx_user_status"),
        ]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.full_name or self.email

    def get_short_name(self):
        return self.full_name.split(" ")[0] if self.full_name else self.email


class UserProfile(models.Model):
    """Extended profile for rental-specific data (ID proof, Stripe, etc.)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # ── ID Verification ──────────────────────────────────────────
    id_proof_type = models.CharField(
        "ID proof type",
        max_length=20,
        choices=[
            ("aadhar", "Aadhar Card"),
            ("pan", "PAN Card"),
            ("passport", "Passport"),
            ("driving_license", "Driving License"),
        ],
        blank=True,
    )
    id_proof_number = models.CharField("ID proof number", max_length=50, blank=True)
    id_proof_document = models.FileField(upload_to="id_proofs/%Y/%m/", blank=True, null=True)

    # ── Stripe ───────────────────────────────────────────────────
    stripe_customer_id = models.CharField(max_length=255, blank=True, db_index=True)

    # ── Timestamps ───────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "user profile"
        verbose_name_plural = "user profiles"

    def __str__(self):
        return f"Profile: {self.user.email}"
