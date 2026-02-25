from django.contrib import admin
from django.utils.html import format_html

from .models import Accessory, Console, ConsoleImage, Game, Rental, Review


# ═══════════════════════════════════════════════════════════════════
# CONSOLE
# ═══════════════════════════════════════════════════════════════════

class ConsoleImageInline(admin.TabularInline):
    model = ConsoleImage
    extra = 1
    fields = ("image", "alt_text", "is_primary", "order")


@admin.register(Console)
class ConsoleAdmin(admin.ModelAdmin):
    inlines = [ConsoleImageInline]

    list_display = (
        "name",
        "console_type",
        "condition_status",
        "daily_price",
        "stock_quantity",
        "available_quantity",
        "stock_badge",
        "is_active",
        "created_at",
    )
    list_filter = ("console_type", "condition_status", "is_active", "created_at")
    list_editable = ("is_active",)
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("name", "slug", "console_type", "description", "condition_status")}),
        ("Pricing", {"fields": ("daily_price", "weekly_price", "monthly_price", "security_deposit")}),
        ("Inventory", {"fields": ("stock_quantity", "available_quantity")}),
        ("Media", {"fields": ("image",)}),
        ("Status", {"fields": ("is_active",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Stock")
    def stock_badge(self, obj):
        if obj.available_quantity == 0:
            color = "#dc3545"
            label = "Out of stock"
        elif obj.available_quantity <= 2:
            color = "#ffc107"
            label = f"{obj.available_quantity} left"
        else:
            color = "#28a745"
            label = f"{obj.available_quantity} available"
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>', color, label
        )


# ═══════════════════════════════════════════════════════════════════
# GAME
# ═══════════════════════════════════════════════════════════════════

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "platform",
        "genre",
        "rating",
        "daily_price",
        "stock_quantity",
        "available_quantity",
        "is_active",
        "created_at",
    )
    list_filter = ("platform", "genre", "is_active", "created_at")
    list_editable = ("is_active",)
    search_fields = ("title", "slug", "description")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("title", "slug", "platform", "genre", "description", "rating")}),
        ("Pricing", {"fields": ("daily_price", "weekly_price")}),
        ("Inventory", {"fields": ("stock_quantity", "available_quantity")}),
        ("Media", {"fields": ("cover_image",)}),
        ("Status", {"fields": ("is_active",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


# ═══════════════════════════════════════════════════════════════════
# ACCESSORY
# ═══════════════════════════════════════════════════════════════════

@admin.register(Accessory)
class AccessoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "compatible_with",
        "price_per_day",
        "stock_quantity",
        "available_quantity",
        "is_active",
        "created_at",
    )
    list_filter = ("category", "compatible_with", "is_active", "created_at")
    list_editable = ("is_active",)
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("name", "slug", "category", "compatible_with", "description")}),
        ("Pricing", {"fields": ("price_per_day",)}),
        ("Inventory", {"fields": ("stock_quantity", "available_quantity")}),
        ("Media", {"fields": ("image",)}),
        ("Status", {"fields": ("is_active",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


# ═══════════════════════════════════════════════════════════════════
# RENTAL
# ═══════════════════════════════════════════════════════════════════

@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = (
        "rental_number",
        "user",
        "console",
        "rental_type",
        "status",
        "payment_status",
        "delivery_option",
        "rental_start_date",
        "rental_end_date",
        "total_price",
        "late_fee",
        "created_at",
    )
    list_filter = (
        "status",
        "rental_type",
        "payment_status",
        "delivery_option",
        "rental_start_date",
        "rental_end_date",
        "created_at",
    )
    list_editable = ("status", "payment_status")
    search_fields = ("rental_number", "user__email", "console__name")
    readonly_fields = ("created_at", "updated_at", "rental_number", "late_fee")
    raw_id_fields = ("user", "console")
    filter_horizontal = ("games", "accessories")

    fieldsets = (
        (None, {"fields": ("rental_number", "user", "console")}),
        ("Items", {"fields": ("games", "accessories")}),
        ("Configuration", {"fields": ("rental_type", "status", "payment_status")}),
        ("Dates", {"fields": ("rental_start_date", "rental_end_date", "actual_return_date")}),
        ("Pricing", {"fields": ("daily_rate", "total_price", "deposit_amount", "discount_amount", "late_fee")}),
        ("Delivery", {"fields": ("delivery_option", "delivery_address", "delivery_notes")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


# ═══════════════════════════════════════════════════════════════════
# REVIEW
# ═══════════════════════════════════════════════════════════════════

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "console", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("user__email", "console__name", "comment")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("user", "rental", "console")
