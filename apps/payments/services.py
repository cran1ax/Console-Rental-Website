import logging

import stripe
from django.conf import settings

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service class for Stripe API interactions."""

    @staticmethod
    def create_customer(user):
        """Create a Stripe customer for a user."""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.get_full_name(),
                metadata={"user_id": str(user.id)},
            )
            user.profile.stripe_customer_id = customer.id
            user.profile.save(update_fields=["stripe_customer_id"])
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation failed: {e}")
            raise

    @staticmethod
    def get_or_create_customer(user):
        """Get existing Stripe customer or create a new one."""
        if user.profile.stripe_customer_id:
            try:
                return stripe.Customer.retrieve(user.profile.stripe_customer_id)
            except stripe.error.InvalidRequestError:
                pass
        return StripeService.create_customer(user)

    @staticmethod
    def create_payment_intent(amount, currency, customer_id, metadata=None):
        """Create a Stripe PaymentIntent."""
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to smallest currency unit
                currency=currency.lower(),
                customer=customer_id,
                metadata=metadata or {},
                automatic_payment_methods={"enabled": True},
            )
            return intent
        except stripe.error.StripeError as e:
            logger.error(f"Stripe PaymentIntent creation failed: {e}")
            raise

    @staticmethod
    def create_refund(payment_intent_id, amount=None):
        """Create a refund for a payment."""
        try:
            params = {"payment_intent": payment_intent_id}
            if amount:
                params["amount"] = int(amount * 100)
            refund = stripe.Refund.create(**params)
            return refund
        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund creation failed: {e}")
            raise

    @staticmethod
    def construct_webhook_event(payload, sig_header):
        """Construct and verify a Stripe webhook event."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.error(f"Stripe webhook verification failed: {e}")
            raise
