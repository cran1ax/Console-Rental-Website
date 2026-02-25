from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.rentals.models import Rental


# ═══════════════════════════════════════════════════════════════════
# CHOICES
# ═══════════════════════════════════════════════════════════════════

class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    EXPIRED = "expired", "Expired"
    REFUNDED = "refunded", "Refunded"
    PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"


class PaymentType(models.TextChoices):
    RENTAL = "rental", "Rental Payment"
    DEPOSIT = "deposit", "Security Deposit"
    LATE_FEE = "late_fee", "Late Fee"
    DAMAGE = "damage", "Damage Fee"
    REFUND = "refund", "Refund"


# ═══════════════════════════════════════════════════════════════════
# PAYMENT
# ═══════════════════════════════════════════════════════════════════

class Payment(BaseModel):
    """
    Payment record linked to a rental.

    Uses Stripe *Checkout Sessions* as the primary flow.
    The ``transaction_id`` stores the Stripe PaymentIntent ID returned
    after checkout completes, and serves as the authoritative reference
    for refunds and dispute lookups.
    """

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

    # ── Stripe identifiers ───────────────────────────────────────
    stripe_checkout_session_id = models.CharField(
        "Stripe Checkout Session ID",
        max_length=255,
        blank=True,
        db_index=True,
        help_text="cs_xxx — created when the checkout session is initiated.",
    )
    transaction_id = models.CharField(
        "Stripe PaymentIntent / Transaction ID",
        max_length=255,
        blank=True,
        db_index=True,
        help_text="pi_xxx — populated once payment succeeds via webhook.",
    )
    stripe_charge_id = models.CharField(
        "Stripe Charge ID",
        max_length=255,
        blank=True,
        help_text="ch_xxx — populated from the successful charge.",
    )
    stripe_customer_id = models.CharField(
        "Stripe Customer ID",
        max_length=255,
        blank=True,
        help_text="cus_xxx — the customer who paid.",
    )

    # ── Metadata ─────────────────────────────────────────────────
    failure_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "payment"
        verbose_name_plural = "payments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["rental", "status"],
                name="idx_payment_rental_status",
            ),
        ]

    def __str__(self):
        return (
            f"Payment {self.id} – ₹{self.amount} "
            f"({self.get_status_display()})"
        )

    @property
    def is_successful(self):
        return self.status == PaymentStatus.COMPLETED

    @property
    def is_refundable(self):
        return self.status in (
            PaymentStatus.COMPLETED,
            PaymentStatus.PARTIALLY_REFUNDED,
        ) and bool(self.transaction_id)


# ═══════════════════════════════════════════════════════════════════
# STRIPE WEBHOOK EVENT  (idempotency log)
# ═══════════════════════════════════════════════════════════════════

class StripeWebhookEvent(BaseModel):
    """
    Every Stripe webhook delivery is logged here.

    * ``stripe_event_id`` is unique — prevents double-processing.
    * ``processed`` flips to True once the handler succeeds.
    """

    stripe_event_id = models.CharField(max_length=255, unique=True, db_index=True)
    event_type = models.CharField(max_length=255, db_index=True)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "stripe webhook event"
        verbose_name_plural = "stripe webhook events"

    def __str__(self):
        status = "✓" if self.processed else "✗"
        return f"[{status}] {self.event_type} – {self.stripe_event_id}"
