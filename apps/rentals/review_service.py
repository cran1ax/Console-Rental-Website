"""
Review Service Layer
====================
All business logic for the review lifecycle — creation, updates,
deletion, and aggregate statistics.  Views / serializers stay thin
and only handle HTTP concerns.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django.db import IntegrityError, models, transaction
from django.db.models import Avg, Count, Q

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()

from .models import Console, Rental, RentalStatus, Review

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# VALIDATION  HELPERS
# ═══════════════════════════════════════════════════════════════════

class ReviewValidationError(Exception):
    """Raised when a review operation violates business rules."""

    def __init__(self, detail: str | dict, code: str = "invalid"):
        self.detail = detail
        self.code = code
        super().__init__(detail)


def _validate_rental_for_review(rental: Rental, user) -> None:
    """
    Guard: the rental must be RETURNED and belong to the requesting user.

    Raises ``ReviewValidationError`` if any condition fails.
    """
    if rental.user_id != user.id:
        raise ReviewValidationError(
            "You can only review your own rentals.",
            code="not_owner",
        )

    if rental.status != RentalStatus.RETURNED:
        raise ReviewValidationError(
            "Reviews can only be submitted for returned rentals "
            f"(current status: {rental.get_status_display()}).",
            code="rental_not_returned",
        )


def _validate_no_duplicate(rental: Rental, exclude_review_id=None) -> None:
    """
    Guard: one review per rental (DB also enforces via UniqueConstraint).

    ``exclude_review_id`` is used when *updating* an existing review so
    the check doesn't flag the review being edited.
    """
    qs = Review.objects.filter(rental=rental)
    if exclude_review_id:
        qs = qs.exclude(id=exclude_review_id)
    if qs.exists():
        raise ReviewValidationError(
            "A review already exists for this rental.",
            code="duplicate_review",
        )


# ═══════════════════════════════════════════════════════════════════
# CREATE
# ═══════════════════════════════════════════════════════════════════

@transaction.atomic
def create_review(
    *,
    user,
    rental: Rental,
    rating: int,
    title: str = "",
    comment: str = "",
) -> Review:
    """
    Create a verified review for a completed rental.

    Parameters
    ----------
    user : User
        The authenticated user submitting the review.
    rental : Rental
        Must be RETURNED and owned by ``user``.
    rating : int
        1–5 inclusive.
    title : str
        Optional headline.
    comment : str
        Optional body text.

    Returns
    -------
    Review

    Raises
    ------
    ReviewValidationError
        If any business rule is violated.
    """
    _validate_rental_for_review(rental, user)
    _validate_no_duplicate(rental)

    try:
        review = Review.objects.create(
            rental=rental,
            user=user,
            console=rental.console,  # nullable — None for game-only rentals
            title=title,
            rating=rating,
            comment=comment,
            is_verified=True,
        )
    except IntegrityError:
        # Race condition — the UniqueConstraint caught a concurrent insert
        raise ReviewValidationError(
            "A review already exists for this rental.",
            code="duplicate_review",
        )

    logger.info(
        "Review %s created by %s for Rental %s (%d★).",
        review.id,
        user.email,
        rental.rental_number,
        rating,
    )
    return review


# ═══════════════════════════════════════════════════════════════════
# UPDATE
# ═══════════════════════════════════════════════════════════════════

def update_review(
    *,
    review: Review,
    user,
    rating: int | None = None,
    title: str | None = None,
    comment: str | None = None,
) -> Review:
    """
    Update an existing review.  Only the original author may edit.

    Raises
    ------
    ReviewValidationError
        If the user is not the review author.
    """
    if review.user_id != user.id:
        raise ReviewValidationError(
            "You can only edit your own reviews.",
            code="not_owner",
        )

    update_fields = ["updated_at"]

    if rating is not None:
        review.rating = rating
        update_fields.append("rating")
    if title is not None:
        review.title = title
        update_fields.append("title")
    if comment is not None:
        review.comment = comment
        update_fields.append("comment")

    review.save(update_fields=update_fields)

    logger.info("Review %s updated by %s.", review.id, user.email)
    return review


# ═══════════════════════════════════════════════════════════════════
# DELETE
# ═══════════════════════════════════════════════════════════════════

def delete_review(*, review: Review, user) -> None:
    """
    Soft-guard: only the author or an admin may delete.

    For now we do a hard delete.  If you need soft-delete in the future
    add an ``is_deleted`` flag and filter accordingly.
    """
    if review.user_id != user.id and not user.is_staff:
        raise ReviewValidationError(
            "You can only delete your own reviews.",
            code="not_owner",
        )

    logger.info(
        "Review %s deleted by %s (Rental %s).",
        review.id,
        user.email,
        review.rental.rental_number,
    )
    review.delete()


# ═══════════════════════════════════════════════════════════════════
# AGGREGATE STATS
# ═══════════════════════════════════════════════════════════════════

def get_console_review_stats(console: Console) -> dict[str, Any]:
    """
    Return aggregate review statistics for a console.

    Returns
    -------
    dict with keys:
        average_rating  – float rounded to 1 dp, or None
        total_reviews   – int
        rating_breakdown – {1: count, 2: count, …, 5: count}
    """
    qs = Review.objects.filter(console=console, is_verified=True)

    agg = qs.aggregate(
        average_rating=Avg("rating"),
        total_reviews=Count("id"),
    )

    # Rating breakdown in one query
    breakdown_qs = (
        qs.values("rating")
        .annotate(count=Count("id"))
        .order_by("rating")
    )
    breakdown = {i: 0 for i in range(1, 6)}
    for row in breakdown_qs:
        breakdown[row["rating"]] = row["count"]

    avg = agg["average_rating"]
    return {
        "average_rating": round(avg, 1) if avg is not None else None,
        "total_reviews": agg["total_reviews"],
        "rating_breakdown": breakdown,
    }


def get_reviewable_rentals(user) -> models.QuerySet:
    """
    Return rentals that the user can still review (RETURNED + no review yet).
    Useful for a "Write a review" prompt on the frontend.
    """
    return (
        Rental.objects
        .filter(user=user, status=RentalStatus.RETURNED)
        .exclude(review__isnull=False)
        .select_related("console")
        .order_by("-actual_return_date")
    )
