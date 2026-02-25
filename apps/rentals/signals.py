"""
Rental Signals
==============
Thin signal handlers that delegate to the service layer.
Heavy logic (price calc, stock, late fees) lives in ``rental_service.py``.
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Rental, RentalStatus

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Rental)
def track_status_change(sender, instance, **kwargs):
    """
    Stash the *previous* status on the instance so ``post_save`` can
    detect a real transition (avoids duplicate stock restores).
    """
    if instance.pk:
        try:
            instance._prev_status = (
                Rental.objects.filter(pk=instance.pk)
                .values_list("status", flat=True)
                .first()
            )
        except Rental.DoesNotExist:
            instance._prev_status = None
    else:
        instance._prev_status = None


@receiver(post_save, sender=Rental)
def handle_status_transition(sender, instance, created, **kwargs):
    """
    React to status transitions that the service layer did *not* handle
    inline (e.g. admin panel changes).

    If the service already restored stock (return_rental / cancel_rental),
    the stock is already correct — but admin-driven changes also need
    stock correction.
    """
    from . import rental_service  # late import to avoid circular

    prev = getattr(instance, "_prev_status", None)
    curr = instance.status

    # No actual change → nothing to do
    if prev == curr:
        return

    # ── Returned via admin (service.return_rental handles its own) ──
    if curr == RentalStatus.RETURNED and prev in (
        RentalStatus.ACTIVE,
        RentalStatus.LATE,
        RentalStatus.OVERDUE,
    ):
        # Only compute late fee if it wasn't already set
        if instance.late_fee == 0 and instance.actual_return_date:
            instance.late_fee = rental_service.calculate_late_fee(
                instance, return_date=instance.actual_return_date,
            )
            Rental.objects.filter(pk=instance.pk).update(late_fee=instance.late_fee)
            logger.info(
                "Signal: late fee ₹%s applied to %s",
                instance.late_fee,
                instance.rental_number,
            )

    # ── Cancelled via admin ─────────────────────────────────────────
    # (service.cancel_rental already restores stock, but admin changes
    #  bypass the service, so this acts as a safety net.)
    # NOTE: The service layer is the primary stock manager.  If you need
    # admin-driven stock correction too, uncomment the block below:
    #
    # if curr == RentalStatus.CANCELLED and prev in (
    #     RentalStatus.PENDING, RentalStatus.CONFIRMED,
    # ):
    #     rental_service._restore_stock(instance)

    logger.debug(
        "Rental %s status: %s → %s", instance.rental_number, prev, curr,
    )
