from decimal import Decimal

from rest_framework import serializers

from .models import Payment


# ═══════════════════════════════════════════════════════════════════
# CHECKOUT SESSION (input)
# ═══════════════════════════════════════════════════════════════════

class CheckoutSessionSerializer(serializers.Serializer):
    """Validates input for creating a Stripe Checkout Session."""

    rental_id = serializers.UUIDField(
        help_text="UUID of the rental to pay for.",
    )
    payment_type = serializers.ChoiceField(
        choices=[
            ("rental", "Rental Payment"),
            ("deposit", "Security Deposit"),
            ("late_fee", "Late Fee"),
        ],
        help_text="Type of payment being made.",
    )
    success_url = serializers.URLField(
        required=False,
        help_text="Override the default success redirect URL.",
    )
    cancel_url = serializers.URLField(
        required=False,
        help_text="Override the default cancel redirect URL.",
    )


# ═══════════════════════════════════════════════════════════════════
# PAYMENT (output — list & detail)
# ═══════════════════════════════════════════════════════════════════

class PaymentListSerializer(serializers.ModelSerializer):
    """Compact representation for the payment list view."""

    payment_type_display = serializers.CharField(
        source="get_payment_type_display", read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True,
    )
    rental_number = serializers.CharField(
        source="rental.rental_number", read_only=True,
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "rental",
            "rental_number",
            "payment_type",
            "payment_type_display",
            "status",
            "status_display",
            "amount",
            "currency",
            "created_at",
        ]


class PaymentDetailSerializer(serializers.ModelSerializer):
    """
    Full payment detail including Stripe identifiers.

    ``stripe_checkout_session_id`` and ``transaction_id`` are exposed
    so the frontend / admin can look them up in the Stripe Dashboard.
    """

    payment_type_display = serializers.CharField(
        source="get_payment_type_display", read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True,
    )
    rental_number = serializers.CharField(
        source="rental.rental_number", read_only=True,
    )
    is_refundable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "rental",
            "rental_number",
            "payment_type",
            "payment_type_display",
            "status",
            "status_display",
            "amount",
            "currency",
            "stripe_checkout_session_id",
            "transaction_id",
            "stripe_charge_id",
            "failure_reason",
            "is_refundable",
            "created_at",
            "updated_at",
        ]


# ═══════════════════════════════════════════════════════════════════
# REFUND (input)
# ═══════════════════════════════════════════════════════════════════

class RefundSerializer(serializers.Serializer):
    """Validates input for issuing a refund."""

    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        help_text="Partial refund amount in ₹. Omit for full refund.",
    )
    reason = serializers.ChoiceField(
        choices=[
            ("requested_by_customer", "Requested by customer"),
            ("duplicate", "Duplicate"),
            ("fraudulent", "Fraudulent"),
        ],
        default="requested_by_customer",
        required=False,
    )

    def validate_amount(self, value):
        if value is not None and value <= Decimal("0"):
            raise serializers.ValidationError("Refund amount must be positive.")
        return value
