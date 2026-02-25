from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    payment_type_display = serializers.CharField(
        source="get_payment_type_display", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "rental",
            "payment_type",
            "payment_type_display",
            "status",
            "status_display",
            "amount",
            "currency",
            "stripe_client_secret",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "stripe_client_secret",
            "created_at",
        ]


class CreatePaymentIntentSerializer(serializers.Serializer):
    rental_id = serializers.UUIDField()
    payment_type = serializers.ChoiceField(
        choices=[("rental", "Rental"), ("deposit", "Deposit")]
    )
