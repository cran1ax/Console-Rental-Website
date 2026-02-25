"""
Availability Service
====================
Date-range-aware availability checking for consoles, games, and accessories.

The core idea
~~~~~~~~~~~~~
``available_quantity`` on each item reflects *current* real-time stock.
To know if an item is available for a **future** date range we must also
account for overlapping rentals that have already been booked but haven't
started yet (status = pending / confirmed / active / late).

Algorithm:
    overlapping_count = # of non-terminal rentals whose date range
                        overlaps [start, end)
    date_available    = stock_quantity - overlapping_count
    is_available      = date_available > 0

Date overlap condition (standard interval overlap):
    existing.rental_start_date < requested_end
    AND existing.rental_end_date > requested_start

This correctly handles:
    - exact same dates
    - partial overlap on either side
    - one rental fully inside another
    - adjacent dates (end == start → NOT overlapping, the item is returned)

Performance
~~~~~~~~~~~
All queries use a *single* aggregated DB hit per item type (console /
games / accessories) — no N+1 loops.  The composite indexes added to
``Rental.Meta`` make the overlap scan an index-only range check on
PostgreSQL.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Sequence
from uuid import UUID

from django.db.models import Count, Q

from .models import (
    Accessory,
    Console,
    Game,
    Rental,
    RentalStatus,
)

logger = logging.getLogger(__name__)

# Rental statuses that "hold" inventory — i.e. the item is not back yet.
BLOCKING_STATUSES = {
    RentalStatus.PENDING,
    RentalStatus.CONFIRMED,
    RentalStatus.ACTIVE,
    RentalStatus.LATE,
    RentalStatus.OVERDUE,
}


# ═══════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class AvailabilityResult:
    """Availability verdict for a single item."""

    item_id: UUID
    item_type: str          # "console" | "game" | "accessory"
    item_name: str
    is_available: bool
    stock_quantity: int
    overlapping_rentals: int
    available_for_dates: int  # stock_quantity - overlapping_rentals

    @property
    def reason(self) -> str:
        if self.is_available:
            return f"{self.available_for_dates} unit(s) available"
        return (
            f"All {self.stock_quantity} unit(s) booked "
            f"({self.overlapping_rentals} overlapping rental(s))"
        )


@dataclass(frozen=True, slots=True)
class BulkAvailabilityResult:
    """Combined availability check for a full rental cart."""

    console: AvailabilityResult | None
    games: list[AvailabilityResult]
    accessories: list[AvailabilityResult]

    @property
    def all_available(self) -> bool:
        items: list[AvailabilityResult] = []
        if self.console:
            items.append(self.console)
        items.extend(self.games)
        items.extend(self.accessories)
        return all(item.is_available for item in items)

    @property
    def unavailable_items(self) -> list[AvailabilityResult]:
        items: list[AvailabilityResult] = []
        if self.console and not self.console.is_available:
            items.append(self.console)
        items.extend(g for g in self.games if not g.is_available)
        items.extend(a for a in self.accessories if not a.is_available)
        return items


# ═══════════════════════════════════════════════════════════════════
# OVERLAP QUERY HELPERS
# ═══════════════════════════════════════════════════════════════════


def _blocking_overlap_q(start: date, end: date) -> Q:
    """
    Q filter matching rentals that overlap ``[start, end)`` and block stock.

    Overlap logic (both conditions must be true):
        rental_start_date < end   (rental begins before the requested period ends)
        rental_end_date   > start (rental ends after the requested period begins)

    Edge-case: ``end == existing.start`` → NOT overlapping (item returned in the
    morning, re-rented in the afternoon is acceptable).
    """
    return Q(
        status__in=BLOCKING_STATUSES,
        rental_start_date__lt=end,
        rental_end_date__gt=start,
    )


def _count_overlapping_console_rentals(
    console_id: UUID,
    start: date,
    end: date,
    *,
    exclude_rental_id: UUID | None = None,
) -> int:
    """Count non-terminal rentals for a console overlapping the given range."""
    qs = Rental.objects.filter(
        console_id=console_id,
    ).filter(
        _blocking_overlap_q(start, end),
    )
    if exclude_rental_id:
        qs = qs.exclude(pk=exclude_rental_id)
    return qs.count()


def _count_overlapping_game_rentals(
    game_ids: Sequence[UUID],
    start: date,
    end: date,
    *,
    exclude_rental_id: UUID | None = None,
) -> dict[UUID, int]:
    """
    For each game id, return the count of overlapping blocking rentals.

    Uses a *single* aggregated query — no N+1.
    """
    if not game_ids:
        return {}

    qs = (
        Rental.objects
        .filter(
            games__id__in=game_ids,
        )
        .filter(_blocking_overlap_q(start, end))
    )
    if exclude_rental_id:
        qs = qs.exclude(pk=exclude_rental_id)

    rows = (
        qs.values("games__id")
        .annotate(cnt=Count("id", distinct=True))
    )
    return {row["games__id"]: row["cnt"] for row in rows}


def _count_overlapping_accessory_rentals(
    accessory_ids: Sequence[UUID],
    start: date,
    end: date,
    *,
    exclude_rental_id: UUID | None = None,
) -> dict[UUID, int]:
    """Same as game variant, but for accessories.  Single DB query."""
    if not accessory_ids:
        return {}

    qs = (
        Rental.objects
        .filter(
            accessories__id__in=accessory_ids,
        )
        .filter(_blocking_overlap_q(start, end))
    )
    if exclude_rental_id:
        qs = qs.exclude(pk=exclude_rental_id)

    rows = (
        qs.values("accessories__id")
        .annotate(cnt=Count("id", distinct=True))
    )
    return {row["accessories__id"]: row["cnt"] for row in rows}


# ═══════════════════════════════════════════════════════════════════
# PUBLIC API — single-item checks
# ═══════════════════════════════════════════════════════════════════


def check_console_availability(
    console: Console,
    start: date,
    end: date,
    *,
    exclude_rental_id: UUID | None = None,
) -> AvailabilityResult:
    """
    Check whether a specific console is available for ``[start, end)``.

    Parameters
    ----------
    console : Console
        The console instance to check.
    start / end : date
        Requested rental period (end is exclusive — the item is returned on
        ``end`` and can be re-rented the same day).
    exclude_rental_id : UUID, optional
        If supplied, excludes this rental from the overlap count (useful when
        editing an existing booking).

    Returns
    -------
    AvailabilityResult
    """
    if end <= start:
        raise ValueError("end date must be after start date")

    overlapping = _count_overlapping_console_rentals(
        console.pk, start, end, exclude_rental_id=exclude_rental_id,
    )
    available_for_dates = console.stock_quantity - overlapping

    return AvailabilityResult(
        item_id=console.pk,
        item_type="console",
        item_name=str(console),
        is_available=available_for_dates > 0,
        stock_quantity=console.stock_quantity,
        overlapping_rentals=overlapping,
        available_for_dates=max(available_for_dates, 0),
    )


def check_game_availability(
    game: Game,
    start: date,
    end: date,
    *,
    exclude_rental_id: UUID | None = None,
) -> AvailabilityResult:
    """Check a single game's availability for ``[start, end)``."""
    if end <= start:
        raise ValueError("end date must be after start date")

    counts = _count_overlapping_game_rentals(
        [game.pk], start, end, exclude_rental_id=exclude_rental_id,
    )
    overlapping = counts.get(game.pk, 0)
    available_for_dates = game.stock_quantity - overlapping

    return AvailabilityResult(
        item_id=game.pk,
        item_type="game",
        item_name=str(game),
        is_available=available_for_dates > 0,
        stock_quantity=game.stock_quantity,
        overlapping_rentals=overlapping,
        available_for_dates=max(available_for_dates, 0),
    )


