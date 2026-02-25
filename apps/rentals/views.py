import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import IsAdminOrReadOnly, IsOwner

from . import availability_service, rental_service, review_service
from .models import Accessory, Console, Game, Rental, RentalStatus, Review
from .review_service import ReviewValidationError
from .serializers import (
    AccessorySerializer,
    AvailabilityCheckSerializer,
    AvailabilityItemSerializer,
    BulkAvailabilitySerializer,
    ConsoleDetailSerializer,
    ConsoleListSerializer,
    GameDetailSerializer,
    GameListSerializer,
    RentalCreateSerializer,
    RentalDetailSerializer,
    RentalListSerializer,
    ReviewableRentalSerializer,
    ReviewCreateSerializer,
    ReviewDetailSerializer,
    ReviewListSerializer,
    ReviewStatsSerializer,
    ReviewUpdateSerializer,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# CONSOLE
# ═══════════════════════════════════════════════════════════════════

class ConsoleViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve available consoles."""

    queryset = Console.objects.filter(is_active=True).prefetch_related("images")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["console_type", "condition_status"]
    search_fields = ["name", "description"]
    ordering_fields = ["daily_price", "created_at", "name"]
    ordering = ["-created_at"]
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ConsoleDetailSerializer
        return ConsoleListSerializer

    @action(detail=True, methods=["get"])
    def reviews(self, request, slug=None):
        """GET /consoles/{slug}/reviews/ — paginated reviews for this console."""
        console = self.get_object()
        reviews = (
            Review.objects
            .filter(console=console)
            .select_related("user", "rental")
            .order_by("-created_at")
        )
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = ReviewListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReviewListSerializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="review-stats")
    def review_stats(self, request, slug=None):
        """GET /consoles/{slug}/review-stats/ — aggregate rating stats."""
        console = self.get_object()
        stats = review_service.get_console_review_stats(console)
        serializer = ReviewStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="check-availability")
    def check_availability(self, request, slug=None):
        """
        Check if this console is available for a date range.

        Query params: ``?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD``

        Returns an availability verdict with stock / overlap details.
        """
        console = self.get_object()
        serializer = AvailabilityCheckSerializer(data={
            "console_id": console.pk,
            "start_date": request.query_params.get("start_date"),
            "end_date": request.query_params.get("end_date"),
        })
        serializer.is_valid(raise_exception=True)

        result = availability_service.check_console_availability(
            console=console,
            start=serializer.validated_data["start_date"],
            end=serializer.validated_data["end_date"],
        )
        return Response(AvailabilityItemSerializer(result).data)


# ═══════════════════════════════════════════════════════════════════
# GAME
# ═══════════════════════════════════════════════════════════════════

class GameViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve available games."""

    queryset = Game.objects.filter(is_active=True)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["platform", "genre"]
    search_fields = ["title", "description"]
    ordering_fields = ["daily_price", "rating", "created_at", "title"]
    ordering = ["-created_at"]
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return GameDetailSerializer
        return GameListSerializer


# ═══════════════════════════════════════════════════════════════════
# ACCESSORY
# ═══════════════════════════════════════════════════════════════════

class AccessoryViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve available accessories."""

    queryset = Accessory.objects.filter(is_active=True)
    serializer_class = AccessorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "compatible_with"]
    search_fields = ["name", "description"]
    ordering_fields = ["price_per_day", "created_at", "name"]
    ordering = ["-created_at"]
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"


# ═══════════════════════════════════════════════════════════════════
# RENTAL
# ═══════════════════════════════════════════════════════════════════

class RentalViewSet(viewsets.ModelViewSet):
    """
    CRUD for user rentals.

    All business logic (pricing, stock, late fees) is delegated to
    ``rental_service``.  This view is intentionally thin.
    """

    permission_classes = [permissions.IsAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "rental_type", "payment_status"]
    ordering_fields = ["created_at", "rental_start_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            Rental.objects.filter(user=self.request.user)
            .select_related("console")
            .prefetch_related("games", "accessories")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return RentalCreateSerializer
        if self.action in ("retrieve",):
            return RentalDetailSerializer
        return RentalListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        try:
            rental = rental_service.create_rental(
                user=request.user,
                console=data.get("console"),
                games=data.get("game_ids", []),
                accessories=data.get("accessory_ids", []),
                rental_type=data["rental_type"],
                rental_start_date=data["rental_start_date"],
                rental_end_date=data["rental_end_date"],
                delivery_option=data.get("delivery_option", "pickup"),
                delivery_address=data.get("delivery_address", ""),
                delivery_notes=data.get("delivery_notes", ""),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            RentalDetailSerializer(rental).data,
            status=status.HTTP_201_CREATED,
        )

    # ── Return a rental ──────────────────────────────────────────
    @action(detail=True, methods=["post"])
    def return_rental(self, request, pk=None):
        rental = self.get_object()
        try:
            rental = rental_service.return_rental(rental)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(RentalDetailSerializer(rental).data)

    # ── Cancel a rental ──────────────────────────────────────────
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        rental = self.get_object()
        try:
            rental = rental_service.cancel_rental(rental)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Rental cancelled successfully."})

    # ── Late fee preview ─────────────────────────────────────────
    @action(detail=True, methods=["get"])
    def late_fee(self, request, pk=None):
        rental = self.get_object()
        fee = rental_service.calculate_late_fee(rental)
        return Response({
            "rental_number": rental.rental_number,
            "overdue_days": rental.overdue_days,
            "late_fee": str(fee),
        })


# ═══════════════════════════════════════════════════════════════════
# REVIEW
# ═══════════════════════════════════════════════════════════════════

class ReviewViewSet(viewsets.GenericViewSet):
    """
    Full CRUD for reviews — business logic delegated to ``review_service``.

    Endpoints (registered at ``/reviews/``)
    ──────────────────────────────────────
    POST   /reviews/                 → create
    GET    /reviews/                 → list (own reviews)
    GET    /reviews/{id}/            → detail
    PATCH  /reviews/{id}/            → partial update
    DELETE /reviews/{id}/            → destroy
    GET    /reviews/reviewable/      → rentals the user can still review
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return (
            Review.objects
            .filter(user=self.request.user)
            .select_related("rental", "console", "user")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ReviewCreateSerializer
        if self.action in ("partial_update", "update"):
            return ReviewUpdateSerializer
        if self.action == "retrieve":
            return ReviewDetailSerializer
        return ReviewListSerializer

    # ── CREATE ───────────────────────────────────────────────────

    def create(self, request):
        """POST /reviews/ — submit a review for a completed rental."""
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            review = review_service.create_review(
                user=request.user,
                rental=serializer.validated_data["rental"],
                rating=serializer.validated_data["rating"],
                title=serializer.validated_data.get("title", ""),
                comment=serializer.validated_data.get("comment", ""),
            )
        except ReviewValidationError as exc:
            return Response(
                {"detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            ReviewDetailSerializer(review).data,
            status=status.HTTP_201_CREATED,
        )

    # ── LIST (own reviews) ───────────────────────────────────────

    def list(self, request):
        """GET /reviews/ — list the authenticated user's reviews."""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ReviewListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReviewListSerializer(queryset, many=True)
        return Response(serializer.data)

    # ── RETRIEVE ─────────────────────────────────────────────────

    def retrieve(self, request, id=None):
        """GET /reviews/{id}/ — single review detail."""
        review = self.get_object()
        return Response(ReviewDetailSerializer(review).data)

    # ── PARTIAL UPDATE ───────────────────────────────────────────

    def partial_update(self, request, id=None):
        """PATCH /reviews/{id}/ — edit an existing review."""
        review = self.get_object()
        serializer = ReviewUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            review = review_service.update_review(
                review=review,
                user=request.user,
                **serializer.validated_data,
            )
        except ReviewValidationError as exc:
            return Response(
                {"detail": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(ReviewDetailSerializer(review).data)

    # ── DELETE ────────────────────────────────────────────────────

    def destroy(self, request, id=None):
        """DELETE /reviews/{id}/ — remove a review."""
        review = self.get_object()
        try:
            review_service.delete_review(review=review, user=request.user)
        except ReviewValidationError as exc:
            return Response(
                {"detail": exc.detail},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── REVIEWABLE RENTALS ───────────────────────────────────────

    @action(detail=False, methods=["get"])
    def reviewable(self, request):
        """
        GET /reviews/reviewable/
        Returns rentals the user can still submit a review for.
        """
        rentals = review_service.get_reviewable_rentals(request.user)
        page = self.paginate_queryset(rentals)
        if page is not None:
            serializer = ReviewableRentalSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReviewableRentalSerializer(rentals, many=True)
        return Response(serializer.data)


# ═══════════════════════════════════════════════════════════════════
# AVAILABILITY
# ═══════════════════════════════════════════════════════════════════

class AvailabilityCheckView(generics.GenericAPIView):
    """
    POST /api/rentals/availability/check/

    Bulk availability check for an entire cart (console + games +
    accessories) against a date range.  Returns per-item verdicts
    and a top-level ``all_available`` flag.

    Request body::

        {
            "console_id": "<uuid>",          // optional
            "game_ids": ["<uuid>", ...],     // optional
            "accessory_ids": ["<uuid>", ...],// optional
            "start_date": "2026-03-01",
            "end_date": "2026-03-08"
        }
    """

    serializer_class = AvailabilityCheckSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        result = availability_service.check_bulk_availability(
            console=data.get("console_id"),
            games=data.get("game_ids", []),
            accessories=data.get("accessory_ids", []),
            start=data["start_date"],
            end=data["end_date"],
        )

        return Response(BulkAvailabilitySerializer(result).data)
