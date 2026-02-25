from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.rentals.models import Rental


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"
    PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"


class PaymentType(models.TextChoices):
    RENTAL = "rental", "Rental Payment"
    DEPOSIT = "deposit", "Security Deposit"
    LATE_FEE = "late_fee", "Late Fee"
    DAMAGE = "damage", "Damage Fee"
    REFUND = "refund", "Refund"


class Payment(BaseModel):
    """Payment record linked to a rental."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    rental = models.ForeignKey(
        Rental,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.RENTAL,
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")

    # Stripe
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_charge_id = models.CharField(max_length=255, blank=True)
    stripe_client_secret = models.CharField(max_length=255, blank=True)

    # Metadata
    failure_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "payment"
        verbose_name_plural = "payments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.id} - {self.amount} {self.currency} ({self.status})"


class StripeWebhookEvent(BaseModel):
    """Log of processed Stripe webhook events (idempotency)."""

    stripe_event_id = models.CharField(max_length=255, unique=True, db_index=True)
    event_type = models.CharField(max_length=255)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "stripe webhook event"
        verbose_name_plural = "stripe webhook events"

    def __str__(self):
        return f"{self.event_type} - {self.stripe_event_id}"
