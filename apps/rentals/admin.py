from django.contrib import admin

from .models import Console, ConsoleImage, Rental, Review


class ConsoleImageInline(admin.TabularInline):
    model = ConsoleImage
    extra = 1


@admin.register(Console)
class ConsoleAdmin(admin.ModelAdmin):
    inlines = [ConsoleImageInline]
    list_display = (
        "name",
        "console_type",
        "condition",
        "daily_rate",
        "is_available",
        "is_active",
        "created_at",
    )
    list_filter = ("console_type", "condition", "is_available", "is_active")
    search_fields = ("name", "serial_number", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")


@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = (
        "rental_number",
        "user",
        "console",
        "status",
        "start_date",
        "end_date",
        "total_amount",
        "created_at",
    )
    list_filter = ("status", "start_date", "end_date", "created_at")
    search_fields = ("rental_number", "user__email", "console__name")
    readonly_fields = ("created_at", "updated_at", "rental_number")
    raw_id_fields = ("user", "console")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "console", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("user__email", "console__name", "comment")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("user", "rental", "console")
