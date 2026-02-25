from django.contrib import admin

from .models import Payment, StripeWebhookEvent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "rental",
        "payment_type",
        "status",
        "amount",
        "currency",
        "created_at",
    )
    list_filter = ("status", "payment_type", "currency", "created_at")
    search_fields = (
        "user__email",
        "stripe_payment_intent_id",
        "stripe_charge_id",
        "rental__rental_number",
    )
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("user", "rental")


@admin.register(StripeWebhookEvent)
class StripeWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("stripe_event_id", "event_type", "processed", "created_at")
    list_filter = ("event_type", "processed", "created_at")
    search_fields = ("stripe_event_id", "event_type")
    readonly_fields = ("created_at", "updated_at", "payload")
