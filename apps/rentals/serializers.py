from django.db import models
from rest_framework import serializers

from .models import Console, ConsoleImage, Rental, Review


class ConsoleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsoleImage
        fields = ["id", "image", "alt_text", "is_primary", "order"]


class ConsoleListSerializer(serializers.ModelSerializer):
    console_type_display = serializers.CharField(
        source="get_console_type_display", read_only=True
    )
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Console
        fields = [
            "id",
            "name",
            "slug",
            "console_type",
            "console_type_display",
            "condition",
            "daily_rate",
            "weekly_rate",
            "monthly_rate",
            "security_deposit",
            "is_available",
            "includes_controller",
            "includes_games",
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
    console_type_display = serializers.CharField(
        source="get_console_type_display", read_only=True
    )
    images = ConsoleImageSerializer(many=True, read_only=True)
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
            "condition",
            "daily_rate",
            "weekly_rate",
            "monthly_rate",
            "security_deposit",
            "is_available",
            "includes_controller",
            "includes_games",
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


class RentalCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rental
        fields = [
            "console",
            "start_date",
            "end_date",
            "delivery_address",
            "delivery_notes",
        ]

    def validate(self, data):
        if data["start_date"] >= data["end_date"]:
            raise serializers.ValidationError(
                "End date must be after start date."
            )
        if not data["console"].is_available:
            raise serializers.ValidationError(
                "This console is not currently available for rent."
            )
        return data


class RentalListSerializer(serializers.ModelSerializer):
    console_name = serializers.CharField(source="console.name", read_only=True)
    duration_days = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )

    class Meta:
        model = Rental
        fields = [
            "id",
            "rental_number",
            "console",
            "console_name",
            "status",
            "status_display",
            "start_date",
            "end_date",
            "duration_days",
            "total_amount",
            "security_deposit",
            "created_at",
        ]


class RentalDetailSerializer(serializers.ModelSerializer):
    console = ConsoleListSerializer(read_only=True)
    duration_days = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Rental
        fields = [
            "id",
            "rental_number",
            "console",
            "status",
            "status_display",
            "start_date",
            "end_date",
            "actual_return_date",
            "duration_days",
            "daily_rate",
            "total_amount",
            "security_deposit",
            "discount_amount",
            "delivery_address",
            "delivery_notes",
            "is_overdue",
            "created_at",
            "updated_at",
        ]


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "rental",
            "rating",
            "comment",
            "user_name",
            "created_at",
        ]
        read_only_fields = ["id", "user_name", "created_at"]

    def get_user_name(self, obj):
        return obj.user.get_full_name()

    def validate_rental(self, value):
        from .models import RentalStatus

        if value.status != RentalStatus.RETURNED:
            raise serializers.ValidationError(
                "You can only review returned rentals."
            )
        if hasattr(value, "review"):
            raise serializers.ValidationError(
                "You have already reviewed this rental."
            )
        return value
