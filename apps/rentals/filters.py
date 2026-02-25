"""
FilterSet classes for the Rentals app
=====================================

Provides rich filtering on list endpoints via ``django-filter``.
Each FilterSet is wired into the corresponding ViewSet's
``filterset_class`` attribute.

All range filters use ``__gte`` / ``__lte`` suffixes in the query
string — e.g.  ``?daily_price_min=500&daily_price_max=1500``.
"""

import django_filters
from django.db.models import Q

from .models import (
    Accessory,
    Console,
    Game,
    Rental,
    Review,
)


# ═══════════════════════════════════════════════════════════════════
# CONSOLE
# ═══════════════════════════════════════════════════════════════════

class ConsoleFilter(django_filters.FilterSet):
    """
    Filterable fields
    -----------------
    * ``console_type``  — exact (ps4, ps5, …)
    * ``condition_status`` — exact
    * ``daily_price_min`` / ``daily_price_max`` — range
    * ``in_stock`` — boolean: True → available_quantity > 0
    """

    daily_price_min = django_filters.NumberFilter(
        field_name="daily_price", lookup_expr="gte", label="Min daily price (₹)",
    )
    daily_price_max = django_filters.NumberFilter(
        field_name="daily_price", lookup_expr="lte", label="Max daily price (₹)",
    )
    in_stock = django_filters.BooleanFilter(
        method="filter_in_stock", label="In stock only",
    )

    class Meta:
        model = Console
        fields = ["console_type", "condition_status"]

    def filter_in_stock(self, queryset, name, value):
        if value is True:
            return queryset.filter(available_quantity__gt=0)
        if value is False:
            return queryset.filter(available_quantity=0)
        return queryset


# ═══════════════════════════════════════════════════════════════════
# GAME
# ═══════════════════════════════════════════════════════════════════

class GameFilter(django_filters.FilterSet):
    """
    Filterable fields
    -----------------
    * ``platform`` — exact  (ps4, ps5, cross_gen)
    * ``genre``    — exact  (action, rpg, …)
    * ``daily_price_min`` / ``daily_price_max`` — range
    * ``rating_min`` / ``rating_max`` — range (0-10)
    * ``in_stock`` — boolean
    """

    platform = django_filters.CharFilter(
        field_name="platform", lookup_expr="exact",
    )
    genre = django_filters.CharFilter(
        field_name="genre", lookup_expr="exact",
    )
    daily_price_min = django_filters.NumberFilter(
        field_name="daily_price", lookup_expr="gte", label="Min daily price (₹)",
    )
    daily_price_max = django_filters.NumberFilter(
        field_name="daily_price", lookup_expr="lte", label="Max daily price (₹)",
    )
    rating_min = django_filters.NumberFilter(
        field_name="rating", lookup_expr="gte", label="Min rating (0-10)",
    )
    rating_max = django_filters.NumberFilter(
        field_name="rating", lookup_expr="lte", label="Max rating (0-10)",
    )
    in_stock = django_filters.BooleanFilter(
        method="filter_in_stock", label="In stock only",
    )

    class Meta:
        model = Game
        fields = ["platform", "genre"]

    def filter_in_stock(self, queryset, name, value):
        if value is True:
            return queryset.filter(available_quantity__gt=0)
        if value is False:
            return queryset.filter(available_quantity=0)
        return queryset


# ═══════════════════════════════════════════════════════════════════
# ACCESSORY
# ═══════════════════════════════════════════════════════════════════

class AccessoryFilter(django_filters.FilterSet):
    """
    Filterable fields
    -----------------
    * ``category`` — exact
    * ``compatible_with`` — exact (ps4, ps5, cross_gen)
    * ``price_min`` / ``price_max`` — range on price_per_day
    * ``in_stock`` — boolean
    """

    price_min = django_filters.NumberFilter(
        field_name="price_per_day", lookup_expr="gte", label="Min price/day (₹)",
    )
    price_max = django_filters.NumberFilter(
        field_name="price_per_day", lookup_expr="lte", label="Max price/day (₹)",
    )
    in_stock = django_filters.BooleanFilter(
        method="filter_in_stock", label="In stock only",
    )

    class Meta:
        model = Accessory
        fields = ["category", "compatible_with"]

    def filter_in_stock(self, queryset, name, value):
        if value is True:
            return queryset.filter(available_quantity__gt=0)
        if value is False:
            return queryset.filter(available_quantity=0)
        return queryset


# ═══════════════════════════════════════════════════════════════════
# RENTAL
# ═══════════════════════════════════════════════════════════════════

class RentalFilter(django_filters.FilterSet):
    """
    Filterable fields
    -----------------
    * ``status`` — exact
    * ``rental_type`` — exact
    * ``payment_status`` — exact
    * ``start_after`` / ``start_before`` — date range on rental_start_date
    * ``end_after`` / ``end_before`` — date range on rental_end_date
    * ``created_after`` / ``created_before`` — created_at range
    """

    status = django_filters.CharFilter(field_name="status", lookup_expr="exact")
    rental_type = django_filters.CharFilter(field_name="rental_type", lookup_expr="exact")
    payment_status = django_filters.CharFilter(field_name="payment_status", lookup_expr="exact")

    start_after = django_filters.DateFilter(
        field_name="rental_start_date", lookup_expr="gte", label="Start date from",
    )
    start_before = django_filters.DateFilter(
        field_name="rental_start_date", lookup_expr="lte", label="Start date to",
    )
    end_after = django_filters.DateFilter(
        field_name="rental_end_date", lookup_expr="gte", label="End date from",
    )
    end_before = django_filters.DateFilter(
        field_name="rental_end_date", lookup_expr="lte", label="End date to",
    )
    created_after = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte", label="Created from",
    )
    created_before = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="lte", label="Created to",
    )

    class Meta:
        model = Rental
        fields = ["status", "rental_type", "payment_status"]


# ═══════════════════════════════════════════════════════════════════
# REVIEW
# ═══════════════════════════════════════════════════════════════════

class ReviewFilter(django_filters.FilterSet):
    """
    Filterable fields
    -----------------
    * ``rating`` — exact  (1-5)
    * ``rating_min`` / ``rating_max`` — range
    * ``console`` — UUID (filter by console)
    * ``is_verified`` — boolean
    """

    rating_min = django_filters.NumberFilter(
        field_name="rating", lookup_expr="gte", label="Min rating",
    )
    rating_max = django_filters.NumberFilter(
        field_name="rating", lookup_expr="lte", label="Max rating",
    )
    console = django_filters.UUIDFilter(
        field_name="console__id", label="Console UUID",
    )
    is_verified = django_filters.BooleanFilter(
        field_name="is_verified", label="Verified only",
    )

    class Meta:
        model = Review
        fields = ["rating", "console", "is_verified"]
