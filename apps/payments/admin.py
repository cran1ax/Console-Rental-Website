from django.contrib import admin
from django.utils.html import format_html

from .models import Payment, PaymentStatus, StripeWebhookEvent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "short_id",
        "user",
        "rental_number",
        "payment_type",
        "status_badge",
        "amount",
        "currency",
        "created_at",
    )
    list_filter = ("status", "payment_type", "currency", "created_at")
    search_fields = (
        "user__email",
        "stripe_checkout_session_id",
        "transaction_id",
        "stripe_charge_id",
        "rental__rental_number",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "stripe_checkout_session_id",
        "transaction_id",
        "stripe_charge_id",
        "stripe_customer_id",
    )
    raw_id_fields = ("user", "rental")

    fieldsets = (
        ("Basics", {
            "fields": (
                "user",
                "rental",
                "payment_type",
                "status",
                "amount",
                "currency",
            ),
        }),
        ("Stripe", {
            "fields": (
                "stripe_checkout_session_id",
                "transaction_id",
                "stripe_charge_id",
                "stripe_customer_id",
            ),
            "classes": ("collapse",),
        }),
        ("Metadata", {
            "fields": (
                "failure_reason",
                "metadata",
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="ID")
    def short_id(self, obj):
        return str(obj.id)[:8]

    @admin.display(description="Rental #")
    def rental_number(self, obj):
        return obj.rental.rental_number

    @admin.display(description="Status")
    def status_badge(self, obj):
        colours = {
            PaymentStatus.PENDING: "#ffc107",
            PaymentStatus.PROCESSING: "#17a2b8",
            PaymentStatus.COMPLETED: "#28a745",
            PaymentStatus.FAILED: "#dc3545",
            PaymentStatus.EXPIRED: "#6c757d",
            PaymentStatus.REFUNDED: "#6610f2",
            PaymentStatus.PARTIALLY_REFUNDED: "#fd7e14",
        }
        colour = colours.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;">{}</span>',
            colour,
            obj.get_status_display(),
        )


@admin.register(StripeWebhookEvent)
class StripeWebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "stripe_event_id",
        "event_type",
        "processed_icon",
        "created_at",
    )
    list_filter = ("event_type", "processed", "created_at")
    search_fields = ("stripe_event_id", "event_type")
    readonly_fields = ("created_at", "updated_at", "payload")

    @admin.display(description="OK?", boolean=True)
    def processed_icon(self, obj):
        return obj.processed
