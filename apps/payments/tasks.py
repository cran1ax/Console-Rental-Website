"""
Celery tasks for the Payments app.

Periodic tasks
--------------
1. ``expire_stale_checkout_sessions``
   → Marks PENDING payments older than 30 minutes as EXPIRED.
     Stripe Checkout Sessions expire after 24 h by default, but we
     expire our local records sooner to keep the data clean.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 1. EXPIRE STALE CHECKOUT SESSIONS
# ═══════════════════════════════════════════════════════════════════

@shared_task(
    name="apps.payments.tasks.expire_stale_checkout_sessions",
    bind=True,
    max_retries=3,
    default_retry_delay=60 * 5,
    autoretry_for=(Exception,),
    acks_late=True,
)
def expire_stale_checkout_sessions(self):
    """
    Find PENDING payments created more than 30 minutes ago
    and mark them as EXPIRED.

    This keeps the database tidy and prevents users from paying
    for long-abandoned checkout sessions.

    Runs every 30 minutes via Celery Beat.
    """
    from apps.payments.models import Payment, PaymentStatus

    cutoff = timezone.now() - timedelta(minutes=30)

    stale_payments = Payment.objects.filter(
        status=PaymentStatus.PENDING,
        created_at__lt=cutoff,
    )

    count = stale_payments.count()

    if count == 0:
        logger.info("No stale checkout sessions to expire.")
        return {"expired": 0}

    with transaction.atomic():
        expired = stale_payments.update(status=PaymentStatus.EXPIRED)

    logger.info("Expired %d stale checkout session(s).", expired)
    return {"expired": expired}


# ═══════════════════════════════════════════════════════════════════
# 2. SEND PAYMENT CONFIRMATION EMAIL  (on-demand, not periodic)
# ═══════════════════════════════════════════════════════════════════

@shared_task(
    name="apps.payments.tasks.send_payment_confirmation",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def send_payment_confirmation(payment_id: int):
    """
    Send a payment confirmation email after a successful checkout.

    Can be triggered from the Stripe webhook handler::

        from apps.payments.tasks import send_payment_confirmation
        send_payment_confirmation.delay(payment_id=payment.id)
    """
    from django.conf import settings
    from django.core.mail import send_mail

    from apps.payments.models import Payment

    payment = (
        Payment.objects
        .select_related("user", "rental", "rental__console")
        .get(pk=payment_id)
    )

    rental = payment.rental
    console_name = rental.console.name if rental.console else "N/A"

    subject = f"✅ Payment confirmed – Rental #{rental.rental_number}"
    message = (
        f"Hi {payment.user.full_name or payment.user.email},\n\n"
        f"Your payment of ₹{payment.amount} for rental "
        f"#{rental.rental_number} ({console_name}) has been confirmed.\n\n"
        f"Payment type: {payment.get_payment_type_display()}\n"
        f"Transaction ID: {payment.transaction_id or 'N/A'}\n\n"
        f"Rental dates: {rental.rental_start_date:%B %d, %Y} – "
        f"{rental.rental_end_date:%B %d, %Y}\n\n"
        f"Thanks for choosing Corner Console!\n"
        f"The Corner Console Team"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[payment.user.email],
        fail_silently=False,
    )

    logger.info(
        "Payment confirmation email sent for Payment #%d (Rental #%s).",
        payment.id,
        rental.rental_number,
    )
    return {"payment_id": payment.id, "sent": True}
