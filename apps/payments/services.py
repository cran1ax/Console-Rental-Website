"""
Stripe Service Layer
====================
Encapsulates **all** Stripe API interaction for the project.

Primary flow: Stripe *Checkout Sessions*
─────────────────────────────────────────
1.  ``create_checkout_session``  →  returns a hosted-page URL
2.  Stripe redirects the user to your success/cancel URLs
3.  ``checkout.session.completed`` webhook fires
4.  ``handle_checkout_completed`` updates Payment + Rental rows

Secondary helpers:
    • ``process_refund``   →  full / partial refund via PaymentIntent
    • ``expire_session``   →  manually expire an open session
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import stripe
from django.conf import settings
from django.db import transaction

from .models import Payment, PaymentStatus, PaymentType, StripeWebhookEvent

logger = logging.getLogger(__name__)

# ── Initialise the module-level Stripe API key ───────────────────
stripe.api_key = settings.STRIPE_SECRET_KEY


# ═══════════════════════════════════════════════════════════════════
# CUSTOMER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

class StripeCustomerMixin:
    """Helpers for Stripe Customer lifecycle."""

    @staticmethod
    def create_customer(user) -> stripe.Customer:
        """Create a Stripe customer and persist the ID on the profile."""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.get_full_name(),
                metadata={"user_id": str(user.id)},
            )
            user.profile.stripe_customer_id = customer.id
            user.profile.save(update_fields=["stripe_customer_id"])
            logger.info("Stripe customer %s created for user %s", customer.id, user.id)
            return customer
        except stripe.error.StripeError as e:
            logger.error("Stripe customer creation failed for user %s: %s", user.id, e)
            raise

    @staticmethod
    def get_or_create_customer(user) -> stripe.Customer:
        """Return existing Stripe customer or create a new one."""
        if user.profile.stripe_customer_id:
            try:
                return stripe.Customer.retrieve(user.profile.stripe_customer_id)
            except stripe.error.InvalidRequestError:
                logger.warning(
                    "Stale stripe_customer_id %s for user %s — re-creating.",
                    user.profile.stripe_customer_id,
                    user.id,
                )
        return StripeCustomerMixin.create_customer(user)


# ═══════════════════════════════════════════════════════════════════
# MAIN SERVICE
# ═══════════════════════════════════════════════════════════════════

class StripeService(StripeCustomerMixin):
    """
    All Stripe operations funnelled through one service.

    Each public method is a *thin* wrapper around the Stripe API with
    logging, error handling, and local-DB bookkeeping.
    """

    # ──────────────────────────────────────────────────────────────
    # 1. Checkout Session
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def create_checkout_session(
        *,
        user,
        rental,
        payment_type: str = "rental",
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a Stripe Checkout Session and a local ``Payment`` record.

        Returns
        -------
        dict with keys:
            checkout_url  – redirect the frontend here
            session_id    – cs_xxx
            payment_id    – local Payment UUID
        """
        # ── Resolve amount / type ────────────────────────────────
        if payment_type == "deposit":
            amount = rental.deposit_amount
            p_type = PaymentType.DEPOSIT
            description = f"Security deposit for Rental #{rental.rental_number}"
        elif payment_type == "late_fee":
            amount = rental.late_fee
            p_type = PaymentType.LATE_FEE
            description = f"Late fee for Rental #{rental.rental_number}"
        else:
            amount = rental.total_price
            p_type = PaymentType.RENTAL
            description = f"Rental payment for #{rental.rental_number}"

        if amount <= 0:
            raise ValueError(f"Payment amount must be positive, got ₹{amount}")

        # ── Stripe customer ──────────────────────────────────────
        customer = StripeService.get_or_create_customer(user)

        # ── Build URLs ───────────────────────────────────────────
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        if not success_url:
            success_url = (
                f"{frontend_url}/payments/success"
                "?session_id={CHECKOUT_SESSION_ID}"
            )
        if not cancel_url:
            cancel_url = f"{frontend_url}/payments/cancel"

        # ── Create Checkout Session ──────────────────────────────
        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                customer=customer.id,
                line_items=[
                    {
                        "price_data": {
                            "currency": "inr",
                            "unit_amount": int(amount * 100),  # paise
                            "product_data": {
                                "name": description,
                                "metadata": {
                                    "rental_number": rental.rental_number,
                                },
                            },
                        },
                        "quantity": 1,
                    },
                ],
                metadata={
                    "rental_id": str(rental.id),
                    "rental_number": rental.rental_number,
                    "payment_type": payment_type,
                    "user_id": str(user.id),
                },
                success_url=success_url,
                cancel_url=cancel_url,
                expires_after=1800,  # 30 min
            )
        except stripe.error.StripeError as e:
            logger.error("Checkout session creation failed: %s", e)
            raise

        # ── Local Payment record ─────────────────────────────────
        payment = Payment.objects.create(
            user=user,
            rental=rental,
            payment_type=p_type,
            amount=amount,
            status=PaymentStatus.PROCESSING,
            stripe_checkout_session_id=session.id,
            stripe_customer_id=customer.id,
            metadata={
                "rental_number": rental.rental_number,
                "stripe_session_url": session.url,
            },
        )

        logger.info(
            "Checkout session %s created → Payment %s (₹%s)",
            session.id,
            payment.id,
            amount,
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "payment_id": str(payment.id),
        }

    # ──────────────────────────────────────────────────────────────
    # 2. Webhook: checkout.session.completed
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def handle_checkout_completed(session: dict) -> None:
        """
        Called from the webhook when ``checkout.session.completed`` fires.

        • Updates the Payment row with transaction_id + charge_id.
        • Flips Payment.status → COMPLETED.
        • Updates the Rental's payment_status and status accordingly.
        """
        session_id = session.get("id", "")
        payment_intent_id = session.get("payment_intent", "") or ""

        try:
            payment = Payment.objects.select_for_update().get(
                stripe_checkout_session_id=session_id
            )
        except Payment.DoesNotExist:
            logger.warning("No Payment found for checkout session %s", session_id)
            return

        # ── Populate Stripe IDs ──────────────────────────────────
        payment.transaction_id = payment_intent_id
        payment.status = PaymentStatus.COMPLETED

        # Try to grab the charge ID from the PaymentIntent
        if payment_intent_id:
            try:
                pi = stripe.PaymentIntent.retrieve(payment_intent_id)
                payment.stripe_charge_id = pi.latest_charge or ""
            except stripe.error.StripeError:
                pass  # non-critical — charge_id is informational

        payment.save(update_fields=[
            "transaction_id",
            "stripe_charge_id",
            "status",
            "updated_at",
        ])

        # ── Update Rental ────────────────────────────────────────
        rental = payment.rental

        from apps.rentals.models import PaymentStatus as RentalPaymentStatus
        from apps.rentals.models import RentalStatus

        if payment.payment_type in (PaymentType.RENTAL, PaymentType.DEPOSIT):
            rental.payment_status = RentalPaymentStatus.PAID
            if rental.status == RentalStatus.PENDING:
                rental.status = RentalStatus.CONFIRMED
            rental.save(update_fields=["payment_status", "status", "updated_at"])

        elif payment.payment_type == PaymentType.LATE_FEE:
            # Late fee paid — no status change, just mark paid
            rental.save(update_fields=["updated_at"])

        logger.info(
            "Payment %s completed (pi=%s) → Rental %s confirmed.",
            payment.id,
            payment_intent_id,
            rental.rental_number,
        )

    # ──────────────────────────────────────────────────────────────
    # 3. Webhook: checkout.session.expired
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def handle_checkout_expired(session: dict) -> None:
        """Mark payment as expired when the session times out."""
        session_id = session.get("id", "")
        try:
            payment = Payment.objects.get(stripe_checkout_session_id=session_id)
            payment.status = PaymentStatus.EXPIRED
            payment.failure_reason = "Checkout session expired."
            payment.save(update_fields=["status", "failure_reason", "updated_at"])
            logger.info("Payment %s marked expired (session %s).", payment.id, session_id)
        except Payment.DoesNotExist:
            logger.warning("No Payment for expired session %s", session_id)

    # ──────────────────────────────────────────────────────────────
    # 4. Webhook: payment_intent.payment_failed
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def handle_payment_failed(payment_intent: dict) -> None:
        """Record a payment failure with the reason from Stripe."""
        pi_id = payment_intent.get("id", "")
        error_msg = "Unknown error"
        last_error = payment_intent.get("last_payment_error")
        if last_error:
            error_msg = last_error.get("message", error_msg)

        updated = Payment.objects.filter(
            transaction_id=pi_id
        ).update(
            status=PaymentStatus.FAILED,
            failure_reason=error_msg,
        )
        if not updated:
            logger.warning("No Payment found for failed pi %s", pi_id)
        else:
            logger.info("Payment for pi %s marked FAILED: %s", pi_id, error_msg)

    # ──────────────────────────────────────────────────────────────
    # 5. Refunds
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def process_refund(
        payment: Payment,
        amount: Decimal | None = None,
        reason: str = "requested_by_customer",
    ) -> stripe.Refund:
        """
        Issue a full or partial refund on a completed payment.

        Parameters
        ----------
        payment : Payment
            Must have a non-empty ``transaction_id`` and status COMPLETED.
        amount : Decimal or None
            If None → full refund.  Otherwise → partial (in ₹).
        reason : str
            One of "requested_by_customer", "duplicate", "fraudulent".
        """
        if not payment.is_refundable:
            raise ValueError("Payment is not eligible for refund.")

        try:
            params: dict[str, Any] = {
                "payment_intent": payment.transaction_id,
                "reason": reason,
            }
            if amount is not None:
                params["amount"] = int(amount * 100)

            refund = stripe.Refund.create(**params)
        except stripe.error.StripeError as e:
            logger.error("Refund failed for Payment %s: %s", payment.id, e)
            raise

        payment.status = (
            PaymentStatus.REFUNDED
            if amount is None
            else PaymentStatus.PARTIALLY_REFUNDED
        )
        payment.save(update_fields=["status", "updated_at"])

        # ── Update rental payment_status ─────────────────────────
        from apps.rentals.models import PaymentStatus as RentalPaymentStatus

        rental = payment.rental
        rental.payment_status = RentalPaymentStatus.REFUNDED
        rental.save(update_fields=["payment_status", "updated_at"])

        logger.info(
            "Refund %s issued on Payment %s (₹%s).",
            refund.id,
            payment.id,
            amount or payment.amount,
        )
        return refund

    # ──────────────────────────────────────────────────────────────
    # 6. Webhook signature verification
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
        """
        Verify the signature and return a ``stripe.Event``.

        Raises ``ValueError`` or ``stripe.error.SignatureVerificationError``
        if verification fails — the caller should return HTTP 400.
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.error("Webhook signature verification failed: %s", e)
            raise

    # ──────────────────────────────────────────────────────────────
    # 7. Expire a Checkout Session manually
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def expire_checkout_session(session_id: str) -> None:
        """Force-expire an open Checkout Session (e.g. user cancelled)."""
        try:
            stripe.checkout.Session.expire(session_id)
            logger.info("Checkout session %s manually expired.", session_id)
        except stripe.error.StripeError as e:
            logger.error("Failed to expire session %s: %s", session_id, e)
            raise
