"""
Celery tasks for the Rentals app.

Periodic tasks
--------------
1. ``send_rental_end_reminders``
   → Sends an email to users whose rental ends **tomorrow** (status = ACTIVE).
2. ``auto_mark_late_rentals``
   → Marks all ACTIVE rentals past their end date as LATE (runs at midnight).
3. ``auto_refund_deposits``
   → Automatically refunds the security deposit for rentals returned on time
     (no late fee, deposit payment completed).
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 1. SEND RENTAL-END REMINDERS
# ═══════════════════════════════════════════════════════════════════

@shared_task(
    name="apps.rentals.tasks.send_rental_end_reminders",
    bind=True,
    max_retries=3,
    default_retry_delay=60 * 5,  # 5 minutes
    autoretry_for=(Exception,),
    acks_late=True,
)
def send_rental_end_reminders(self):
    """
    Email every user whose *active* rental ends tomorrow.

    Runs daily at 09:00 via Celery Beat.
    """
    from apps.rentals.models import Rental, RentalStatus

    tomorrow = timezone.now().date() + timedelta(days=1)

    rentals = (
        Rental.objects
        .filter(
            status=RentalStatus.ACTIVE,
            rental_end_date=tomorrow,
        )
        .select_related("user", "console")
    )

    sent_count = 0
    failed_count = 0

    for rental in rentals:
        try:
            _send_reminder_email(rental)
            sent_count += 1
            logger.info(
                "Reminder sent for Rental #%s to %s",
                rental.rental_number,
                rental.user.email,
            )
        except Exception as exc:
            failed_count += 1
            logger.error(
                "Failed to send reminder for Rental #%s: %s",
                rental.rental_number,
                exc,
            )

    logger.info(
        "Rental reminders: %d sent, %d failed out of %d total.",
        sent_count,
        failed_count,
        rentals.count(),
    )
    return {
        "sent": sent_count,
        "failed": failed_count,
        "total": sent_count + failed_count,
    }


def _send_reminder_email(rental):
    """Build and dispatch the rental-ending-soon email."""
    subject = f"⏰ Reminder: Your rental #{rental.rental_number} ends tomorrow!"

    # Try HTML template first; fall back to plain text.
    context = {
        "user": rental.user,
        "rental": rental,
        "console_name": rental.console.name if rental.console else "N/A",
        "end_date": rental.rental_end_date,
        "rental_number": rental.rental_number,
        "site_url": getattr(settings, "SITE_URL", "http://localhost:8000"),
        "frontend_url": getattr(settings, "FRONTEND_URL", "http://localhost:3000"),
    }

    try:
        html_message = render_to_string(
            "emails/rental_end_reminder.html", context
        )
        plain_message = strip_tags(html_message)
    except Exception:
        # Template not found — use inline plain text.
        plain_message = (
            f"Hi {rental.user.full_name or rental.user.email},\n\n"
            f"This is a friendly reminder that your rental "
            f"#{rental.rental_number} "
            f"({'for ' + rental.console.name if rental.console else ''}) "
            f"is ending on {rental.rental_end_date:%B %d, %Y}.\n\n"
            f"Please make sure to return the rented items on time to avoid "
            f"late fees.\n\n"
            f"If you've already arranged the return, you can ignore this "
            f"email.\n\n"
            f"Thanks,\nThe Corner Console Team"
        )
        html_message = None

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[rental.user.email],
        html_message=html_message,
        fail_silently=False,
    )


# ═══════════════════════════════════════════════════════════════════
# 2. AUTO-MARK LATE RENTALS
# ═══════════════════════════════════════════════════════════════════

@shared_task(
    name="apps.rentals.tasks.auto_mark_late_rentals",
    bind=True,
    max_retries=3,
    default_retry_delay=60 * 5,
    autoretry_for=(Exception,),
    acks_late=True,
)
def auto_mark_late_rentals(self):
    """
    Find every ACTIVE rental whose end date has passed and mark it LATE.

    Runs daily at 00:05 via Celery Beat.  Uses the existing
    ``rental_service.mark_rental_late()`` so all business logic
    (status transition, late-fee snapshot) stays in one place.
    """
    from apps.rentals.models import Rental, RentalStatus
    from apps.rentals.rental_service import RentalService

    today = timezone.now().date()

    overdue_rentals = (
        Rental.objects
        .filter(
            status=RentalStatus.ACTIVE,
            rental_end_date__lt=today,
        )
        .select_related("user", "console")
    )

    marked = 0
    errors = 0

    for rental in overdue_rentals:
        try:
            with transaction.atomic():
                RentalService.mark_rental_late(rental)
            marked += 1
            logger.info(
                "Rental #%s marked LATE (%d day(s) overdue).",
                rental.rental_number,
                rental.overdue_days,
            )
        except Exception as exc:
            errors += 1
            logger.error(
                "Could not mark Rental #%s as late: %s",
                rental.rental_number,
                exc,
            )

    logger.info(
        "Auto-mark-late: %d marked, %d errors out of %d overdue.",
        marked,
        errors,
        overdue_rentals.count(),
    )
    return {"marked": marked, "errors": errors}


# ═══════════════════════════════════════════════════════════════════
# 3. AUTO-REFUND DEPOSITS
# ═══════════════════════════════════════════════════════════════════

@shared_task(
    name="apps.rentals.tasks.auto_refund_deposits",
    bind=True,
    max_retries=3,
    default_retry_delay=60 * 10,  # 10 minutes (Stripe calls)
    autoretry_for=(Exception,),
    acks_late=True,
)
def auto_refund_deposits(self):
    """
    Refund the security deposit for rentals that were returned on time
    (i.e. ``late_fee == 0`` and a completed deposit payment exists).

    Criteria:
    * status  = RETURNED
    * late_fee = 0  (no late charges)
    * A related Payment with type=DEPOSIT and status=COMPLETED exists
    * The deposit payment hasn't already been refunded

    Runs daily at 10:00 via Celery Beat.
    """
    from apps.payments.models import Payment, PaymentStatus, PaymentType
    from apps.payments.services import StripeService
    from apps.rentals.models import Rental, RentalStatus

    returned_rentals = (
        Rental.objects
        .filter(
            status=RentalStatus.RETURNED,
            late_fee=0,
        )
        .prefetch_related("payments")
    )

    refunded = 0
    skipped = 0
    errors = 0

    for rental in returned_rentals:
        deposit_payment = (
            rental.payments
            .filter(
                payment_type=PaymentType.DEPOSIT,
                status=PaymentStatus.COMPLETED,
            )
            .first()
        )

        if not deposit_payment:
            skipped += 1
            continue

        if not deposit_payment.is_refundable:
            skipped += 1
            continue

        try:
            with transaction.atomic():
                StripeService.process_refund(
                    payment=deposit_payment,
                    reason="requested_by_customer",
                )
            refunded += 1
            logger.info(
                "Deposit ₹%s refunded for Rental #%s.",
                deposit_payment.amount,
                rental.rental_number,
            )
        except Exception as exc:
            errors += 1
            logger.error(
                "Deposit refund failed for Rental #%s: %s",
                rental.rental_number,
                exc,
            )

    logger.info(
        "Auto-refund deposits: %d refunded, %d skipped, %d errors.",
        refunded,
        skipped,
        errors,
    )
    return {"refunded": refunded, "skipped": skipped, "errors": errors}


# ═══════════════════════════════════════════════════════════════════
# ONE-OFF HELPER TASKS (can be dispatched manually)
# ═══════════════════════════════════════════════════════════════════

@shared_task(
    name="apps.rentals.tasks.send_single_rental_reminder",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def send_single_rental_reminder(rental_id: int):
    """
    Send a reminder for a specific rental.
    Useful for ad-hoc / admin-triggered reminders.

    Usage::

        from apps.rentals.tasks import send_single_rental_reminder
        send_single_rental_reminder.delay(rental_id=42)
    """
    from apps.rentals.models import Rental

    rental = Rental.objects.select_related("user", "console").get(pk=rental_id)
    _send_reminder_email(rental)
    logger.info("Ad-hoc reminder sent for Rental #%s.", rental.rental_number)
    return {"rental_number": rental.rental_number, "sent": True}
