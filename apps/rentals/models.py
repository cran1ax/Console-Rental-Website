from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import BaseModel


class ConsoleType(models.TextChoices):
    PS4 = "ps4", "PlayStation 4"
    PS4_PRO = "ps4_pro", "PlayStation 4 Pro"
    PS5 = "ps5", "PlayStation 5"
    PS5_DIGITAL = "ps5_digital", "PlayStation 5 Digital Edition"


class ConsoleCondition(models.TextChoices):
    EXCELLENT = "excellent", "Excellent"
    GOOD = "good", "Good"
    FAIR = "fair", "Fair"


class RentalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    ACTIVE = "active", "Active"
    RETURNED = "returned", "Returned"
    CANCELLED = "cancelled", "Cancelled"
    OVERDUE = "overdue", "Overdue"


class Console(BaseModel):
    """PlayStation console available for rent."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    console_type = models.CharField(
        max_length=20,
        choices=ConsoleType.choices,
        db_index=True,
    )
    description = models.TextField(blank=True)
    condition = models.CharField(
        max_length=20,
        choices=ConsoleCondition.choices,
        default=ConsoleCondition.GOOD,
    )
    serial_number = models.CharField(max_length=100, unique=True)

    # Pricing
    daily_rate = models.DecimalField(max_digits=8, decimal_places=2)
    weekly_rate = models.DecimalField(max_digits=8, decimal_places=2)
    monthly_rate = models.DecimalField(max_digits=8, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=8, decimal_places=2)

    # Availability
    is_available = models.BooleanField(default=True, db_index=True)
    is_active = models.BooleanField(default=True)

    # Accessories
    includes_controller = models.PositiveSmallIntegerField(default=1)
    includes_games = models.BooleanField(default=False)

    # Images
    image = models.ImageField(upload_to="consoles/", blank=True, null=True)

    class Meta(BaseModel.Meta):
        verbose_name = "console"
        verbose_name_plural = "consoles"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_console_type_display()})"


class ConsoleImage(BaseModel):
    """Additional images for a console."""

    console = models.ForeignKey(
        Console, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="consoles/gallery/")
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta(BaseModel.Meta):
        ordering = ["order"]

    def __str__(self):
        return f"Image for {self.console.name}"


class Rental(BaseModel):
    """A rental booking by a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rentals",
    )
    console = models.ForeignKey(
        Console, on_delete=models.PROTECT, related_name="rentals"
    )
    status = models.CharField(
        max_length=20,
        choices=RentalStatus.choices,
        default=RentalStatus.PENDING,
        db_index=True,
    )

    # Dates
    start_date = models.DateField()
    end_date = models.DateField()
    actual_return_date = models.DateField(blank=True, null=True)

    # Pricing (snapshot at booking time)
    daily_rate = models.DecimalField(max_digits=8, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=8, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Delivery
    delivery_address = models.TextField(blank=True)
    delivery_notes = models.TextField(blank=True)

    # Tracking
    rental_number = models.CharField(max_length=20, unique=True, db_index=True)

    class Meta(BaseModel.Meta):
        verbose_name = "rental"
        verbose_name_plural = "rentals"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Rental #{self.rental_number} - {self.user.email}"

    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days

    @property
    def is_overdue(self):
        from django.utils import timezone

        if self.status == RentalStatus.ACTIVE and self.end_date < timezone.now().date():
            return True
        return False


class Review(BaseModel):
    """User review for a completed rental."""

    rental = models.OneToOneField(
        Rental, on_delete=models.CASCADE, related_name="review"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    console = models.ForeignKey(
        Console, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "review"
        verbose_name_plural = "reviews"
        unique_together = ["user", "rental"]

    def __str__(self):
        return f"Review by {self.user.email} - {self.rating}/5"
