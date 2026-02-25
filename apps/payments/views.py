"""
Payment Views
=============

Thin HTTP controllers — all Stripe logic lives in ``services.py``.

Endpoints
---------
POST  /api/v1/payments/checkout-session/   → Create Checkout Session
POST  /api/v1/payments/webhook/stripe/     → Stripe Webhook receiver
GET   /api/v1/payments/                    → List user's payments
GET   /api/v1/payments/<id>/               → Payment detail
POST  /api/v1/payments/<id>/refund/        → Issue refund (admin)
"""

import logging

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsOwner
from apps.rentals.models import Rental

from .models import Payment, PaymentStatus, StripeWebhookEvent
from .serializers import (
    CheckoutSessionSerializer,
    PaymentDetailSerializer,
    PaymentListSerializer,
    RefundSerializer,
)
from .services import StripeService

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 1. CREATE CHECKOUT SESSION
# ═══════════════════════════════════════════════════════════════════

class CreateCheckoutSessionView(APIView):
    """
    POST /api/v1/payments/checkout-session/

    Creates a Stripe Checkout Session and returns the hosted-page URL.
    The frontend should redirect the user to ``checkout_url``.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CheckoutSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # ── Fetch the rental (must belong to requesting user) ────
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

        # ── Delegate to service ──────────────────────────────────
        try:
            result = StripeService.create_checkout_session(
                user=request.user,
                rental=rental,
                payment_type=serializer.validated_data["payment_type"],
                success_url=serializer.validated_data.get("success_url"),
                cancel_url=serializer.validated_data.get("cancel_url"),
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error("Checkout session creation failed: %s", e)
            return Response(
                {"detail": "Unable to create payment session. Try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(result, status=status.HTTP_201_CREATED)


# ═══════════════════════════════════════════════════════════════════
# 2. STRIPE WEBHOOK
# ═══════════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    """
    POST /api/v1/payments/webhook/stripe/

    • CSRF-exempt (Stripe sends raw POST from their servers).
    • No authentication — only the webhook signature is checked.
    • Idempotent — duplicate event IDs are safely ignored.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        if not sig_header:
            return Response(
                {"detail": "Missing Stripe-Signature header."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Verify signature ─────────────────────────────────────
        try:
            event = StripeService.construct_webhook_event(payload, sig_header)
        except Exception:
            return Response(
                {"detail": "Invalid signature."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Idempotency check ────────────────────────────────────
        if StripeWebhookEvent.objects.filter(stripe_event_id=event.id).exists():
            return Response({"detail": "Event already processed."}, status=status.HTTP_200_OK)

        # ── Log the event ────────────────────────────────────────
        webhook_event = StripeWebhookEvent.objects.create(
            stripe_event_id=event.id,
            event_type=event.type,
            payload=event.data,
        )

        # ── Route to handler ─────────────────────────────────────
        try:
            self._route_event(event)
            webhook_event.processed = True
            webhook_event.save(update_fields=["processed", "updated_at"])
        except Exception as e:
            logger.error("Webhook handler failed for %s: %s", event.type, e)
            webhook_event.error_message = str(e)
            webhook_event.save(update_fields=["error_message", "updated_at"])

        # Always return 200 — Stripe will retry on 4xx/5xx
        return Response(status=status.HTTP_200_OK)

    # ── Event router ─────────────────────────────────────────────

    EVENT_HANDLERS = {
        "checkout.session.completed": "_on_checkout_completed",
        "checkout.session.expired": "_on_checkout_expired",
        "payment_intent.payment_failed": "_on_payment_failed",
    }

    def _route_event(self, event):
        handler_name = self.EVENT_HANDLERS.get(event.type)
        if handler_name:
            handler = getattr(self, handler_name)
            handler(event.data.object)
        else:
            logger.info("Unhandled Stripe event type: %s", event.type)

    # ── Individual handlers (delegate to service) ────────────────

    @staticmethod
    def _on_checkout_completed(session):
        StripeService.handle_checkout_completed(session)

    @staticmethod
    def _on_checkout_expired(session):
        StripeService.handle_checkout_expired(session)

    @staticmethod
    def _on_payment_failed(payment_intent):
        StripeService.handle_payment_failed(payment_intent)


# ═══════════════════════════════════════════════════════════════════
# 3. PAYMENT LIST / DETAIL
# ═══════════════════════════════════════════════════════════════════

class PaymentListView(generics.ListAPIView):
    """GET /api/v1/payments/ — list payments for the authenticated user."""

    serializer_class = PaymentListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Payment.objects
            .filter(user=self.request.user)
            .select_related("rental")
        )


class PaymentDetailView(generics.RetrieveAPIView):
    """GET /api/v1/payments/<id>/ — single payment detail."""

    serializer_class = PaymentDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    lookup_field = "id"

    def get_queryset(self):
        return (
            Payment.objects
            .filter(user=self.request.user)
            .select_related("rental")
        )


# ═══════════════════════════════════════════════════════════════════
# 4. REFUND  (admin or owner)
# ═══════════════════════════════════════════════════════════════════

class RefundView(APIView):
    """
    POST /api/v1/payments/<id>/refund/

    Body (optional): { "amount": "500.00", "reason": "requested_by_customer" }
    Omit ``amount`` for a full refund.
    """

    permission_classes = [permissions.IsAdminUser]

    def post(self, request, id):
        try:
            payment = Payment.objects.select_related("rental").get(id=id)
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refund = StripeService.process_refund(
                payment=payment,
                amount=serializer.validated_data.get("amount"),
                reason=serializer.validated_data.get("reason", "requested_by_customer"),
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error("Refund failed for Payment %s: %s", id, e)
            return Response(
                {"detail": "Refund could not be processed."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "detail": "Refund processed.",
                "refund_id": refund.id,
                "status": payment.status,
            },
            status=status.HTTP_200_OK,
        )
