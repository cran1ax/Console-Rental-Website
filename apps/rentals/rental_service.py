"""
Rental Service Layer
====================
All business logic for the rental lifecycle lives here — pricing,
stock management, late fees, status transitions.  Views / serializers
stay thin and only handle HTTP concerns.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import models, transaction
from django.utils import timezone

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()

from .models import (
    Accessory,
    Console,
    DeliveryOption,
    Game,
    PaymentStatus,
    Rental,
    RentalStatus,
    RentalType,
)

logger = logging.getLogger(__name__)

# ── Late-fee config (₹ per day the item is overdue) ─────────────
LATE_FEE_PER_DAY_CONSOLE = Decimal("150.00")
LATE_FEE_PER_DAY_GAME = Decimal("30.00")
LATE_FEE_PER_DAY_ACCESSORY = Decimal("20.00")


# ═══════════════════════════════════════════════════════════════════
# PRICE CALCULATION
# ═══════════════════════════════════════════════════════════════════


def calculate_rental_price(
    *,
    console: Console | None,
    games: list[Game],
    accessories: list[Accessory],
    rental_type: str,
    rental_start_date: date,
    rental_end_date: date,
) -> dict:
    """
    Return a price breakdown dict::

        {
            "console_price": Decimal,
            "games_price": Decimal,
            "accessories_price": Decimal,
            "total_price": Decimal,
            "deposit_amount": Decimal,
            "daily_rate": Decimal,
            "duration_days": int,
        }

    Pricing strategy
    ~~~~~~~~~~~~~~~~
    * **daily** – ``daily_price × duration_days``
    * **weekly** – ``weekly_price × full_weeks`` + ``daily_price × leftover_days``
    * **monthly** – ``monthly_price × full_months`` + ``daily_price × leftover_days``

    Games/accessories use their ``daily_price`` / ``price_per_day`` for all
    rental types because they only carry a daily rate.
    """
    duration_days = (rental_end_date - rental_start_date).days
    if duration_days <= 0:
        raise ValueError("rental_end_date must be after rental_start_date")

    # ── Console ──────────────────────────────────────────────────
    console_price = Decimal("0.00")
    deposit_amount = Decimal("0.00")
    daily_rate = Decimal("0.00")

    if console:
        daily_rate = console.daily_price
        deposit_amount = console.security_deposit
        console_price = _price_for_item(
            daily=console.daily_price,
            weekly=console.weekly_price,
            monthly=console.monthly_price,
            rental_type=rental_type,
            duration_days=duration_days,
        )

    # ── Games ────────────────────────────────────────────────────
    games_price = Decimal("0.00")
    for game in games:
        games_price += _price_for_item(
            daily=game.daily_price,
            weekly=game.weekly_price or game.daily_price * 7,
            monthly=game.daily_price * 30,
            rental_type=rental_type,
            duration_days=duration_days,
        )

    # ── Accessories ──────────────────────────────────────────────
    accessories_price = Decimal("0.00")
    for acc in accessories:
        accessories_price += acc.price_per_day * Decimal(duration_days)

    total_price = console_price + games_price + accessories_price

    return {
        "console_price": console_price,
        "games_price": games_price,
        "accessories_price": accessories_price,
        "total_price": total_price,
        "deposit_amount": deposit_amount,
        "daily_rate": daily_rate,
        "duration_days": duration_days,
    }


def _price_for_item(
    *,
    daily: Decimal,
    weekly: Decimal,
    monthly: Decimal,
    rental_type: str,
    duration_days: int,
) -> Decimal:
    """Compute price for a single item using the right rate bucket."""
    if rental_type == RentalType.WEEKLY:
        full_weeks, leftover = divmod(duration_days, 7)
        return (weekly * full_weeks) + (daily * leftover)

    if rental_type == RentalType.MONTHLY:
        full_months, leftover = divmod(duration_days, 30)
        return (monthly * full_months) + (daily * leftover)

    # default → daily
    return daily * Decimal(duration_days)


# ═══════════════════════════════════════════════════════════════════
# STOCK MANAGEMENT
# ═══════════════════════════════════════════════════════════════════


def _decrement_stock(rental: Rental) -> None:
    """Atomically reduce ``available_quantity`` for every item in the rental."""
    if rental.console_id:
        Console.objects.filter(pk=rental.console_id).update(
            available_quantity=models.F("available_quantity") - 1,
        )

    for game in rental.games.all():
        Game.objects.filter(pk=game.pk).update(
            available_quantity=models.F("available_quantity") - 1,
        )

    for acc in rental.accessories.all():
        Accessory.objects.filter(pk=acc.pk).update(
            available_quantity=models.F("available_quantity") - 1,
        )

    logger.info("Stock decremented for rental %s", rental.rental_number)


def _restore_stock(rental: Rental) -> None:
    """Atomically restore ``available_quantity`` for every item in the rental."""
    if rental.console_id:
        Console.objects.filter(pk=rental.console_id).update(
            available_quantity=models.F("available_quantity") + 1,
        )

    for game in rental.games.all():
        Game.objects.filter(pk=game.pk).update(
            available_quantity=models.F("available_quantity") + 1,
        )

    for acc in rental.accessories.all():
        Accessory.objects.filter(pk=acc.pk).update(
            available_quantity=models.F("available_quantity") + 1,
        )

    logger.info("Stock restored for rental %s", rental.rental_number)


# ═══════════════════════════════════════════════════════════════════
# LATE-FEE CALCULATION
# ═══════════════════════════════════════════════════════════════════


def calculate_late_fee(rental: Rental, *, return_date: date | None = None) -> Decimal:
    """
    Compute the late fee for a rental.

    If ``return_date`` is supplied it is used; otherwise ``timezone.now().date()``
    is assumed.  Only days *past* ``rental_end_date`` count.
    """
    effective_return = return_date or timezone.now().date()

    overdue_days = (effective_return - rental.rental_end_date).days
    if overdue_days <= 0:
        return Decimal("0.00")

    fee = Decimal("0.00")

    if rental.console_id:
        fee += LATE_FEE_PER_DAY_CONSOLE * overdue_days

    fee += LATE_FEE_PER_DAY_GAME * rental.games.count() * overdue_days
    fee += LATE_FEE_PER_DAY_ACCESSORY * rental.accessories.count() * overdue_days

    return fee


# ═══════════════════════════════════════════════════════════════════
# RENTAL LIFECYCLE  (create → return → cancel)
# ═══════════════════════════════════════════════════════════════════


@transaction.atomic
def create_rental(
    *,
    user: "User",
    console: Console | None,
    games: list[Game],
    accessories: list[Accessory],
    rental_type: str,
    rental_start_date: date,
    rental_end_date: date,
    delivery_option: str = DeliveryOption.PICKUP,
    delivery_address: str = "",
    delivery_notes: str = "",
) -> Rental:
    """
    Create a new rental, auto-calculate pricing, decrement stock.

    Raises ``ValueError`` if nothing is being rented or stock is insufficient.
    """
    # ── Guard: must rent something ───────────────────────────────
    if not console and not games and not accessories:
        raise ValueError("At least a console, game, or accessory is required.")

    # ── Guard: stock availability ────────────────────────────────
    if console and console.available_quantity < 1:
        raise ValueError(f'Console "{console.name}" is out of stock.')

    for game in games:
        if game.available_quantity < 1:
            raise ValueError(f'Game "{game.title}" is out of stock.')

    for acc in accessories:
        if acc.available_quantity < 1:
            raise ValueError(f'Accessory "{acc.name}" is out of stock.')

    # ── Price calculation ────────────────────────────────────────
    pricing = calculate_rental_price(
        console=console,
        games=games,
        accessories=accessories,
        rental_type=rental_type,
        rental_start_date=rental_start_date,
        rental_end_date=rental_end_date,
    )

    rental_number = f"CC-{uuid.uuid4().hex[:8].upper()}"

    rental = Rental.objects.create(
        user=user,
        console=console,
        rental_type=rental_type,
        rental_start_date=rental_start_date,
        rental_end_date=rental_end_date,
        daily_rate=pricing["daily_rate"],
        total_price=pricing["total_price"],
        deposit_amount=pricing["deposit_amount"],
        delivery_option=delivery_option,
        delivery_address=delivery_address,
        delivery_notes=delivery_notes,
        rental_number=rental_number,
        status=RentalStatus.PENDING,
        payment_status=PaymentStatus.UNPAID,
    )

    # M2M relations (must be set after save)
    if games:
        rental.games.set(games)
    if accessories:
        rental.accessories.set(accessories)

    # ── Decrement stock ──────────────────────────────────────────
    _decrement_stock(rental)

    logger.info(
        "Rental %s created for user %s – ₹%s",
        rental_number,
        user.email,
        pricing["total_price"],
    )
    return rental


@transaction.atomic
def return_rental(rental: Rental, *, return_date: date | None = None) -> Rental:
    """
    Mark a rental as returned, restore stock, and compute any late fee.

    Only rentals in ``ACTIVE`` / ``LATE`` / ``OVERDUE`` status can be returned.
    """
    allowed = {RentalStatus.ACTIVE, RentalStatus.LATE, RentalStatus.OVERDUE}
    if rental.status not in allowed:
        raise ValueError(
            f"Cannot return a rental in '{rental.get_status_display()}' status."
        )

    effective_return = return_date or timezone.now().date()

    late_fee = calculate_late_fee(rental, return_date=effective_return)

    rental.actual_return_date = effective_return
    rental.late_fee = late_fee
    rental.status = RentalStatus.RETURNED
    rental.save(update_fields=[
        "actual_return_date",
        "late_fee",
        "status",
        "updated_at",
    ])

    _restore_stock(rental)

    logger.info(
        "Rental %s returned (late fee: ₹%s)", rental.rental_number, late_fee,
    )
    return rental


@transaction.atomic
def cancel_rental(rental: Rental) -> Rental:
    """
    Cancel a pending / confirmed rental and restore stock.
    """
    allowed = {RentalStatus.PENDING, RentalStatus.CONFIRMED}
    if rental.status not in allowed:
        raise ValueError(
            f"Cannot cancel a rental in '{rental.get_status_display()}' status."
        )

    rental.status = RentalStatus.CANCELLED
    rental.save(update_fields=["status", "updated_at"])

    _restore_stock(rental)

    logger.info("Rental %s cancelled", rental.rental_number)
    return rental


@transaction.atomic
def mark_rental_active(rental: Rental) -> Rental:
    """Transition a confirmed rental to active (e.g. after delivery/pickup)."""
    if rental.status != RentalStatus.CONFIRMED:
        raise ValueError(
            f"Cannot activate a rental in '{rental.get_status_display()}' status."
        )

    rental.status = RentalStatus.ACTIVE
    rental.save(update_fields=["status", "updated_at"])

    logger.info("Rental %s is now active", rental.rental_number)
    return rental


@transaction.atomic
def mark_rental_late(rental: Rental) -> Rental:
    """
    Mark an active rental as late and snapshot the current late fee.

    Designed to be called by a periodic Celery task / management command.
    """
    if rental.status != RentalStatus.ACTIVE:
        return rental  # no-op for non-active rentals

    if not rental.is_overdue:
        return rental

    rental.status = RentalStatus.LATE
    rental.late_fee = calculate_late_fee(rental)
    rental.save(update_fields=["status", "late_fee", "updated_at"])

    logger.info(
        "Rental %s marked late (₹%s fee)", rental.rental_number, rental.late_fee,
    )
    return rental
