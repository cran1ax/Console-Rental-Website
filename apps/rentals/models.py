from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify

from apps.core.models import BaseModel


# ═══════════════════════════════════════════════════════════════════
# CHOICES
# ═══════════════════════════════════════════════════════════════════

class ConsoleType(models.TextChoices):
    PS4 = "ps4", "PlayStation 4"
    PS4_SLIM = "ps4_slim", "PlayStation 4 Slim"
    PS4_PRO = "ps4_pro", "PlayStation 4 Pro"
    PS5 = "ps5", "PlayStation 5"
    PS5_DIGITAL = "ps5_digital", "PlayStation 5 Digital Edition"
    PS5_PRO = "ps5_pro", "PlayStation 5 Pro"


class ConditionStatus(models.TextChoices):
    NEW = "new", "Brand New"
    EXCELLENT = "excellent", "Excellent"
    GOOD = "good", "Good"
    FAIR = "fair", "Fair"
    REFURBISHED = "refurbished", "Refurbished"


class Platform(models.TextChoices):
    PS4 = "ps4", "PlayStation 4"
    PS5 = "ps5", "PlayStation 5"
    CROSS_GEN = "cross_gen", "Cross-Gen (PS4 & PS5)"


class Genre(models.TextChoices):
    ACTION = "action", "Action"
    ADVENTURE = "adventure", "Adventure"
    RPG = "rpg", "RPG"
    SPORTS = "sports", "Sports"
    RACING = "racing", "Racing"
    FIGHTING = "fighting", "Fighting"
    SHOOTER = "shooter", "Shooter"
    HORROR = "horror", "Horror"
    PUZZLE = "puzzle", "Puzzle"
    SIMULATION = "simulation", "Simulation"
    STRATEGY = "strategy", "Strategy"
    OTHER = "other", "Other"


class AccessoryCategory(models.TextChoices):
    CONTROLLER = "controller", "Controller"
    VR_HEADSET = "vr_headset", "VR Headset"
    HEADSET = "headset", "Headset"
    CHARGING_DOCK = "charging_dock", "Charging Dock"
    CAMERA = "camera", "Camera"
    STEERING_WHEEL = "steering_wheel", "Steering Wheel"
    OTHER = "other", "Other"


class RentalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    ACTIVE = "active", "Active"
    RETURNED = "returned", "Returned"
    CANCELLED = "cancelled", "Cancelled"
    OVERDUE = "overdue", "Overdue"


# ═══════════════════════════════════════════════════════════════════
# CONSOLE
# ═══════════════════════════════════════════════════════════════════

