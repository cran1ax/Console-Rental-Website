from django.db import models
from rest_framework import serializers

from .models import (
    Accessory,
    Console,
    ConsoleImage,
    DeliveryOption,
    Game,
    Rental,
    RentalType,
    Review,
)


# ═══════════════════════════════════════════════════════════════════
# CONSOLE
# ═══════════════════════════════════════════════════════════════════

class ConsoleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsoleImage
        fields = ["id", "image", "alt_text", "is_primary", "order"]


class ConsoleListSerializer(serializers.ModelSerializer):
    console_type_display = serializers.CharField(source="get_console_type_display", read_only=True)
    condition_display = serializers.CharField(source="get_condition_status_display", read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Console
        fields = [
            "id",
            "name",
            "slug",
            "console_type",
            "console_type_display",
            "condition_status",
            "condition_display",
            "daily_price",
            "weekly_price",
            "monthly_price",
            "security_deposit",
            "stock_quantity",
            "available_quantity",
            "is_in_stock",
            "primary_image",
        ]

    def get_primary_image(self, obj):
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            return ConsoleImageSerializer(primary).data
        if obj.image:
            return {"image": obj.image.url}
        return None


class ConsoleDetailSerializer(serializers.ModelSerializer):
    console_type_display = serializers.CharField(source="get_console_type_display", read_only=True)
    condition_display = serializers.CharField(source="get_condition_status_display", read_only=True)
    images = ConsoleImageSerializer(many=True, read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Console
        fields = [
            "id",
            "name",
            "slug",
            "console_type",
            "console_type_display",
            "description",
            "condition_status",
            "condition_display",
            "daily_price",
            "weekly_price",
            "monthly_price",
            "security_deposit",
            "stock_quantity",
            "available_quantity",
            "is_in_stock",
            "image",
            "images",
            "average_rating",
            "review_count",
            "created_at",
        ]

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews.exists():
            return round(reviews.aggregate(avg=models.Avg("rating"))["avg"], 1)
        return None

    def get_review_count(self, obj):
        return obj.reviews.count()


# ═══════════════════════════════════════════════════════════════════
# GAME
# ═══════════════════════════════════════════════════════════════════

class GameListSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(source="get_platform_display", read_only=True)
    genre_display = serializers.CharField(source="get_genre_display", read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Game
        fields = [
            "id",
            "title",
            "slug",
            "platform",
            "platform_display",
            "genre",
            "genre_display",
            "rating",
            "daily_price",
            "weekly_price",
            "stock_quantity",
            "available_quantity",
            "is_in_stock",
            "cover_image",
        ]


class GameDetailSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(source="get_platform_display", read_only=True)
    genre_display = serializers.CharField(source="get_genre_display", read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Game
        fields = [
            "id",
            "title",
            "slug",
            "platform",
            "platform_display",
            "genre",
            "genre_display",
            "description",
            "rating",
            "daily_price",
            "weekly_price",
            "stock_quantity",
            "available_quantity",
            "is_in_stock",
            "cover_image",
            "created_at",
        ]


# ═══════════════════════════════════════════════════════════════════
# ACCESSORY
# ═══════════════════════════════════════════════════════════════════

class AccessorySerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    compatible_with_display = serializers.CharField(source="get_compatible_with_display", read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Accessory
        fields = [
            "id",
            "name",
            "slug",
            "category",
            "category_display",
            "compatible_with",
            "compatible_with_display",
            "description",
            "price_per_day",
            "stock_quantity",
            "available_quantity",
            "is_in_stock",
            "image",
        ]


# ═══════════════════════════════════════════════════════════════════
# RENTAL
# ═══════════════════════════════════════════════════════════════════

class RentalCreateSerializer(serializers.Serializer):
    """
    Accepts rental input and delegates to the service layer.
    This is a plain Serializer (not ModelSerializer) because creation
    is fully handled by ``rental_service.create_rental``.
    """

    console = serializers.PrimaryKeyRelatedField(
        queryset=Console.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    game_ids = serializers.PrimaryKeyRelatedField(
        queryset=Game.objects.filter(is_active=True),
        many=True,
        required=False,
    )
    accessory_ids = serializers.PrimaryKeyRelatedField(
        queryset=Accessory.objects.filter(is_active=True),
        many=True,
        required=False,
    )
    rental_type = serializers.ChoiceField(
        choices=RentalType.choices,
        default=RentalType.DAILY,
    )
    rental_start_date = serializers.DateField()
    rental_end_date = serializers.DateField()
    delivery_option = serializers.ChoiceField(
        choices=DeliveryOption.choices,
        default=DeliveryOption.PICKUP,
    )
    delivery_address = serializers.CharField(required=False, allow_blank=True, default="")
    delivery_notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, data):
        if data["rental_start_date"] >= data["rental_end_date"]:
            raise serializers.ValidationError(
                {"rental_end_date": "End date must be after start date."}
            )

        console = data.get("console")
        games = data.get("game_ids", [])
        accessories = data.get("accessory_ids", [])

        if not console and not games and not accessories:
            raise serializers.ValidationError(
                "At least a console, game, or accessory is required."
            )

        # ── Date-aware availability check (prevents double-bookings) ──
        from . import availability_service

        result = availability_service.check_bulk_availability(
            console=console,
            games=games,
            accessories=accessories,
            start=data["rental_start_date"],
            end=data["rental_end_date"],
        )
        if not result.all_available:
            errors = {}
            if result.console and not result.console.is_available:
                errors["console"] = result.console.reason
            unavail_games = [g for g in result.games if not g.is_available]
            if unavail_games:
                errors["game_ids"] = [g.reason for g in unavail_games]
            unavail_accs = [a for a in result.accessories if not a.is_available]
            if unavail_accs:
                errors["accessory_ids"] = [a.reason for a in unavail_accs]
            raise serializers.ValidationError(errors or "Selected items are not available.")

        if (
            data.get("delivery_option") == DeliveryOption.HOME_DELIVERY
            and not data.get("delivery_address")
        ):
            raise serializers.ValidationError(
                {"delivery_address": "Required for home delivery."}
            )

        return data


class RentalListSerializer(serializers.ModelSerializer):
    console_name = serializers.CharField(source="console.name", read_only=True, default=None)
    duration_days = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    rental_type_display = serializers.CharField(source="get_rental_type_display", read_only=True)
    delivery_option_display = serializers.CharField(source="get_delivery_option_display", read_only=True)
    payment_status_display = serializers.CharField(source="get_payment_status_display", read_only=True)

    class Meta:
        model = Rental
        fields = [
            "id",
            "rental_number",
            "console",
            "console_name",
            "rental_type",
            "rental_type_display",
            "status",
            "status_display",
            "rental_start_date",
            "rental_end_date",
            "duration_days",
            "total_price",
            "deposit_amount",
            "late_fee",
            "delivery_option",
            "delivery_option_display",
            "payment_status",
            "payment_status_display",
            "created_at",
        ]


class RentalDetailSerializer(serializers.ModelSerializer):
    console = ConsoleListSerializer(read_only=True)
    games = GameListSerializer(many=True, read_only=True)
    accessories = AccessorySerializer(many=True, read_only=True)
    duration_days = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    rental_type_display = serializers.CharField(source="get_rental_type_display", read_only=True)
    delivery_option_display = serializers.CharField(source="get_delivery_option_display", read_only=True)
    payment_status_display = serializers.CharField(source="get_payment_status_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    overdue_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = Rental
        fields = [
            "id",
            "rental_number",
            "console",
            "games",
            "accessories",
            "rental_type",
            "rental_type_display",
            "status",
            "status_display",
            "rental_start_date",
            "rental_end_date",
            "actual_return_date",
            "duration_days",
            "daily_rate",
            "total_price",
            "deposit_amount",
            "discount_amount",
            "late_fee",
            "delivery_option",
            "delivery_option_display",
            "delivery_address",
            "delivery_notes",
            "payment_status",
            "payment_status_display",
            "is_overdue",
            "overdue_days",
            "created_at",
            "updated_at",
        ]


# ═══════════════════════════════════════════════════════════════════
# REVIEW
# ═══════════════════════════════════════════════════════════════════

class ReviewCreateSerializer(serializers.Serializer):
    """
    Input serializer for creating a review.

    Validation is intentionally *thin* — heavy business-rule checks
    (rental ownership, returned status, duplicate) live in
    ``review_service.create_review()``.
    """

    rental_id = serializers.PrimaryKeyRelatedField(
        queryset=Rental.objects.all(),
        source="rental",
        help_text="UUID of the completed rental to review.",
    )
    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        help_text="1 = terrible, 5 = excellent.",
    )
    title = serializers.CharField(
        max_length=150,
        required=False,
        default="",
        help_text="Optional headline for the review.",
    )
    comment = serializers.CharField(
        required=False,
        default="",
        help_text="Detailed review text.",
    )


class ReviewUpdateSerializer(serializers.Serializer):
    """Input serializer for editing an existing review."""

    rating = serializers.IntegerField(
        min_value=1, max_value=5, required=False,
    )
    title = serializers.CharField(
        max_length=150, required=False, allow_blank=True,
    )
    comment = serializers.CharField(
        required=False, allow_blank=True,
    )


class ReviewListSerializer(serializers.ModelSerializer):
    """Compact output for review listings (e.g. console detail page)."""

    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    console_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "rental",
            "console",
            "console_name",
            "title",
            "rating",
            "comment",
            "is_verified",
            "helpful_count",
            "user_name",
            "created_at",
        ]

    def get_console_name(self, obj):
        return obj.console.name if obj.console else None


class ReviewDetailSerializer(serializers.ModelSerializer):
    """Full review detail with rental context."""

    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    rental_number = serializers.CharField(source="rental.rental_number", read_only=True)
    console_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "rental",
            "rental_number",
            "console",
            "console_name",
            "user_name",
            "user_email",
            "title",
            "rating",
            "comment",
            "is_verified",
            "helpful_count",
            "created_at",
            "updated_at",
        ]

    def get_console_name(self, obj):
        return obj.console.name if obj.console else None


class ReviewStatsSerializer(serializers.Serializer):
    """Output for aggregate console review stats."""

    average_rating = serializers.FloatField(allow_null=True)
    total_reviews = serializers.IntegerField()
    rating_breakdown = serializers.DictField(
        child=serializers.IntegerField(),
    )


class ReviewableRentalSerializer(serializers.ModelSerializer):
    """Compact rental info for the 'reviewable rentals' endpoint."""

    console_name = serializers.SerializerMethodField()

    class Meta:
        model = Rental
        fields = [
            "id",
            "rental_number",
            "console",
            "console_name",
            "rental_start_date",
            "rental_end_date",
            "actual_return_date",
        ]

    def get_console_name(self, obj):
        return obj.console.name if obj.console else None


# ═══════════════════════════════════════════════════════════════════
# AVAILABILITY
# ═══════════════════════════════════════════════════════════════════

class AvailabilityCheckSerializer(serializers.Serializer):
    """
    Input serializer for the availability check endpoint.

    At minimum the caller must provide a date range.  Item IDs are optional —
    if only dates are given the response just confirms the dates are valid.
    """

    console_id = serializers.PrimaryKeyRelatedField(
        queryset=Console.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        help_text="Console to check.",
    )
    game_ids = serializers.PrimaryKeyRelatedField(
        queryset=Game.objects.filter(is_active=True),
        many=True,
        required=False,
        help_text="Games to check.",
    )
    accessory_ids = serializers.PrimaryKeyRelatedField(
        queryset=Accessory.objects.filter(is_active=True),
        many=True,
        required=False,
        help_text="Accessories to check.",
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, data):
        if data["start_date"] >= data["end_date"]:
            raise serializers.ValidationError(
                {"end_date": "End date must be after start date."}
            )
        return data


class AvailabilityItemSerializer(serializers.Serializer):
    """Read-only serializer for a single AvailabilityResult dataclass."""

    item_id = serializers.UUIDField()
    item_type = serializers.CharField()
    item_name = serializers.CharField()
    is_available = serializers.BooleanField()
    stock_quantity = serializers.IntegerField()
    overlapping_rentals = serializers.IntegerField()
    available_for_dates = serializers.IntegerField()
    reason = serializers.CharField()


class BulkAvailabilitySerializer(serializers.Serializer):
    """Read-only serializer for BulkAvailabilityResult."""

    all_available = serializers.BooleanField()
    console = AvailabilityItemSerializer(allow_null=True)
    games = AvailabilityItemSerializer(many=True)
    accessories = AvailabilityItemSerializer(many=True)
