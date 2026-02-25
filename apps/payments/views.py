import logging

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rentals.models import Rental

from .models import Payment, PaymentStatus, PaymentType, StripeWebhookEvent
from .serializers import CreatePaymentIntentSerializer, PaymentSerializer
from .services import StripeService

logger = logging.getLogger(__name__)


class CreatePaymentIntentView(APIView):
    """Create a Stripe PaymentIntent for a rental."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreatePaymentIntentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            rental = Rental.objects.get(
                id=serializer.validated_data["rental_id"],
                user=request.user,
            )
        except Rental.DoesNotExist:
            return Response(
                {"detail": "Rental not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Determine amount
        payment_type = serializer.validated_data["payment_type"]
        if payment_type == "deposit":
            amount = rental.security_deposit
            p_type = PaymentType.DEPOSIT
        else:
            amount = rental.total_amount
            p_type = PaymentType.RENTAL

        # Get or create Stripe customer
        customer = StripeService.get_or_create_customer(request.user)

        # Create PaymentIntent
        intent = StripeService.create_payment_intent(
            amount=amount,
            currency="inr",
            customer_id=customer.id,
            metadata={
                "rental_id": str(rental.id),
                "rental_number": rental.rental_number,
                "payment_type": payment_type,
                "user_id": str(request.user.id),
            },
        )

        # Create Payment record
        payment = Payment.objects.create(
            user=request.user,
            rental=rental,
            payment_type=p_type,
            amount=amount,
            stripe_payment_intent_id=intent.id,
            stripe_client_secret=intent.client_secret,
            status=PaymentStatus.PROCESSING,
        )

        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED,
        )


class PaymentListView(generics.ListAPIView):
    """List payments for the authenticated user."""

    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)


class StripeWebhookView(APIView):
    """Handle Stripe webhook events."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        try:
            event = StripeService.construct_webhook_event(payload, sig_header)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Idempotency check
        if StripeWebhookEvent.objects.filter(stripe_event_id=event.id).exists():
            return Response(status=status.HTTP_200_OK)

        # Log the event
        webhook_event = StripeWebhookEvent.objects.create(
            stripe_event_id=event.id,
            event_type=event.type,
            payload=event.data,
        )

        try:
            self._handle_event(event)
            webhook_event.processed = True
            webhook_event.save(update_fields=["processed"])
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            webhook_event.error_message = str(e)
            webhook_event.save(update_fields=["error_message"])

        return Response(status=status.HTTP_200_OK)

    def _handle_event(self, event):
        """Route webhook events to handlers."""
        handlers = {
            "payment_intent.succeeded": self._handle_payment_succeeded,
            "payment_intent.payment_failed": self._handle_payment_failed,
        }
        handler = handlers.get(event.type)
        if handler:
            handler(event.data.object)

    def _handle_payment_succeeded(self, payment_intent):
        """Handle successful payment."""
        try:
            payment = Payment.objects.get(
                stripe_payment_intent_id=payment_intent.id
            )
            payment.status = PaymentStatus.COMPLETED
            payment.stripe_charge_id = (
                payment_intent.latest_charge or ""
            )
            payment.save(update_fields=["status", "stripe_charge_id"])

            # Update rental status if rental payment
            if payment.payment_type == PaymentType.RENTAL:
                from apps.rentals.models import RentalStatus

                payment.rental.status = RentalStatus.CONFIRMED
                payment.rental.save(update_fields=["status"])

        except Payment.DoesNotExist:
            logger.warning(
                f"Payment not found for intent: {payment_intent.id}"
            )

    def _handle_payment_failed(self, payment_intent):
        """Handle failed payment."""
        try:
            payment = Payment.objects.get(
                stripe_payment_intent_id=payment_intent.id
            )
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = (
                payment_intent.last_payment_error.message
                if payment_intent.last_payment_error
                else "Unknown error"
            )
            payment.save(update_fields=["status", "failure_reason"])
        except Payment.DoesNotExist:
            logger.warning(
                f"Payment not found for intent: {payment_intent.id}"
            )