class Console(BaseModel):
    """PlayStation console available for rent."""

    name = models.CharField("name", max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    console_type = models.CharField(
        "type",
        max_length=20,
        choices=ConsoleType.choices,
    )
    description = models.TextField("description", blank=True)
    condition_status = models.CharField(
        "condition",
        max_length=20,
        choices=ConditionStatus.choices,
        default=ConditionStatus.GOOD,
    )

    # ── Pricing ──────────────────────────────────────────────────
    daily_price = models.DecimalField("daily price (₹)", max_digits=8, decimal_places=2)
    weekly_price = models.DecimalField("weekly price (₹)", max_digits=8, decimal_places=2)
    monthly_price = models.DecimalField("monthly price (₹)", max_digits=8, decimal_places=2)
    security_deposit = models.DecimalField("security deposit (₹)", max_digits=8, decimal_places=2, default=0)

    # ── Inventory ────────────────────────────────────────────────
    stock_quantity = models.PositiveIntegerField("total stock", default=0)
    available_quantity = models.PositiveIntegerField("available stock", default=0)

    # ── Media ────────────────────────────────────────────────────
    image = models.ImageField(upload_to="consoles/%Y/%m/", blank=True, null=True)

    # ── Flags ────────────────────────────────────────────────────
    is_active = models.BooleanField("active", default=True)

    class Meta(BaseModel.Meta):
        verbose_name = "console"
        verbose_name_plural = "consoles"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["console_type"], name="idx_console_type"),
            models.Index(fields=["is_active", "available_quantity"], name="idx_console_availability"),
            models.Index(fields=["daily_price"], name="idx_console_price"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_console_type_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def clean(self):
        if self.available_quantity > self.stock_quantity:
            raise ValidationError(
                {"available_quantity": "Available quantity cannot exceed total stock."}
            )

    @property
    def is_in_stock(self):
        return self.available_quantity > 0


class ConsoleImage(BaseModel):
    """Additional images for a console listing."""

    console = models.ForeignKey(Console, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="consoles/gallery/%Y/%m/")
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta(BaseModel.Meta):
        ordering = ["order"]
        indexes = [
            models.Index(fields=["console", "is_primary"], name="idx_console_img_primary"),
        ]

    def __str__(self):
        return f"Image for {self.console.name} (#{self.order})"


# ═══════════════════════════════════════════════════════════════════
# GAME
# ═══════════════════════════════════════════════════════════════════

class Game(BaseModel):
    """PlayStation game available for rent alongside consoles."""

    title = models.CharField("title", max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    platform = models.CharField(
        "platform",
        max_length=20,
        choices=Platform.choices,
    )
    genre = models.CharField(
        "genre",
        max_length=20,
        choices=Genre.choices,
        default=Genre.ACTION,
    )
    description = models.TextField("description", blank=True)
    rating = models.DecimalField(
        "rating",
        max_digits=3,
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Rating out of 10",
    )

    # ── Pricing ──────────────────────────────────────────────────
    daily_price = models.DecimalField("daily price (₹)", max_digits=8, decimal_places=2)
    weekly_price = models.DecimalField("weekly price (₹)", max_digits=8, decimal_places=2, default=0)

    # ── Inventory ────────────────────────────────────────────────
    stock_quantity = models.PositiveIntegerField("total stock", default=0)
    available_quantity = models.PositiveIntegerField("available stock", default=0)

    # ── Media ────────────────────────────────────────────────────
    cover_image = models.ImageField(upload_to="games/%Y/%m/", blank=True, null=True)

    # ── Flags ────────────────────────────────────────────────────
    is_active = models.BooleanField("active", default=True)

    class Meta(BaseModel.Meta):
        verbose_name = "game"
        verbose_name_plural = "games"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["platform"], name="idx_game_platform"),
            models.Index(fields=["genre"], name="idx_game_genre"),
            models.Index(fields=["is_active", "available_quantity"], name="idx_game_availability"),
            models.Index(fields=["rating"], name="idx_game_rating"),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_platform_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def clean(self):
        if self.available_quantity > self.stock_quantity:
            raise ValidationError(
                {"available_quantity": "Available quantity cannot exceed total stock."}
            )

    @property
    def is_in_stock(self):
        return self.available_quantity > 0


# ═══════════════════════════════════════════════════════════════════
# ACCESSORY
# ═══════════════════════════════════════════════════════════════════

class Accessory(BaseModel):
    """Rental accessories (controllers, VR headsets, etc.)."""

    name = models.CharField("name", max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    category = models.CharField(
        "category",
        max_length=20,
        choices=AccessoryCategory.choices,
    )
    description = models.TextField("description", blank=True)
    compatible_with = models.CharField(
        "compatible with",
        max_length=20,
        choices=Platform.choices,
        default=Platform.CROSS_GEN,
        help_text="Which platform this accessory is compatible with.",
    )

    # ── Pricing ──────────────────────────────────────────────────
    price_per_day = models.DecimalField("price per day (₹)", max_digits=8, decimal_places=2)

    # ── Inventory ────────────────────────────────────────────────
    stock_quantity = models.PositiveIntegerField("total stock", default=0)
    available_quantity = models.PositiveIntegerField("available stock", default=0)

    # ── Media ────────────────────────────────────────────────────
    image = models.ImageField(upload_to="accessories/%Y/%m/", blank=True, null=True)

    # ── Flags ────────────────────────────────────────────────────
    is_active = models.BooleanField("active", default=True)

    class Meta(BaseModel.Meta):
        verbose_name = "accessory"
        verbose_name_plural = "accessories"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category"], name="idx_accessory_category"),
            models.Index(fields=["is_active", "available_quantity"], name="idx_accessory_availability"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def clean(self):
        if self.available_quantity > self.stock_quantity:
            raise ValidationError(
                {"available_quantity": "Available quantity cannot exceed total stock."}
            )

    @property
    def is_in_stock(self):
        return self.available_quantity > 0


# ═══════════════════════════════════════════════════════════════════
# RENTAL
# ═══════════════════════════════════════════════════════════════════

class Rental(BaseModel):
    """A rental booking by a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rentals",
    )
    console = models.ForeignKey(
        Console, on_delete=models.PROTECT, related_name="rentals",
    )
    status = models.CharField(
        max_length=20,
        choices=RentalStatus.choices,
        default=RentalStatus.PENDING,
    )

    # ── Optional add-ons ─────────────────────────────────────────
    games = models.ManyToManyField(Game, blank=True, related_name="rentals")
    accessories = models.ManyToManyField(Accessory, blank=True, related_name="rentals")

    # ── Dates ────────────────────────────────────────────────────
    start_date = models.DateField()
    end_date = models.DateField()
    actual_return_date = models.DateField(blank=True, null=True)

    # ── Pricing (snapshot at booking time) ───────────────────────
    daily_rate = models.DecimalField(max_digits=8, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    security_deposit = models.DecimalField(max_digits=8, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # ── Delivery ─────────────────────────────────────────────────
    delivery_address = models.TextField(blank=True)
    delivery_notes = models.TextField(blank=True)

    # ── Tracking ─────────────────────────────────────────────────
    rental_number = models.CharField(max_length=20, unique=True)

    class Meta(BaseModel.Meta):
        verbose_name = "rental"
        verbose_name_plural = "rentals"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="idx_rental_status"),
            models.Index(fields=["rental_number"], name="idx_rental_number"),
            models.Index(fields=["user", "status"], name="idx_rental_user_status"),
            models.Index(fields=["start_date", "end_date"], name="idx_rental_dates"),
        ]

    def __str__(self):
        return f"Rental #{self.rental_number} – {self.user.email}"

    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days

    @property
    def is_overdue(self):
        from django.utils import timezone
        return (
            self.status == RentalStatus.ACTIVE
            and self.end_date < timezone.now().date()
        )


# ═══════════════════════════════════════════════════════════════════
# REVIEW
# ═══════════════════════════════════════════════════════════════════

class Review(BaseModel):
    """User review for a completed rental."""

    rental = models.OneToOneField(
        Rental, on_delete=models.CASCADE, related_name="review",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    console = models.ForeignKey(
        Console, on_delete=models.CASCADE, related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "review"
        verbose_name_plural = "reviews"
        constraints = [
            models.UniqueConstraint(fields=["user", "rental"], name="unique_user_rental_review"),
        ]
        indexes = [
            models.Index(fields=["console", "rating"], name="idx_review_console_rating"),
        ]

    def __str__(self):
        return f"Review by {self.user.email} – {self.rating}/5"