def check_accessory_availability(
    accessory: Accessory,
    start: date,
    end: date,
    *,
    exclude_rental_id: UUID | None = None,
) -> AvailabilityResult:
    """Check a single accessory's availability for ``[start, end)``."""
    if end <= start:
        raise ValueError("end date must be after start date")

    counts = _count_overlapping_accessory_rentals(
        [accessory.pk], start, end, exclude_rental_id=exclude_rental_id,
    )
    overlapping = counts.get(accessory.pk, 0)
    available_for_dates = accessory.stock_quantity - overlapping

    return AvailabilityResult(
        item_id=accessory.pk,
        item_type="accessory",
        item_name=str(accessory),
        is_available=available_for_dates > 0,
        stock_quantity=accessory.stock_quantity,
        overlapping_rentals=overlapping,
        available_for_dates=max(available_for_dates, 0),
    )


# ═══════════════════════════════════════════════════════════════════
# PUBLIC API — bulk / cart check
# ═══════════════════════════════════════════════════════════════════


def check_bulk_availability(
    *,
    console: Console | None = None,
    games: Sequence[Game] | None = None,
    accessories: Sequence[Accessory] | None = None,
    start: date,
    end: date,
    exclude_rental_id: UUID | None = None,
) -> BulkAvailabilityResult:
    """
    Check availability for an entire rental cart in the fewest DB hits.

    Queries performed:
        1 query  for the console        (if present)
        1 query  for all games           (aggregated)
        1 query  for all accessories     (aggregated)
    = max 3 queries regardless of cart size.

    Returns
    -------
    BulkAvailabilityResult
        Contains per-item verdicts and a convenience ``all_available`` flag.
    """
    if end <= start:
        raise ValueError("end date must be after start date")

    games = list(games or [])
    accessories = list(accessories or [])

    # ── Console ──────────────────────────────────────────────────
    console_result: AvailabilityResult | None = None
    if console:
        console_result = check_console_availability(
            console, start, end, exclude_rental_id=exclude_rental_id,
        )

    # ── Games (single query for all) ────────────────────────────
    game_results: list[AvailabilityResult] = []
    if games:
        game_ids = [g.pk for g in games]
        counts = _count_overlapping_game_rentals(
            game_ids, start, end, exclude_rental_id=exclude_rental_id,
        )
        for game in games:
            overlapping = counts.get(game.pk, 0)
            avail = game.stock_quantity - overlapping
            game_results.append(
                AvailabilityResult(
                    item_id=game.pk,
                    item_type="game",
                    item_name=str(game),
                    is_available=avail > 0,
                    stock_quantity=game.stock_quantity,
                    overlapping_rentals=overlapping,
                    available_for_dates=max(avail, 0),
                )
            )

    # ── Accessories (single query for all) ──────────────────────
    accessory_results: list[AvailabilityResult] = []
    if accessories:
        acc_ids = [a.pk for a in accessories]
        counts = _count_overlapping_accessory_rentals(
            acc_ids, start, end, exclude_rental_id=exclude_rental_id,
        )
        for acc in accessories:
            overlapping = counts.get(acc.pk, 0)
            avail = acc.stock_quantity - overlapping
            accessory_results.append(
                AvailabilityResult(
                    item_id=acc.pk,
                    item_type="accessory",
                    item_name=str(acc),
                    is_available=avail > 0,
                    stock_quantity=acc.stock_quantity,
                    overlapping_rentals=overlapping,
                    available_for_dates=max(avail, 0),
                )
            )

    result = BulkAvailabilityResult(
        console=console_result,
        games=game_results,
        accessories=accessory_results,
    )

    logger.debug(
        "Availability check [%s → %s]: all_available=%s, unavailable=%s",
        start,
        end,
        result.all_available,
        [u.item_name for u in result.unavailable_items],
    )

    return result
